import json
import secrets
import threading
import time

import httpx
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLineEdit

from jarvis_client.api import ApiClient, ClientError
from test_core import credentials
from test_window import window


def test_password_login_and_session_resume_after_client_restart(vault):
    requests = []
    issued = credentials()
    def server(request):
        requests.append(request)
        if request.url.path.endswith("desktop-login"):
            payload = json.loads(request.content)
            assert payload["username"] == "synthetic-owner" and "password" in payload
            assert "cookie" not in request.headers
            return httpx.Response(200, json=issued)
        if request.url.path.endswith("/token"):
            assert json.loads(request.content)["refresh_token"] == issued["refresh_token"]
            return httpx.Response(200, json=credentials())
        return httpx.Response(200, json={"session_id": "synthetic", "permissions": ["chat:read", "chat:write"]})
    origin = "http://127.0.0.1:8765"
    first = ApiClient(origin, vault, transport=httpx.MockTransport(server))
    assert first.login("synthetic-owner", secrets.token_urlsafe(18), "Test Windows", "synthetic-device")["session_id"] == "synthetic"
    first.close()
    second = ApiClient(origin, vault, transport=httpx.MockTransport(server))
    assert second.session()["session_id"] == "synthetic"
    assert sum(request.url.path.endswith("desktop-login") for request in requests) == 1
    assert sum(request.url.path.endswith("/token") for request in requests) == 1
    second.close()


def test_offline_before_send_preserves_saved_login(vault):
    origin = "http://127.0.0.1:8765"
    saved = secrets.token_urlsafe(32)
    vault.save(origin, saved)
    calls = []
    def offline(request):
        calls.append(request)
        raise httpx.ConnectError("synthetic unreachable server")
    api = ApiClient(origin, vault, transport=httpx.MockTransport(offline))
    try:
        api.session()
    except ClientError as error:
        assert error.code == "network_before_send" and error.status == 0
    else:
        raise AssertionError("Expected offline error")
    assert vault.load(origin) == saved
    api.close()


def test_login_form_masks_and_clears_password_and_keeps_public_device_identity(qt, tmp_path, vault):
    app = window(tmp_path, vault)
    main_thread = threading.get_ident()
    seen = []
    identity = app.preferences.installation_id
    class Api:
        origin = "http://127.0.0.1:8765"
        def login(self, username, password, name, device_id):
            seen.append((username, password, device_id, threading.get_ident()))
            return {"session_id": "synthetic", "device_id": identity, "permissions": ["chat:read", "chat:write"]}
        def request(self, method, path, body=None):
            if path.startswith("/api/v1/chat/conversations"):
                return {"items": [], "has_more": False}
            return {"id": identity, "name": "Test", "type": "windows", "trusted": True, "permissions": []}
    app.manager.api = Api()
    app.manager.timer = QTimer(app.manager)
    app.manager.state = "login"
    app.manager.login_pending = False
    app.username.setText("synthetic-owner")
    password = secrets.token_urlsafe(18)
    app.password.setText(password)
    assert app.password.echoMode() == QLineEdit.EchoMode.Password
    app.login()
    assert app.password.text() == ""
    deadline = time.monotonic() + 3
    while (not app.principal or app.jobs.active) and time.monotonic() < deadline:
        qt.processEvents()
        time.sleep(0.01)
    assert app.principal and app.pages.currentIndex() == 0
    assert len(seen) == 1 and seen[0][1] == password and seen[0][2] == identity and seen[0][3] != main_thread
    saved = app.store.path.read_text(encoding="utf-8")
    assert password not in saved and "synthetic-owner" not in saved
    assert json.loads(saved)["installation_id"] == identity
    app.save_settings()
    assert app.preferences.installation_id == identity
    app.manager.timer.stop()
    app.closing = True
    app.tray.hide()
    app.close()
