from tests.test_security import client_for, make_app, auth, pair, approve, redeem, post
from tests.auth_helpers import owner_hash


def test_paired_client_can_only_inspect_and_revoke_itself(settings):
    app = make_app(settings)
    with client_for(app) as owner:
        app.state.security.store.create_owner("owner", owner_hash())
        principal = auth(owner)
        pending, verifier = pair(owner, scopes=["chat:read"])
        assert approve(owner, pending, scopes=["chat:read"]).status_code == 200
        credentials = redeem(app, pending, verifier).json()
        with client_for(app) as native:
            native.headers["Authorization"] = "Bearer " + credentials["access_token"]
            device = native.get("/api/v1/auth/device").json()
            assert device["id"] == credentials["device_id"] and device["type"] == "windows"
            assert "password_hash" not in device and "user_id" not in device
            assert native.get("/api/v1/devices").status_code == 403
            assert native.post("/api/v1/auth/disconnect", json={"device_id": principal["device_id"]}).status_code == 200
            assert native.get("/api/v1/auth/device").status_code == 401
            assert native.post("/api/v1/auth/token", json={"refresh_token": credentials["refresh_token"]}).status_code == 401
        assert owner.get("/api/v1/auth/session").status_code == 200


def test_self_device_routes_require_authentication_and_cookie_csrf(settings):
    app = make_app(settings)
    with client_for(app) as owner:
        app.state.security.store.create_owner("owner", owner_hash())
        assert owner.get("/api/v1/auth/device").status_code == 401
        assert owner.post("/api/v1/auth/disconnect").status_code == 401
        auth(owner)
        owner.headers.pop("X-Jarvis-CSRF", None)
        assert owner.post("/api/v1/auth/disconnect").status_code == 403
        assert post(owner, "/api/v1/auth/disconnect").status_code == 200
