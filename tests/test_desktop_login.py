from uuid import uuid4

from tests.test_security import client_for, make_app, auth
from tests.auth_helpers import TEST_PASSWORD, owner_hash


def body(device=None, password=TEST_PASSWORD, username="owner"):
    return {"username": username, "password": password, "device_name": "Synthetic Windows", "device_id": device or str(uuid4())}


def test_direct_desktop_password_login_has_no_approval_and_minimal_rights(settings):
    app = make_app(settings)
    with client_for(app) as native:
        app.state.security.store.create_owner("owner", owner_hash())
        response = native.post("/api/v1/auth/desktop-login", json=body())
        assert response.status_code == 200 and "set-cookie" not in response.headers
        credentials = response.json()
        assert set(credentials["scope"].split()) == {"chat:read", "chat:write", "chat:delete", "status:read"}
        assert not app.state.security.store.pairs()["items"]
        native.headers["Authorization"] = "Bearer " + credentials["access_token"]
        assert native.get("/api/v1/auth/device").json()["type"] == "windows"
        session = native.get("/api/v1/auth/session").json()
        assert session["session_expires_at"] - app.state.security.store.clock() > 29 * 86400
        assert native.get("/api/v1/devices").status_code == 403
        assert native.get("/api/v1/security/audit").status_code == 403
        assert native.get("/api/v1/chat/conversations").status_code == 200
        with app.state.security.store.db() as db:
            assert db.execute("SELECT count(*) FROM auth_pairing").fetchone()[0] == 0


def test_desktop_login_uses_existing_generic_errors_and_bruteforce_limit(settings):
    app = make_app(settings)
    with client_for(app) as native:
        app.state.security.store.create_owner("owner", owner_hash())
        for index in range(5):
            response = native.post("/api/v1/auth/desktop-login", json=body(password="incorrect", username="owner" if index % 2 else "unknown"))
            assert response.status_code == 401 and response.json()["error"]["code"] == "invalid_credentials"
            assert "incorrect" not in response.text and "unknown" not in response.text
        assert native.post("/api/v1/auth/desktop-login", json=body()).status_code == 429
        assert not app.state.security.store.devices()["items"]


def test_password_login_reuses_installation_reauthorizes_after_revoke_and_invalidates_old_session(settings):
    app = make_app(settings)
    with client_for(app) as native:
        app.state.security.store.create_owner("owner", owner_hash())
        payload = body()
        first = native.post("/api/v1/auth/desktop-login", json=payload).json()
        native.headers["Authorization"] = "Bearer " + first["access_token"]
        assert native.post("/api/v1/auth/disconnect").status_code == 200
        assert native.get("/api/v1/auth/session").status_code == 401
        second = native.post("/api/v1/auth/desktop-login", json=payload).json()
        assert second["device_id"] == first["device_id"] == payload["device_id"]
        assert second["session_id"] != first["session_id"]
        assert len(app.state.security.store.devices()["items"]) == 1
        assert native.post("/api/v1/auth/token", json={"refresh_token": first["refresh_token"]}).status_code == 401
        native.headers["Authorization"] = "Bearer " + second["access_token"]
        assert native.get("/api/v1/auth/session").status_code == 200


def test_native_password_route_rejects_browser_cookie_sessions_and_cross_site(settings):
    app = make_app(settings)
    with client_for(app) as owner:
        app.state.security.store.create_owner("owner", owner_hash())
        auth(owner)
        assert owner.post("/api/v1/auth/desktop-login", json=body()).status_code == 403
        assert owner.post("/api/v1/auth/desktop-login", json=body(), headers={"Origin": "https://attacker.example"}).status_code == 403
        assert owner.get("/api/v1/auth/session").status_code == 200


def test_native_password_cannot_replace_a_browser_device(settings):
    app = make_app(settings)
    with client_for(app) as owner:
        app.state.security.store.create_owner("owner", owner_hash())
        browser = auth(owner)
        with client_for(app) as native:
            assert native.post("/api/v1/auth/desktop-login", json=body(device=browser["device_id"])).status_code == 409
        assert owner.get("/api/v1/auth/session").status_code == 200
