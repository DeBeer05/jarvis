"""Real TCP/process restart test; isolated account/database, no live AI calls."""
import http.cookiejar
import json
import os
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path

from server.chat_store import ChatStore
from server.config import load_settings
from server.database import Database
from server.security.store import SecurityStore
from server.security.types import pkce, token
from tests.auth_helpers import TEST_PASSWORD, owner_hash

ROOT = Path(__file__).resolve().parents[1]
FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def test_real_auth_pairing_revocation_and_restart(tmp_path):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    configuration = {"JARVIS_DATABASE_PATH": str(tmp_path / "isolated.sqlite3"), "JARVIS_LOG_PATH": str(tmp_path / "server.log"), "JARVIS_RUNTIME_DIR": str(tmp_path / "run"), "JARVIS_PORT": str(port), "GEMINI_API_KEY": "", "GROQ_API_KEY": ""}
    settings = load_settings(root=tmp_path, environ=configuration)
    database = Database(settings.database_path)
    database.initialize()
    store = SecurityStore(database, settings)
    store.create_owner("owner", owner_hash())
    history = ChatStore(database)
    cid, _ = history.start(str(__import__("uuid").uuid4()), None, "Synthetische bewaarde tekst")
    env = {key: value for key, value in os.environ.items() if not key.startswith("JARVIS_") and key not in ("GEMINI_API_KEY", "GROQ_API_KEY")}
    env.update(configuration)
    env["JARVIS_ALLOWED_ORIGINS"] = f"http://127.0.0.1:{port},http://localhost:{port}"
    base = f"http://127.0.0.1:{port}"

    @contextmanager
    def running_server():
        with (tmp_path / "console.log").open("a", encoding="utf-8") as output:
            process = subprocess.Popen([sys.executable, "-m", "server"], cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT, creationflags=FLAGS)
            try:
                ready = subprocess.run([sys.executable, "-m", "server", "status", "--wait", "10"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=15, creationflags=FLAGS)
                assert ready.returncode == 0, ready.stdout
                yield
            finally:
                stopped = subprocess.run([sys.executable, "-m", "server", "stop"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=15, creationflags=FLAGS)
                assert stopped.returncode == 0
                assert process.wait(timeout=10) == 0

    jar = http.cookiejar.CookieJar()
    browser = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPCookieProcessor(jar))
    native = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(path, body=None, method=None, *, client=browser, bearer=None):
        headers = {}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if bearer:
            headers["Authorization"] = "Bearer " + bearer
        elif client is browser:
            csrf = next((cookie.value for cookie in jar if cookie.name == "jarvis_csrf"), "")
            headers["X-Jarvis-CSRF"] = csrf
        req = urllib.request.Request(base + path, json.dumps(body).encode() if body is not None else None, headers, method=method)
        try:
            with client.open(req, timeout=5) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    with running_server():
        assert request("/health", client=native)[0] == 200
        assert request("/api/v1/chat/conversations", client=native)[0] == 401
        assert request("/api/v1/auth/csrf")[0] == 200
        status, principal = request("/api/v1/auth/login", {"username": "owner", "password": TEST_PASSWORD})
        assert status == 200
        assert request("/api/v1/chat/conversations/" + cid)[1]["turns"][0]["user_text"] == "Synthetische bewaarde tekst"
        verifier = token()
        status, pair = request("/api/v1/pairing/requests", {"device_name": "Temporary TCP device", "device_type": "android", "scopes": ["chat:read"], "code_challenge": pkce(verifier), "code_challenge_method": "S256"}, client=native)
        assert status == 200 and "?" not in pair["verification_uri"]
        assert request("/api/v1/pairing/requests/" + pair["request_id"] + "/decision", {"approve": True, "user_code": pair["user_code"], "scopes": ["chat:read"]})[0] == 200
        status, paired = request("/api/v1/pairing/token", {"grant_type": "urn:ietf:params:oauth:grant-type:device_code", "device_code": pair["device_code"], "code_verifier": verifier}, client=native)
        assert status == 200
        assert request("/api/v1/chat/conversations", client=native, bearer=paired["access_token"])[0] == 200
        assert request("/api/v1/devices", client=native, bearer=paired["access_token"])[0] == 403
        assert request("/api/v1/devices/" + paired["device_id"] + "/revoke", method="POST")[0] == 200
        assert request("/api/v1/chat/conversations", client=native, bearer=paired["access_token"])[0] == 401
        assert request("/api/v1/auth/refresh", method="POST")[0] == 200
    with running_server():
        assert request("/api/v1/auth/session")[1]["session_id"] == principal["session_id"]
        assert request("/api/v1/chat/conversations/" + cid)[0] == 200
        events = request("/api/v1/security/audit")[1]["items"]
        assert {"login_success", "pairing_approved", "device_paired", "device_revoked", "token_refreshed"} <= {row["event"] for row in events}
        assert request("/api/v1/auth/logout", method="POST")[0] == 200
        assert request("/api/v1/auth/session")[0] == 401
    log = (tmp_path / "server.log").read_text(encoding="utf-8")
    for value in (TEST_PASSWORD, verifier, pair["device_code"], pair["user_code"], paired["access_token"], paired["refresh_token"]):
        assert value not in log
