#!/usr/bin/env python3
"""Etz Chaim — Claude Max bridge.

Mini HTTP gateway listening on localhost:11435. Receives JSON requests
from the Docker container stub and re-executes them as native subprocess
calls to the host's claude CLI (which has OAuth Max auth).

Request:  POST /exec  { "args": [...claude flags...], "stdin": "prompt text" }
Response: { "stdout": "...", "stderr": "...", "exit_code": 0 }

Bind only on 127.0.0.1 — host.docker.internal resolves to the host loopback,
so Docker containers reach this service without exposing it to the LAN.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOG_PATH = os.path.expanduser("~/.etz-chaim/claude-bridge/bridge.log")
PORT = int(os.environ.get("ETZ_CHAIM_CLAUDE_BRIDGE_PORT", "11435"))
CLAUDE_BIN = shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")
DEFAULT_TIMEOUT = int(os.environ.get("ETZ_CHAIM_CLAUDE_BRIDGE_TIMEOUT", "600"))

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("claude-bridge")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        log.info("%s - %s", self.address_string(), fmt % args)

    def _json(self, status: int, body: dict) -> None:
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json(200, {"ok": True, "claude_bin": CLAUDE_BIN, "exists": os.path.exists(CLAUDE_BIN)})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/exec":
            self._json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            req = json.loads(raw or b"{}")
        except Exception as exc:
            self._json(400, {"error": f"invalid json: {exc}"})
            return

        args = req.get("args", [])
        stdin = req.get("stdin", "")
        timeout = int(req.get("timeout", DEFAULT_TIMEOUT))

        if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            self._json(400, {"error": "args must be list[str]"})
            return

        if not os.path.exists(CLAUDE_BIN):
            self._json(503, {
                "error": "claude binary not found on host",
                "claude_bin": CLAUDE_BIN,
            })
            return

        # Force OAuth Max path — strip any ANTHROPIC_API_KEY from inherited env
        clean_env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        cmd = [CLAUDE_BIN] + args
        log.info("exec: %s (stdin=%d bytes, timeout=%ds)", " ".join(cmd[:6]) + " …", len(stdin), timeout)

        try:
            result = subprocess.run(
                cmd,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=clean_env,
            )
            self._json(200, {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
            })
        except subprocess.TimeoutExpired:
            self._json(200, {
                "stdout": "",
                "stderr": f"[bridge] subprocess timeout after {timeout}s",
                "exit_code": 124,
            })
        except Exception as exc:
            log.exception("exec failed")
            self._json(500, {"error": str(exc)})


def main() -> int:
    log.info("starting on 127.0.0.1:%d (claude=%s)", PORT, CLAUDE_BIN)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("stopping")
    return 0


if __name__ == "__main__":
    sys.exit(main())
