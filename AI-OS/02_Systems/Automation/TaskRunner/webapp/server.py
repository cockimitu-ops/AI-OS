#!/usr/bin/env python3
"""AI-OS personal web client: a thin HTTP layer over the existing TaskRunner.

Built because Felix wants his day-to-day AI-OS use to happen in a real app
(phone + laptop) instead of this chat/shell session - see the approved plan
at ~/.claude/plans/virtual-tumbling-locket.md for the full reasoning. The
short version: everything that actually does work (the task queue, agent
routing, conversation memory, the money board / DMARC / flip-log data) is
already built and proven by telegram_bridge.py and the scripts/ modules.
This file adds nothing to that - it is only routing, auth, and static file
serving so a browser can reach it.

Stdlib only, same convention as money_board.py/dmarc_prospector.py: this
service never touches Open Interpreter or litellm, so it runs under plain
/usr/bin/python3, not the interpreter-env venv aios_runner.py/telegram_bridge
need.

Binds to the Tailscale interface explicitly (AIOS_WEB_BIND, default the
server's Tailscale IP), never 0.0.0.0 - Tailscale is the real access boundary
here, not a firewall rule that could be misconfigured later. See
webapp/README.md for the PWA-installability HTTPS requirement and how
`tailscale serve` covers it without this file needing to speak TLS itself.
"""
import hmac
import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

WEBAPP_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(WEBAPP_DIR, "static")
TASK_RUNNER_DIR = os.path.dirname(WEBAPP_DIR)
sys.path.insert(0, TASK_RUNNER_DIR)
sys.path.insert(0, os.path.join(TASK_RUNNER_DIR, "scripts"))

import api  # noqa: E402  (needs sys.path set first)

# Tailscale IP first (the intended, only access path), loopback as a
# same-box-only fallback so this is still testable without editing .env.
BIND_HOST = os.environ.get("AIOS_WEB_BIND", "100.64.2.100")
PORT = int(os.environ.get("AIOS_WEB_PORT", "8787"))
TOKEN = os.environ.get("AIOS_WEB_TOKEN", "")

# Every route the frontend actually calls. A plain dict, not a framework -
# a handful of entries is well inside what a manual table can hold clearly.
API_ROUTES = {
    ("GET", "/api/today"): api.get_today,
    # POST because they take a query body; both are reads and change nothing.
    ("POST", "/api/snipes"): api.get_snipes,
    ("POST", "/api/vault-search"): api.get_vault_search,
    ("POST", "/api/vault-page"): api.get_vault_page,
    ("GET", "/api/money-board"): api.get_money_board,
    ("GET", "/api/dmarc-leads"): api.get_dmarc_leads,
    ("GET", "/api/flip-log"): api.get_flip_log,
    ("GET", "/api/downloads"): api.get_downloads,
    ("GET", "/api/uploads"): api.get_uploads,
    ("POST", "/api/chat"): api.post_chat,
    ("POST", "/api/voice-import"): api.post_voice_import,
}

# Routes whose body is file bytes, not JSON. They get (query_dict, raw_bytes)
# instead of a parsed body - json.loads on a chat export would fail, and
# there is no reason to make the client base64 a file to fit a JSON shape.
RAW_ROUTES = {
    ("POST", "/api/upload"): api.post_upload,
}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        # Default logs to stderr with a fixed, unhelpful format; this adds
        # the path, which is the one thing worth seeing in `journalctl`.
        sys.stderr.write(f"{self.address_string()} {fmt % args}\n")

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self):
        """Bearer-token check. Defense in depth on top of Tailscale, not a
        replacement for it - see server.py's module docstring. Constant-time
        compare so response timing can't leak how much of the token matched."""
        if not TOKEN:
            # No token configured: fail closed rather than silently accepting
            # everything, since an unset AIOS_WEB_TOKEN is far more likely to
            # be a deploy mistake than a deliberate "no auth" choice.
            return False
        header = self.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return False
        return hmac.compare_digest(header[len("Bearer "):], TOKEN)

    def _serve_static(self, path):
        """Static files only, no directory listing, no path escaping the
        static/ root - the request path is resolved and then checked to
        still be inside STATIC_DIR before anything is opened."""
        if path == "/":
            path = "/index.html"
        rel = path.lstrip("/")
        full = os.path.normpath(os.path.join(STATIC_DIR, rel))
        if not full.startswith(STATIC_DIR + os.sep) and full != STATIC_DIR:
            self.send_error(403)
            return
        if not os.path.isfile(full):
            self.send_error(404)
            return
        ctype, _ = mimetypes.guess_type(full)
        with open(full, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        # Service worker and manifest must always be revalidated, or an
        # installed PWA can get stuck on a stale app shell after an update -
        # everything else can cache briefly since it's fingerprint-free but
        # rarely changes.
        if rel in ("sw.js", "manifest.json"):
            self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _handle(self, method):
        parsed = urlparse(self.path)
        key = (method, parsed.path)
        if key in RAW_ROUTES:
            if not self._authorized():
                self._send_json(401, {"error": "unauthorized"})
                return
            length = int(self.headers.get("Content-Length", 0) or 0)
            # Refused on the declared length, before a single byte is read:
            # an oversized upload should cost this server nothing at all.
            if length > api.MAX_UPLOAD_BYTES:
                self._send_json(413, {"error": "file too large"})
                return
            raw = self.rfile.read(length) if length else b""
            try:
                status, payload = RAW_ROUTES[key](parse_qs(parsed.query), raw)
            except Exception as e:  # noqa: BLE001 - same reason as below
                sys.stderr.write(f"[!] {method} {parsed.path} failed: {e}\n")
                self._send_json(500, {"error": "internal error"})
                return
            self._send_json(status, payload)
            return
        if key in API_ROUTES:
            if not self._authorized():
                self._send_json(401, {"error": "unauthorized"})
                return
            length = int(self.headers.get("Content-Length", 0) or 0)
            raw = self.rfile.read(length) if length else b""
            try:
                body = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                self._send_json(400, {"error": "invalid JSON body"})
                return
            try:
                status, payload = API_ROUTES[key](body)
            except Exception as e:  # noqa: BLE001 - never let a handler bug
                # take the whole server down; report it, keep serving.
                sys.stderr.write(f"[!] {method} {parsed.path} failed: {e}\n")
                self._send_json(500, {"error": "internal error"})
                return
            self._send_json(status, payload)
            return
        if method == "GET" and parsed.path.startswith("/downloads/"):
            # Unlike the rest of static/ (app code, no secrets), a generated
            # file here can be a real report - a DMARC lead list with names,
            # phone numbers, addresses. Gated like the API, not left open
            # like app.js/style.css. The frontend fetches these with the
            # Authorization header and saves the result as a blob, rather
            # than linking to them directly, precisely so this check has
            # something to check.
            if not self._authorized():
                self.send_error(401, "unauthorized")
                return
            self._serve_static(parsed.path)
            return
        if method == "GET" and not parsed.path.startswith("/api/"):
            self._serve_static(parsed.path)
            return
        self.send_error(404)

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")


def main():
    if not TOKEN:
        print("WARNING: AIOS_WEB_TOKEN is not set in .env - every request "
             "will be rejected until it is. Not starting with a blank/"
             "default token; set a real random value.", file=sys.stderr)
    server = ThreadingHTTPServer((BIND_HOST, PORT), Handler)
    print(f"AI-OS web client listening on {BIND_HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
