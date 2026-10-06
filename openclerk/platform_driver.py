import threading
import time
from dataclasses import dataclass
from .types import ClerkError, Observation, validate_action


@dataclass(frozen=True)
class DesktopWindow:
    app_id: str
    window_id: int
    process_id: int
    name: str
    bounds: dict


class PlatformDriver:
    """Shared policy for native Windows and Linux backends."""
    def __init__(self, backend):
        self.backend = backend
        self.lock = threading.RLock()

    def close(self):
        close = getattr(self.backend, 'close', None)
        if close: close()

    def doctor(self): return self.backend.doctor()

    def apps(self):
        return [{"name": w.name, "bundle_id": w.app_id} for w in self.backend.windows()]

    def target(self, app_id):
        windows = [w for w in self.backend.windows() if w.app_id == app_id]
        if len(windows) != 1:
            raise ClerkError("Target must have exactly one visible application window")
        return windows[0]

    def observe(self, app_id):
        with self.lock:
            window = self.target(app_id)
            self.backend.focus(window)
            if self.backend.foreground() != window.window_id:
                raise ClerkError("Approved window is not in the foreground")
            png = self.backend.capture(window)
            return Observation(app_id, window.window_id, window.bounds,
                               int(window.bounds['width']), int(window.bounds['height']), png,
                               process_id=window.process_id)

    def execute(self, app_id, observation, action, stopped):
        with self.lock:
            action = validate_action(action, observation)
            if action['kind'] in {'done', 'handoff'}:
                raise ClerkError("Result confirmations do not post native input")
            fresh = self.observe(app_id)
            if fresh.fingerprint != observation.fingerprint:
                raise ClerkError("Window identity, geometry or screenshot changed before input")
            if stopped(): raise ClerkError("Run stopped before input")
            window = self.target(app_id)
            if self.backend.foreground() != window.window_id:
                raise ClerkError("Foreground changed before input")
            self.backend.input(window, action)
            time.sleep(0.15)
            return {"ok": True, "input_posted": True}


def make_driver(platform, bridge):
    if platform == 'darwin':
        from .driver import MacDriver
        return MacDriver(bridge)
    if platform == 'win32':
        from .windows import WindowsBackend
        return PlatformDriver(WindowsBackend())
    if platform.startswith('linux'):
        from .linux import X11Backend
        return PlatformDriver(X11Backend())
    raise ClerkError("Supported platforms are macOS, Windows, and Linux with X11")
