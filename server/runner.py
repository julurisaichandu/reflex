"""Sandbox runner: executes verifications on a host that has Docker, for a marketplace deployed where Docker is not.

    SANDBOX_TOKEN=<secret> uv run python -m server.runner      # listens on 127.0.0.1:8787
    # marketplace side: SANDBOX_URL=https://<tunnel>/run SANDBOX_TOKEN=<same secret>
"""

import hmac
import json
import logging
import os
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from dotenv import load_dotenv

from server import sandbox

MAX_BODY_BYTES = 1024 * 1024
log = logging.getLogger("reflex.runner")


class Handler(BaseHTTPRequestHandler):
    def _reply(self, status: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._reply(200 if self.path == "/health" else 404, {"ok": self.path == "/health"})

    def do_POST(self):
        token = os.environ["SANDBOX_TOKEN"]
        supplied = self.headers.get("Authorization", "").removeprefix("Bearer ")
        if self.path != "/run" or not hmac.compare_digest(supplied.encode(), token.encode()):
            return self._reply(403, {"error": "forbidden"})
        length = int(self.headers.get("Content-Length") or 0)
        if not 0 < length <= MAX_BODY_BYTES:
            return self._reply(413, {"error": "body too large"})
        try:
            req = json.loads(self.rfile.read(length))
            if req["fixture"] not in sandbox.FIXTURES.values():
                return self._reply(400, {"error": "unknown fixture"})
            result = sandbox.run_local(req["fixture"], req["solution_files"], req["tests"])
        except sandbox.SandboxUnavailable:
            log.exception("sandbox unavailable")
            return self._reply(503, {"error": "sandbox unavailable"})
        except (KeyError, TypeError, ValueError):
            return self._reply(400, {"error": "bad request"})
        self._reply(200, {"fixture": result.fixture, "duration_ms": result.duration_ms, "runs": [asdict(r) for r in result.runs]})


if __name__ == "__main__":
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    if not os.environ.get("SANDBOX_TOKEN"):
        raise SystemExit("set SANDBOX_TOKEN to a long random secret")
    host, port = os.environ.get("RUNNER_HOST", "127.0.0.1"), int(os.environ.get("RUNNER_PORT", "8787"))
    log.info("sandbox runner on http://%s:%d/run", host, port)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
