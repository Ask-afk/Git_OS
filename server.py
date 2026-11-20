#!/usr/bin/env python3
"""Loopback-only Daywell UI, password gate, and local Ollama bridge."""

import argparse
import hashlib
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import os
from pathlib import Path
import secrets
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SESSION_SECONDS = 30 * 60
MAX_BODY = 16 * 1024
MODEL = os.environ.get("DAYWELL_OLLAMA_MODEL", "gemma3:1b")
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
SYSTEM_PROMPT = (
    "You are Agey, a warm, patient companion on a senior's tablet. "
    "Use plain language and short, helpful replies. Be honest when uncertain. "
    "Do not claim to make calls, contact people, set reminders, or access private data. "
    "For urgent medical or safety concerns, advise using a telephone to reach local emergency services or a trusted person."
)


class DaywellServer(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(self, address, ui, state):
        super().__init__(address, DaywellHandler)
        self.ui = Path(ui).resolve()
        self.state = Path(state)
        self.lock = threading.Lock()
        self.sessions = {}
        self.failures = {}

    def has_password(self):
        return self.state.is_file()

    def save_password(self, password):
        salt = secrets.token_bytes(16)
        digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
        self.state.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(self.state, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as output:
            json.dump({"salt": salt.hex(), "hash": digest.hex()}, output)

    def verify_password(self, password):
        try:
            record = json.loads(self.state.read_text())
            actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(record["salt"]), n=16384, r=8, p=1)
            return hmac.compare_digest(actual, bytes.fromhex(record["hash"]))
        except (OSError, ValueError, KeyError):
            return False


class DaywellHandler(BaseHTTPRequestHandler):
    server_version = "Daywell/1.0"

    def log_message(self, format, *args):
        # Avoid writing chat text, passwords, and cookies to service logs.
        pass

    def send_data(self, status, body, content_type="application/json; charset=utf-8", cookie=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

    def host_ok(self):
        return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

    def session(self):
        jar = SimpleCookie()
        try:
            jar.load(self.headers.get("Cookie", ""))
            token = jar["daywell_session"].value
        except (KeyError, ValueError):
            return None
        with self.server.lock:
            expiry = self.server.sessions.get(token, 0)
            if expiry <= time.monotonic():
                self.server.sessions.pop(token, None)
                return None
            self.server.sessions[token] = time.monotonic() + SESSION_SECONDS
        return token

    def do_GET(self):
        if not self.host_ok():
            return self.send_data(HTTPStatus.BAD_REQUEST, {"error": "Invalid host"})
        path = self.path.split("?", 1)[0]
        if path == "/health":
            return self.send_data(HTTPStatus.OK, {"ok": True})
        authenticated = bool(self.session())
        if path == "/api/status":
            return self.send_data(HTTPStatus.OK, {"setup": not self.server.has_password(), "authenticated": authenticated})
        if path == "/":
            path = "/index.html" if authenticated else "/login.html"
        elif path in ("/login.html", "/login.js", "/login.css"):
            pass
        elif not authenticated:
            return self.send_data(HTTPStatus.UNAUTHORIZED, {"error": "Unlock Daywell first"})
        if path.startswith("/api/"):
            return self.send_data(HTTPStatus.NOT_FOUND, {"error": "Not found"})
        relative = path.lstrip("/")
        file = (self.server.ui / relative).resolve()
        if not file.is_relative_to(self.server.ui) or not file.is_file():
            return self.send_data(HTTPStatus.NOT_FOUND, {"error": "Not found"})
        types = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".jpg": "image/jpeg", ".wav": "audio/wav", ".png": "image/png"}
        return self.send_data(HTTPStatus.OK, file.read_bytes(), types.get(file.suffix, "application/octet-stream"))

    def do_POST(self):
        if not self.host_ok() or self.headers.get("Origin") != f"http://127.0.0.1:{self.server.server_port}" or self.headers.get("X-Daywell-Request") != "1":
            return self.send_data(HTTPStatus.FORBIDDEN, {"error": "Request rejected"})
        if self.headers.get("Content-Type", "").split(";", 1)[0] != "application/json":
            return self.send_data(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "Expected JSON"})
        try:
            length = int(self.headers.get("Content-Length", ""))
            if not 0 <= length <= MAX_BODY:
                raise ValueError()
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError()
        except (ValueError, json.JSONDecodeError):
            return self.send_data(HTTPStatus.BAD_REQUEST, {"error": "Invalid request"})
        path = self.path
        if path in ("/api/setup", "/api/login"):
            password = data.get("password")
            if not isinstance(password, str) or len(password) > 256:
                return self.send_data(HTTPStatus.BAD_REQUEST, {"error": "Invalid password"})
            with self.server.lock:
                now = time.monotonic()
                if self.server.failures.get("local", (0, 0))[1] > now:
                    return self.send_data(HTTPStatus.TOO_MANY_REQUESTS, {"error": "Please wait before trying again"})
                if path == "/api/setup":
                    if self.server.has_password():
                        return self.send_data(HTTPStatus.CONFLICT, {"error": "Password already set"})
                    if len(password) < 8:
                        return self.send_data(HTTPStatus.BAD_REQUEST, {"error": "Use at least 8 characters"})
                    try:
                        self.server.save_password(password)
                    except FileExistsError:
                        return self.send_data(HTTPStatus.CONFLICT, {"error": "Password already set"})
                elif not self.server.verify_password(password):
                    count = self.server.failures.get("local", (0, 0))[0] + 1
                    self.server.failures["local"] = (count, now + 30 if count >= 5 else 0)
                    return self.send_data(HTTPStatus.UNAUTHORIZED, {"error": "Incorrect password"})
                self.server.failures.pop("local", None)
                token = secrets.token_urlsafe(32)
                self.server.sessions[token] = now + SESSION_SECONDS
            cookie = f"daywell_session={token}; HttpOnly; SameSite=Strict; Path=/"
            return self.send_data(HTTPStatus.OK, {"ok": True}, cookie=cookie)
        token = self.session()
        if not token:
            return self.send_data(HTTPStatus.UNAUTHORIZED, {"error": "Unlock Daywell first"})
        if path == "/api/logout":
            with self.server.lock:
                self.server.sessions.pop(token, None)
            return self.send_data(HTTPStatus.OK, {"ok": True}, cookie="daywell_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")
        if path == "/api/chat":
            messages = data.get("messages")
            if not isinstance(messages, list) or not 1 <= len(messages) <= 12:
                return self.send_data(HTTPStatus.BAD_REQUEST, {"error": "Send a message to Agey"})
            clean = []
            for item in messages:
                if not isinstance(item, dict) or item.get("role") not in ("user", "assistant") or not isinstance(item.get("content"), str) or not 1 <= len(item["content"]) <= 2000:
                    return self.send_data(HTTPStatus.BAD_REQUEST, {"error": "Invalid message"})
                clean.append({"role": item["role"], "content": item["content"]})
            if clean[-1]["role"] != "user":
                return self.send_data(HTTPStatus.BAD_REQUEST, {"error": "Last message must be yours"})
            payload = json.dumps({"model": MODEL, "stream": False, "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *clean], "options": {"num_predict": 180}}).encode()
            request = Request(OLLAMA_URL, payload, {"Content-Type": "application/json"})
            try:
                with urlopen(request, timeout=90) as response:
                    result = json.load(response)
                answer = result["message"]["content"].strip()
                if not answer:
                    raise ValueError("Empty response")
            except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
                return self.send_data(HTTPStatus.BAD_GATEWAY, {"error": f"Agey is unavailable. Check that Ollama is running and {MODEL} is installed."})
            return self.send_data(HTTPStatus.OK, {"reply": answer[:4000]})
        return self.send_data(HTTPStatus.NOT_FOUND, {"error": "Not found"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ui", type=Path, default=Path(__file__).parent / "ui")
    parser.add_argument("--state", type=Path, default=Path.home() / ".local/share/daywell/auth.json")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    DaywellServer(("127.0.0.1", args.port), args.ui, args.state).serve_forever()


if __name__ == "__main__":
    main()
