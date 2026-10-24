"""
Local stand-in for the Meterless Runtime (provider contract v4), for tests and demos when no
real runtime is running. It is NOT the runtime: it serves canned replies.

  python tests/meterless_stub.py --port 8088 --state-dir data/stub_state

On start it writes a fresh token to <state-dir>/proxy-token, as the real runtime does.
"""

from __future__ import annotations

import argparse
import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional

ROUTING_MODES = [
    "meterless/auto", "meterless/fast", "meterless/deep", "meterless/cheap", "meterless/local", "meterless/fusion",
    "meterless/text", "meterless/text.fast", "meterless/vision-xl.deep",  # the last one is a class Archus doesn't know
    "not-a-routing-mode",  # must be dropped by the client
]


class StubState:
    def __init__(self, token: str, models_status: Optional[int] = None):
        self.token = token
        self.models_status = models_status  # force a /v1/models status (e.g. 500) to test "offline"
        self.requests: List[Dict[str, Any]] = []


def make_handler(state: StubState):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # silent: never echo headers or tokens
            pass

        def _send(self, code: int, body: Dict[str, Any]) -> None:
            data = json.dumps(body).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _record(self, body: Any = None) -> Dict[str, Any]:
            auth = self.headers.get("Authorization", "")
            entry = {
                "path": self.path,
                "authorized": auth == f"Bearer {state.token}" and state.token != "rt-local",
                "has_bearer": auth.startswith("Bearer "),
                "meterless_app": self.headers.get("meterless-app"),
                "meterless_scope": self.headers.get("meterless-scope"),
                "body": body,
            }
            state.requests.append(entry)
            return entry

        def _check(self, entry: Dict[str, Any]) -> bool:
            if not entry["meterless_app"]:
                self._send(400, {"error": "meterless-app header required"})
                return False
            if not entry["authorized"]:
                self._send(401, {"error": "unauthorized"})
                return False
            return True

        def do_GET(self):
            if self.path == "/healthz":
                self._record()
                return self._send(200, {"ok": True})
            if self.path == "/v1/models":
                entry = self._record()
                if state.models_status:
                    return self._send(state.models_status, {"error": "forced"})
                if not self._check(entry):
                    return
                return self._send(200, {"object": "list", "data": [{"id": m, "object": "model"} for m in ROUTING_MODES]})
            self._send(404, {"error": "not found"})

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}")
            entry = self._record(body)
            if self.path != "/v1/chat/completions":
                return self._send(404, {"error": "not found"})
            if not self._check(entry):
                return
            if entry["meterless_scope"] != "user":
                return self._send(400, {"error": "meterless-scope: user required on chat"})
            if not str(body.get("model", "")).startswith("meterless/"):
                return self._send(400, {"error": "model must be a meterless/* routing mode"})
            messages = body.get("messages", [])
            if not all(isinstance(m.get("content"), str) for m in messages):
                return self._send(400, {"error": "plain text requests must send content as a string"})
            last = messages[-1]["content"] if messages else ""
            self._send(200, {
                "id": "chatcmpl-stub",
                "object": "chat.completion",
                "created": 0,
                "model": body["model"],
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": f"Stub reply to: {last}"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            })

    return Handler


def start_stub(port: int = 0, token: Optional[str] = None, host: str = "127.0.0.1",
               models_status: Optional[int] = None):
    """Start in a background thread. Returns (server, state); server.server_address[1] is the port."""
    state = StubState(token or secrets.token_urlsafe(24), models_status)
    server = ThreadingHTTPServer((host, port), make_handler(state))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, state


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8088)
    parser.add_argument("--state-dir", required=True, help="the stub writes its token to <state-dir>/proxy-token")
    args = parser.parse_args()
    token = secrets.token_urlsafe(24)
    state_dir = Path(args.state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "proxy-token").write_text(token, encoding="utf-8")
    server, _ = start_stub(args.port, token)
    print(f"Meterless Runtime STUB on http://127.0.0.1:{args.port}/v1 (token written to {state_dir / 'proxy-token'})", flush=True)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
