import base64
import hashlib
import math
from dataclasses import dataclass
from typing import Any, Dict


class ClerkError(Exception):
    pass


ACTION_KINDS = {"click", "double_click", "type", "key", "scroll", "wait", "done", "handoff"}
KEYS = {"tab", "enter", "escape", "backspace", "space", "left", "right", "up", "down", "home", "end"}


def number(value, name, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ClerkError(name + " must be a finite number")
    if not low <= value <= high:
        raise ClerkError(name + " is out of range")
    return value


@dataclass(frozen=True)
class Observation:
    bundle_id: str
    window_id: int
    bounds: Dict[str, float]
    width: int
    height: int
    png: bytes
    text: str = ""
    process_id: int = 0

    @property
    def fingerprint(self):
        geometry = repr((self.bundle_id, self.window_id, self.process_id, sorted(self.bounds.items()), self.width, self.height))
        return hashlib.sha256(geometry.encode() + self.png).hexdigest()

    def public(self):
        return {"bundle_id": self.bundle_id, "window_id": self.window_id,
                "process_id": self.process_id, "bounds": self.bounds, "width": self.width, "height": self.height,
                "image": "data:image/png;base64," + base64.b64encode(self.png).decode(),
                "text": self.text, "fingerprint": self.fingerprint}


def validate_action(raw: Any, observation: Observation):
    if not isinstance(raw, dict):
        raise ClerkError("Action must be an object")
    allowed = {"kind", "x", "y", "text", "key", "delta", "seconds", "reason", "expected", "evidence"}
    if set(raw) - allowed:
        raise ClerkError("Unknown action fields")
    action = dict(raw)
    kind = action.get("kind")
    if kind not in ACTION_KINDS:
        raise ClerkError("Unsupported action")
    for field in ("reason", "expected"):
        if not isinstance(action.get(field), str) or not 1 <= len(action[field]) <= 1500:
            raise ClerkError(field + " is required and must be at most 1500 characters")
    fields_by_kind = {"click": {"x", "y"}, "double_click": {"x", "y"},
                      "type": {"text"}, "key": {"key"}, "scroll": {"x", "y", "delta"},
                      "wait": {"seconds"}, "done": {"evidence"}, "handoff": set()}
    if set(action) - ({"kind", "reason", "expected"} | fields_by_kind[kind]):
        raise ClerkError("Fields do not match the action kind")
    if kind in {"click", "double_click", "scroll"}:
        number(action.get("x"), "x", 0, observation.width - 1)
        number(action.get("y"), "y", 0, observation.height - 1)
    if kind == "type":
        value = action.get("text")
        if not isinstance(value, str) or not 1 <= len(value) <= 1000 or any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise ClerkError("Text must contain 1 to 1000 printable characters")
    if kind == "key" and action.get("key") not in KEYS:
        raise ClerkError("Key is outside the supported navigation keys")
    if kind == "scroll":
        number(action.get("delta"), "delta", -600, 600)
    if kind == "wait":
        number(action.get("seconds"), "seconds", 0, 5)
    if kind == "done":
        if not isinstance(action.get("evidence"), str) or not 1 <= len(action["evidence"]) <= 1500:
            raise ClerkError("Completion needs visible evidence for the operator to confirm")
    return action
