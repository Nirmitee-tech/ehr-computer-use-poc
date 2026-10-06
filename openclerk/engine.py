import json
import os
import threading
import time
import uuid
from pathlib import Path
from .types import ClerkError, validate_action


class Engine:
    """One reviewed action per screenshot; completion remains an operator decision."""
    def __init__(self, driver, planner, allowed_apps, journal=None, max_steps=30, review_ttl=120):
        self.driver = driver
        self.planner = planner
        self.allowed_apps = set(allowed_apps)
        self.max_steps = max_steps
        self.review_ttl = review_ttl
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.epoch = 0
        self.busy = False
        self.state = "idle"
        self.error = ""
        self.task = ""
        self.bundle_id = ""
        self.run_id = ""
        self.steps = 0
        self.observation = None
        self.pending = None
        self.history = []
        self.events = []
        self.journal = Path(journal) if journal else None
        if self.journal:
            self.journal.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.journal.touch(mode=0o600, exist_ok=True)
            os.chmod(self.journal, 0o600)

    def record(self, event, **metadata):
        # Persist action metadata only. Tasks, typed content, screenshots and OCR stay in memory.
        entry = {"time": time.time(), "run_id": self.run_id, "event": event, **metadata}
        self.events.append(entry)
        self.events = self.events[-100:]
        if self.journal:
            with self.journal.open("a") as stream:
                stream.write(json.dumps(entry, sort_keys=True) + "\n")

    def status(self):
        with self.lock:
            return {"state": self.state, "busy": self.busy, "error": self.error, "run_id": self.run_id,
                    "task": self.task, "bundle_id": self.bundle_id, "steps": self.steps,
                    "max_steps": self.max_steps, "allowed_apps": sorted(self.allowed_apps),
                    "observation": self.observation.public() if self.observation else None,
                    "pending": self.pending, "events": self.events[-25:], "model": self.planner.model}

    def start(self, task, bundle_id, model):
        with self.lock:
            if self.busy:
                raise ClerkError("An operation is still finishing. Wait before starting another run.")
            if bundle_id not in self.allowed_apps:
                raise ClerkError("Application has not been allowed in the runner configuration")
            if not isinstance(task, str) or not 1 <= len(task.strip()) <= 4000:
                raise ClerkError("Enter a task of at most 4000 characters")
            if not isinstance(model, str) or not 1 <= len(model) <= 100 or model.endswith("cloud"):
                raise ClerkError("Choose a local model")
            self.epoch += 1
            self.stop_event.clear()
            self.run_id = uuid.uuid4().hex
            self.task = task.strip(); self.bundle_id = bundle_id
            self.planner.model = model
            self.steps = 0; self.history = []; self.pending = None; self.observation = None
            self.error = ""; self.state = "ready"
            self.record("run_started", bundle_id=bundle_id, model=model)
        return self.status()

    def stop(self):
        with self.lock:
            self.stop_event.set(); self.epoch += 1; self.pending = None
            self.state = "stopped"; self.error = ""
            self.record("stop_requested", in_flight=self.busy)
        return self.status()

    def begin(self, state):
        with self.lock:
            if self.busy:
                raise ClerkError("An operation is already running")
            if self.state in {"idle", "stopped", "completed", "handoff", "uncertain"} or self.stop_event.is_set():
                raise ClerkError("Start a new run before continuing")
            self.busy = True; self.state = state; self.error = ""
            return self.epoch, self.bundle_id

    def fail(self, epoch, exc, uncertain=False):
        with self.lock:
            self.busy = False
            if self.epoch == epoch:
                self.state = "uncertain" if uncertain else "error"
                self.error = str(exc); self.pending = None
                self.record("outcome_uncertain" if uncertain else "operation_failed", error_type=type(exc).__name__)

    def observe(self):
        epoch, bundle = self.begin("observing")
        with self.lock:
            self.pending = None
        try:
            observation = self.driver.observe(bundle)
            with self.lock:
                self.busy = False
                if self.epoch != epoch or self.stop_event.is_set():
                    return self.status()
                self.observation = observation; self.state = "ready"
                self.record("screen_observed", fingerprint=observation.fingerprint)
            return self.status()
        except Exception as exc:
            self.fail(epoch, exc)
            raise

    def propose(self):
        with self.lock:
            if self.steps >= self.max_steps:
                raise ClerkError("Step limit reached. Inspect the result before starting a new run.")
            if self.pending:
                raise ClerkError("Review or reject the pending action first")
        epoch, bundle = self.begin("planning")
        try:
            observation = self.driver.observe(bundle)
            with self.lock:
                if self.epoch != epoch or self.stop_event.is_set():
                    self.busy = False
                    return self.status()
                task, history = self.task, list(self.history)
            action = validate_action(self.planner.propose(task, observation, history), observation)
            with self.lock:
                self.busy = False
                if self.epoch != epoch or self.stop_event.is_set():
                    return self.status()
                self.observation = observation
                self.pending = {"id": uuid.uuid4().hex, "action": action,
                                "created_at": time.time(), "fingerprint": observation.fingerprint}
                self.state = "review"
                self.record("action_proposed", kind=action["kind"], proposal_id=self.pending["id"])
            return self.status()
        except Exception as exc:
            self.fail(epoch, exc)
            raise

    def reject(self, proposal_id):
        with self.lock:
            if self.busy or not self.pending or self.pending["id"] != proposal_id:
                raise ClerkError("This proposal is no longer pending")
            self.record("action_rejected", proposal_id=proposal_id)
            self.pending = None; self.state = "ready"
        return self.status()

    def approve(self, proposal_id):
        with self.lock:
            if self.busy or self.state != "review" or not self.pending or self.pending["id"] != proposal_id:
                raise ClerkError("This proposal is no longer pending")
            proposal = self.pending
            if time.time() - proposal["created_at"] > self.review_ttl:
                self.pending = None; self.state = "ready"
                raise ClerkError("Review expired. Ask for a fresh proposal.")
            action = proposal["action"]
            observation = self.observation
            epoch, bundle = self.begin("executing")
            self.pending = None
            self.record("action_approved", kind=action["kind"], proposal_id=proposal_id)
        issued = False
        try:
            fresh = self.driver.observe(bundle)
            with self.lock:
                if self.epoch != epoch or self.stop_event.is_set():
                    self.busy = False
                    return self.status()
                if fresh.fingerprint != observation.fingerprint:
                    self.observation = fresh
                    raise ClerkError("Screen changed since review. Ask for a fresh proposal.")
                self.steps += 1
            if action["kind"] in {"done", "handoff"}:
                with self.lock:
                    self.busy = False
                    if self.epoch == epoch:
                        self.state = "completed" if action["kind"] == "done" else "handoff"
                        self.record("operator_confirmed_result" if action["kind"] == "done" else "handed_off")
                return self.status()
            issued = True
            self.driver.execute(bundle, fresh, action, self.stop_event.is_set)
            after = self.driver.observe(bundle)
            with self.lock:
                self.busy = False
                self.record("input_posted", kind=action["kind"])
                if self.epoch != epoch or self.stop_event.is_set():
                    return self.status()
                self.observation = after
                self.history.append({"action": action, "result": "Input posted; inspect the new screenshot"})
                self.state = "ready"
                self.record("screen_observed_after_input", fingerprint=after.fingerprint)
            return self.status()
        except Exception as exc:
            # A bridge error may happen after input. Require inspection, never an automatic retry.
            self.fail(epoch, exc, uncertain=issued)
            raise
