import base64
import hashlib
import json
import selectors
import subprocess
import threading
from pathlib import Path
from .types import ClerkError, Observation


class MacDriver:
    """Use a persistent native bridge, one approved window, and CoreGraphics input."""
    def __init__(self, bridge):
        self.bridge = Path(bridge).resolve()
        self.process = None
        self.lock = threading.RLock()

    def close(self):
        with self.lock:
            if self.process:
                process, self.process = self.process, None
                if process.stdin: process.stdin.close()
                try: process.wait(timeout=2)
                except subprocess.TimeoutExpired: process.kill(); process.wait()
                if process.stdout: process.stdout.close()

    def call(self, request):
        if not self.bridge.is_file():
            raise ClerkError("Native bridge is missing. Run scripts/build-native.sh first.")
        with self.lock:
            try:
                if self.process is None or self.process.poll() is not None:
                    self.process = subprocess.Popen([str(self.bridge), "--session"], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
                self.process.stdin.write(json.dumps(request) + "\n")
                self.process.stdin.flush()
                with selectors.DefaultSelector() as selector:
                    selector.register(self.process.stdout, selectors.EVENT_READ)
                    if not selector.select(timeout=20):
                        self.close()
                        raise ClerkError("Native bridge timed out. Inspect the target before retrying.")
                line = self.process.stdout.readline()
                if not line:
                    self.close()
                    raise ClerkError("Native bridge exited before returning a result.")
                response = json.loads(line)
            except (OSError, ValueError) as exc:
                self.close()
                raise ClerkError("Native bridge failed: " + type(exc).__name__) from exc
            if not response.get("ok"):
                raise ClerkError(response.get("error", "Native bridge rejected the request"))
            return response

    def doctor(self):
        return self.call({"command": "doctor"})

    def apps(self):
        return self.call({"command": "apps"})["apps"]

    def activate(self, bundle_id):
        blocked = ('terminal', 'iterm', 'code', 'jetbrains', 'systempreferences', 'openclerk.runner')
        if not isinstance(bundle_id, str) or any(word in bundle_id.lower() for word in blocked):
            raise ClerkError("Application is outside supported desktop targets")
        try:
            result = subprocess.run(['/usr/bin/open', '-b', bundle_id], capture_output=True, timeout=5)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ClerkError("Could not activate the approved application") from exc
        if result.returncode:
            raise ClerkError("The approved application could not be opened")

    def observe(self, bundle_id):
        self.activate(bundle_id)
        value = self.call({"command": "observe", "bundle_id": bundle_id})
        return Observation(bundle_id, value["window_id"], value["bounds"],
                           value["width"], value["height"], base64.b64decode(value["png"]), value.get("text", ""), value.get("process_id", 0))

    def execute(self, bundle_id, observation, action, stopped):
        if stopped():
            raise ClerkError("Run stopped before input")
        self.activate(bundle_id)
        return self.call({"command": "execute", "bundle_id": bundle_id,
                          "window_id": observation.window_id, "process_id": observation.process_id, "bounds": observation.bounds,
                          "fingerprint_png": hashlib.sha256(observation.png).hexdigest(), "action": action})
