import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from .types import ClerkError


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address, engine):
        super().__init__(address, Handler)
        self.engine = engine
        self.token = secrets.token_urlsafe(32)
        self.host_header = "127.0.0.1:" + str(self.server_port)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send(self, code, value, content_type="application/json"):
        body = json.dumps(value).encode() if content_type == "application/json" else value.encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; frame-ancestors 'none'; connect-src 'self'")
        self.end_headers()
        self.wfile.write(body)

    def host_ok(self):
        return self.headers.get("Host") == self.server.host_header

    def authenticated(self):
        return self.host_ok() and secrets.compare_digest(self.headers.get("Authorization", ""), "Bearer " + self.server.token)

    def do_GET(self):
        if not self.host_ok():
            return self.send(403, {"error": "Invalid local host"})
        if self.path.startswith("/api/"):
            if not self.authenticated():
                return self.send(401, {"error": "Local session token required"})
            try:
                if self.path == "/api/status":
                    return self.send(200, self.server.engine.status())
                if self.path == "/api/doctor":
                    return self.send(200, self.server.engine.driver.doctor())
                if self.path == "/api/models":
                    return self.send(200, {"models": self.server.engine.planner.models()})
                if self.path == "/api/apps":
                    allowed = self.server.engine.allowed_apps
                    return self.send(200, {"apps": [a for a in self.server.engine.driver.apps() if a["bundle_id"] in allowed]})
            except Exception as exc:
                return self.send(422, {"error": str(exc)})
            return self.send(404, {"error": "Unknown endpoint"})
        files = {"/": ("index.html", "text/html; charset=utf-8"),
                 "/app.js": ("app.js", "application/javascript"), "/style.css": ("style.css", "text/css")}
        if self.path not in files:
            return self.send(404, {"error": "Not found"})
        filename, mime = files[self.path]
        content = (Path(__file__).parent / "web" / filename).read_text()
        if filename == "index.html":
            content = content.replace("__SESSION_TOKEN__", self.server.token)
        self.send(200, content, mime)

    def do_POST(self):
        if not self.authenticated():
            return self.send(403, {"error": "Local session token required"})
        origin = self.headers.get("Origin")
        if origin and origin != "http://" + self.server.host_header:
            return self.send(403, {"error": "Cross-origin requests are disabled"})
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.send(415, {"error": "Use application/json"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 16384:
                raise ClerkError("Request size is invalid")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ClerkError("Request must be an object")
            engine = self.server.engine
            if self.path == "/api/start":
                result = engine.start(data.get("task"), data.get("bundle_id"), data.get("model"))
            elif self.path == "/api/observe": result = engine.observe()
            elif self.path == "/api/propose": result = engine.propose()
            elif self.path == "/api/approve": result = engine.approve(data.get("proposal_id"))
            elif self.path == "/api/reject": result = engine.reject(data.get("proposal_id"))
            elif self.path == "/api/stop": result = engine.stop()
            else: return self.send(404, {"error": "Unknown endpoint"})
            return self.send(200, result)
        except (ClerkError, ValueError, TypeError) as exc:
            return self.send(422, {"error": str(exc)})
        except Exception:
            return self.send(500, {"error": "Operation failed. Inspect the run state before continuing."})


def serve(engine, port=8768):
    server = LocalServer(("127.0.0.1", port), engine)
    print("OpenClerk console: http://127.0.0.1:" + str(server.server_port), flush=True)
    print("Desktop input requires your review of each action. Screenshots stay in memory.", flush=True)
    server.serve_forever()
