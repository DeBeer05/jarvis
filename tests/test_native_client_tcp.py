import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from tests.auth_helpers import TEST_PASSWORD

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "desktop-client"))
from jarvis_client.api import ApiClient, ClientError


class TemporaryVault:
    def __init__(self):
        self.values = {}
    def load(self, origin):
        return self.values.get(origin)
    def save(self, origin, value):
        self.values[origin] = value
    def delete(self, origin):
        self.values.pop(origin, None)


def test_native_client_true_tcp_pair_chat_history_refresh_and_revoke(tmp_path):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    with (tmp_path / "console.log").open("w", encoding="utf-8") as output:
        process = subprocess.Popen([sys.executable, "-m", "tests.client_test_server", str(tmp_path), str(port)], stdout=output, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        try:
            with httpx.Client(base_url=origin, trust_env=False) as owner:
                deadline = time.monotonic() + 10
                while True:
                    try:
                        if owner.get("/health").status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    assert time.monotonic() < deadline and process.poll() is None
                    time.sleep(0.1)
                owner.get("/api/v1/auth/csrf")
                response = owner.post("/api/v1/auth/login", json={"username": "owner", "password": TEST_PASSWORD}, headers={"X-Jarvis-CSRF": owner.cookies["jarvis_csrf"]})
                assert response.status_code == 200
                vault, clock = TemporaryVault(), [100.0]
                api = ApiClient(origin, vault, clock=lambda: clock[0])
                try:
                    api.probe()
                    public = api.begin_pair("Synthetic native TCP", delete=True)
                    pending = owner.get("/api/v1/pairing/requests").json()["items"][0]
                    approved = owner.post("/api/v1/pairing/requests/" + pending["id"] + "/decision", json={"approve": True, "user_code": public["user_code"], "scopes": ["chat:read", "chat:write", "chat:delete", "status:read"]}, headers={"X-Jarvis-CSRF": owner.cookies["jarvis_csrf"]})
                    assert approved.status_code == 200
                    clock[0] += 6
                    principal = api.poll_pair()
                    assert api.request("GET", "/api/v1/auth/device")["type"] == "windows"
                    events = []
                    assert api.stream("Synthetic request", None, "auto", events.append)["completed"]
                    cid = events[0]["conversation_id"]
                    assert api.request("GET", "/api/v1/chat/conversations/" + cid)["turns"][0]["status"] == "completed"
                    api.deadline = 0
                    assert api.session()["session_id"] == principal["session_id"]
                    assert api.request("DELETE", "/api/v1/chat/conversations/" + cid)["status"] == "deleted"
                    assert api.logout(revoke_device=True)["status"] == "revoked"
                    with pytest.raises(ClientError):
                        api.session()
                    assert owner.get("/api/v1/auth/session").status_code == 200
                finally:
                    api.close()
        finally:
            process.terminate()
            process.wait(timeout=10)
