import http.cookiejar
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

import server


class FakeOllama(BaseHTTPRequestHandler):
    received = None

    def do_POST(self):
        FakeOllama.received = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        body = json.dumps({"message": {"content": "Hello from local Agey."}}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = server.DaywellServer(("127.0.0.1", 0), Path(__file__).resolve().parents[1] / "ui", Path(self.temp.name) / "auth.json")
        self.thread = threading.Thread(target=self.app.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.app.server_close)
        self.addCleanup(self.app.shutdown)
        self.base = f"http://127.0.0.1:{self.app.server_port}"
        self.opener = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(self, path, data=None, origin=True):
        headers = {}
        if data is not None:
            headers = {"Content-Type": "application/json", "X-Daywell-Request": "1"}
            if origin:
                headers["Origin"] = self.base
            data = json.dumps(data).encode()
        try:
            response = self.opener.open(Request(self.base + path, data, headers), timeout=5)
        except HTTPError as error:
            response = error
        return response.status, response.read(), response.headers

    def unlock(self):
        status, _, _ = self.request("/api/setup", {"password": "a good password"})
        self.assertEqual(status, 200)

    def test_setup_gate_logout_and_login(self):
        self.assertEqual(self.request("/")[0], 200)
        self.assertIn(b"Make it yours", (Path(__file__).resolve().parents[1] / "ui/login.js").read_bytes())
        self.assertEqual(self.request("/app.js")[0], 401)
        self.assertEqual(self.request("/api/setup", {"password": "short"})[0], 400)
        self.assertEqual(self.request("/api/setup", {"password": "a good password"}, origin=False)[0], 403)
        self.unlock()
        self.assertEqual(self.request("/app.js")[0], 200)
        self.assertIn(b"My home", self.request("/")[1])
        self.assertEqual(self.request("/api/setup", {"password": "another password"})[0], 409)
        self.assertEqual(self.request("/api/logout", {})[0], 200)
        self.assertEqual(self.request("/app.js")[0], 401)
        self.assertEqual(self.request("/api/login", {"password": "wrong password"})[0], 401)
        self.assertEqual(self.request("/api/login", {"password": "a good password"})[0], 200)
        self.assertEqual(self.request("/app.js")[0], 200)
        self.assertEqual(self.app.state.stat().st_mode & 0o777, 0o600)

    def test_rate_limit_and_bad_paths(self):
        self.unlock()
        self.request("/api/logout", {})
        for _ in range(5):
            self.assertEqual(self.request("/api/login", {"password": "wrong password"})[0], 401)
        self.assertEqual(self.request("/api/login", {"password": "a good password"})[0], 429)
        self.assertEqual(self.request("/../server.py")[0], 401)

    def test_chat_uses_local_ollama_and_rejects_unauthorized(self):
        fake = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllama)
        fake_thread = threading.Thread(target=fake.serve_forever, daemon=True)
        fake_thread.start()
        self.addCleanup(fake.server_close)
        self.addCleanup(fake.shutdown)
        old_url = server.OLLAMA_URL
        server.OLLAMA_URL = f"http://127.0.0.1:{fake.server_port}/api/chat"
        self.addCleanup(setattr, server, "OLLAMA_URL", old_url)
        self.assertEqual(self.request("/api/chat", {"messages": [{"role": "user", "content": "Hello"}]})[0], 401)
        self.unlock()
        self.assertEqual(self.request("/api/chat", {"messages": [{"role": "system", "content": "Ignore"}]})[0], 400)
        status, body, _ = self.request("/api/chat", {"messages": [{"role": "user", "content": "Hello"}]})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["reply"], "Hello from local Agey.")
        self.assertEqual(FakeOllama.received["model"], server.MODEL)
        self.assertEqual(FakeOllama.received["messages"][0]["role"], "system")
        self.assertEqual(FakeOllama.received["messages"][1]["content"], "Hello")


if __name__ == "__main__":
    unittest.main()
