import asyncio
import hashlib
import json
import sqlite3
import uuid
from dataclasses import replace

import pytest
from argon2 import PasswordHasher, Type, extract_parameters
from fastapi.testclient import TestClient

from server.ai.router import AIRouter
from server.app import create_app
from server.config import ConfigurationError, load_settings
from server.database import Database, SCHEMA_VERSION
from server.security.service import SecurityService
from server.security.types import AuthError, OWNER_SCOPES, digest, pkce, token
from tests.ai_helpers import FakeProvider
from tests.auth_helpers import TEST_PASSWORD, fast_hasher, owner_hash, login


class Clock:
    def __init__(self):
        self.now = 2000000000.0
    def __call__(self):
        return self.now
    def advance(self, seconds):
        self.now += seconds


def make_app(settings):
    providers = {name: FakeProvider() for name in ("gemini", "groq", "ollama")}
    app = create_app(settings, ai_router=AIRouter(settings, providers))
    app.state.security.hasher = fast_hasher()
    return app


class SharedLifespanClient(TestClient):
    def __enter__(self):
        self.borrowed = self.app.state.runtime["ready"]
        if self.borrowed:
            self.portal = self.app.state.test_portal
            return self
        result = super().__enter__()
        self.app.state.test_portal = self.portal
        return result

    def __exit__(self, *args):
        if self.borrowed:
            self.close()
            self.portal = None
        else:
            return super().__exit__(*args)


def client_for(app, **kwargs):
    return SharedLifespanClient(app, base_url="http://127.0.0.1:8765", client=("127.0.0.1", 40000), **kwargs)


@pytest.fixture
def secured(settings):
    app = make_app(settings)
    clock = Clock()
    app.state.security.store.clock = clock
    with client_for(app) as client:
        app.state.security.store.create_owner("owner", owner_hash())
        yield app, client, clock


def post(client, path, body=None, **kwargs):
    return client.post(path, json=body, headers={"X-Jarvis-CSRF": client.cookies.get("jarvis_csrf", "")}, **kwargs)


def auth(client):
    response = login(client)
    assert response.status_code == 200
    return response.json()


def pair(client, name="Test Windows", scopes=None):
    verifier = token()
    response = client.post("/api/v1/pairing/requests", json={"device_name": name, "device_type": "windows", "scopes": scopes or ["chat:read", "chat:write"], "code_challenge": pkce(verifier), "code_challenge_method": "S256"})
    assert response.status_code == 200
    return response.json(), verifier


def approve(client, request, scopes=None, **kwargs):
    return post(client, "/api/v1/pairing/requests/" + request["request_id"] + "/decision", {"approve": True, "user_code": request["user_code"], "scopes": scopes or ["chat:read", "chat:write"], **kwargs})


def redeem(app, request, verifier):
    with client_for(app) as native:
        # Keep this request cookie-free; native credentials are only in the body.
        return native.post("/api/v1/pairing/token", json={"grant_type": "urn:ietf:params:oauth:grant-type:device_code", "device_code": request["device_code"], "code_verifier": verifier})


def test_owner_is_single_and_argon2id_with_real_default(settings):
    db = Database(settings.database_path)
    db.initialize()
    service = SecurityService(db, settings)
    service.setup_owner("owner", TEST_PASSWORD)
    encoded = service.store.owner()["password_hash"]
    parameters = extract_parameters(encoded)
    assert parameters.type == Type.ID and parameters.memory_cost >= 65536 and parameters.time_cost >= 3
    assert service.verify(encoded, TEST_PASSWORD) and not service.verify(encoded, "incorrect")
    with pytest.raises(AuthError, match="owner_exists"):
        service.setup_owner("another", TEST_PASSWORD)
    assert TEST_PASSWORD.encode() not in settings.database_path.read_bytes()
    with pytest.raises(AuthError, match="invalid_password"):
        service.validate_password("short")


def test_first_setup_is_cli_only_and_public_status_is_minimal(settings):
    app = make_app(settings)
    with client_for(app) as client:
        assert client.get("/api/v1/auth/status").json() == {"setup_required": True}
        assert client.post("/api/v1/auth/setup", json={"username": "attacker"}).status_code == 401
        assert client.get("/health").json() == {"status": "ok", "service": "jarvis-server"}
        assert client.get("/ready").json() == {"status": "ready", "service": "jarvis-server"}


@pytest.mark.parametrize("path", ["/api/v1/status", "/api/v1/ai/providers", "/api/v1/chat/conversations", "/api/v1/auth/session", "/api/v1/auth/sessions", "/api/v1/devices", "/api/v1/pairing/requests", "/api/v1/security/audit", "/openapi.json", "/api/v1/new-private-route"])
def test_private_routes_default_deny(secured, path):
    _, client, _ = secured
    assert client.get(path).status_code == 401
    assert client.post("/api/v1/chat", json={"message": "private"}).status_code == 401


def test_login_logout_cookies_and_session_metadata(secured):
    app, client, _ = secured
    result = auth(client)
    assert client.get("/api/v1/auth/session").json()["username"] == "owner"
    assert set(result["permissions"]) == OWNER_SCOPES
    saved_access, saved_refresh = client.cookies["jarvis_access"], client.cookies["jarvis_refresh"]
    rows = client.get("/api/v1/auth/sessions").json()["items"]
    assert rows[0]["current"] is True and "access_hash" not in rows[0]
    assert post(client, "/api/v1/auth/logout").status_code == 200
    assert client.get("/api/v1/status").status_code == 401
    with client_for(app) as native:
        assert native.get("/api/v1/status", headers={"Authorization": "Bearer " + saved_access}).status_code == 401
        assert native.post("/api/v1/auth/token", json={"refresh_token": saved_refresh}).status_code == 401


def test_cookie_flags_for_local_http(secured):
    _, client, _ = secured
    client.get("/api/v1/auth/csrf")
    response = post(client, "/api/v1/auth/login", {"username": "owner", "password": TEST_PASSWORD})
    headers = response.headers.get_list("set-cookie")
    for name in ("jarvis_access", "jarvis_refresh"):
        cookie = next(value for value in headers if value.startswith(name + "="))
        assert "HttpOnly" in cookie and "SameSite=strict" in cookie and "Domain=" not in cookie
        assert "; Secure" not in cookie
    assert "Path=/api/v1/auth" in next(value for value in headers if value.startswith("jarvis_refresh="))


def test_cookies_secure_for_real_https_scope(settings):
    app = make_app(replace(settings, allowed_origins=("https://127.0.0.1:8765",)))
    with TestClient(app, base_url="https://127.0.0.1:8765", client=("127.0.0.1", 40000)) as client:
        app.state.security.store.create_owner("owner", owner_hash())
        response = login(client)
        assert response.status_code == 200
        assert all("; Secure" in row for row in response.headers.get_list("set-cookie"))


def test_bad_credentials_are_generic_and_limited(secured):
    app, client, clock = secured
    client.get("/api/v1/auth/csrf")
    for index in range(5):
        response = post(client, "/api/v1/auth/login", {"username": "owner" if index % 2 else "unknown", "password": "incorrect"})
        assert response.status_code == 401 and response.json()["error"]["code"] == "invalid_credentials"
    assert post(client, "/api/v1/auth/login", {"username": "owner", "password": TEST_PASSWORD}).status_code == 429
    clock.advance(301)
    assert post(client, "/api/v1/auth/login", {"username": "owner", "password": TEST_PASSWORD}).status_code == 200
    events = [row["event"] for row in app.state.security.store.audits(100, 0)["items"]]
    assert events.count("login_failed") == 5 and "login_success" in events


def test_csrf_login_write_and_cross_origin(secured):
    _, client, _ = secured
    assert client.post("/api/v1/auth/login", json={"username": "owner", "password": TEST_PASSWORD}).status_code == 403
    auth(client)
    client.headers.pop("X-Jarvis-CSRF", None)
    assert client.post("/api/v1/chat", json={"message": "hello"}).status_code == 403
    assert post(client, "/api/v1/chat", {"message": "hello"}).status_code == 200
    assert client.post("/api/v1/chat", json={"message": "hello"}, headers={"Origin": "https://attacker.example", "X-Jarvis-CSRF": client.cookies["jarvis_csrf"]}).status_code == 403
    assert client.post("/api/v1/auth/login", content="username=owner", headers={"Content-Type": "application/x-www-form-urlencoded"}).status_code == 415
    assert client.get("/api/v1/auth/csrf", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert "access-control-allow-origin" not in client.get("/health").headers


def test_expired_access_refresh_rotation_and_replay_revokes_family(secured):
    app, client, clock = secured
    auth(client)
    old_access, old_refresh = client.cookies["jarvis_access"], client.cookies["jarvis_refresh"]
    clock.advance(301)
    assert client.get("/api/v1/auth/session").status_code == 401
    response = post(client, "/api/v1/auth/refresh")
    assert response.status_code == 200
    fresh_access = client.cookies["jarvis_access"]
    assert fresh_access != old_access and client.cookies["jarvis_refresh"] != old_refresh
    with client_for(app) as native:
        assert native.get("/api/v1/auth/session", headers={"Authorization": "Bearer " + old_access}).status_code == 401
        assert native.post("/api/v1/auth/token", json={"refresh_token": old_refresh}).status_code == 401
        assert native.get("/api/v1/auth/session", headers={"Authorization": "Bearer " + fresh_access}).status_code == 401
    events = [row["event"] for row in app.state.security.store.audits(100, 0)["items"]]
    assert "token_refreshed" in events and "refresh_reuse_detected" in events


def test_browser_replay_with_old_csrf_also_revokes(secured):
    app, client, _ = secured
    auth(client)
    old_refresh, old_csrf = client.cookies["jarvis_refresh"], client.cookies["jarvis_csrf"]
    assert post(client, "/api/v1/auth/refresh").status_code == 200
    with pytest.raises(AuthError):
        app.state.security.store.refresh(old_refresh, digest(old_csrf))
    assert client.get("/api/v1/auth/session").status_code == 401


def test_absolute_session_expiry_cannot_be_extended(secured):
    app, client, clock = secured
    auth(client)
    clock.advance(app.state.settings.session_seconds + 1)
    assert post(client, "/api/v1/auth/refresh").status_code == 401


@pytest.mark.parametrize("revoke", [True, False])
def test_password_change_revoke_policy(secured, revoke):
    _, client, _ = secured
    auth(client)
    new_password = "another-synthetic-passphrase"
    result = post(client, "/api/v1/auth/password", {"current_password": TEST_PASSWORD, "new_password": new_password, "revoke_all_sessions": revoke})
    assert result.status_code == 200 and result.json()["all_sessions_revoked"] is revoke
    assert client.get("/api/v1/auth/session").status_code == (401 if revoke else 200)
    assert login(client, password=TEST_PASSWORD).status_code == 401
    assert login(client, password=new_password).status_code == 200


def test_wrong_password_change_does_not_mutate_credentials(secured):
    _, client, _ = secured
    auth(client)
    assert post(client, "/api/v1/auth/password", {"current_password": "wrong", "new_password": "another-synthetic-passphrase"}).status_code == 401
    assert client.get("/api/v1/auth/session").status_code == 200


def test_browser_relogin_reuses_device_and_revokes_old_session(secured):
    app, client, _ = secured
    first = auth(client)
    old_access = client.cookies["jarvis_access"]
    second = auth(client)
    assert first["device_id"] == second["device_id"] and first["session_id"] != second["session_id"]
    with client_for(app) as native:
        assert native.get("/api/v1/auth/session", headers={"Authorization": "Bearer " + old_access}).status_code == 401


def test_pair_approval_requires_code_proof_and_is_single_use(secured):
    app, client, _ = secured
    auth(client)
    request, verifier = pair(client)
    assert app.state.security.store.pairs()["items"][0]["name"] == "Test Windows"
    assert approve(client, request, user_code="WRONG").status_code == 400
    assert approve(client, request).status_code == 200
    assert approve(client, request).status_code == 409
    assert redeem(app, request, "b" * 43).status_code == 400
    response = redeem(app, request, verifier)
    assert response.status_code == 200
    credentials = response.json()
    assert credentials["token_type"] == "Bearer"
    assert set(credentials["scope"].split()) == {"chat:read", "chat:write"}
    assert redeem(app, request, verifier).status_code == 400
    with client_for(app) as native:
        native.headers["Authorization"] = "Bearer " + credentials["access_token"]
        assert native.get("/api/v1/chat/conversations").status_code == 200
        assert native.post("/api/v1/chat", json={"message": "hello"}).status_code == 200
        assert native.get("/api/v1/devices").status_code == 403
        assert native.get("/api/v1/auth/sessions").status_code == 403
        assert native.get("/api/v1/security/audit").status_code == 403
        assert native.get("/api/v1/ai/providers").status_code == 403
    assert post(client, "/api/v1/pairing/requests/" + request["request_id"] + "/decision", {"approve": False}).status_code == 409


def test_pair_polling_pending_slowdown_expired_and_denied(secured):
    app, client, clock = secured
    auth(client)
    request, verifier = pair(client)
    assert redeem(app, request, verifier).json()["error"]["code"] == "authorization_pending"
    assert redeem(app, request, verifier).json()["error"]["code"] == "slow_down"
    clock.advance(app.state.settings.pairing_seconds + 1)
    assert redeem(app, request, verifier).json()["error"]["code"] == "expired_token"
    assert approve(client, request).status_code == 401  # access also expired
    auth(client)
    second, verifier = pair(client)
    assert post(client, "/api/v1/pairing/requests/" + second["request_id"] + "/decision", {"approve": False}).status_code == 200
    assert redeem(app, second, verifier).json()["error"]["code"] == "access_denied"


def test_pair_device_revocation_blocks_access_and_refresh(secured):
    app, client, _ = secured
    auth(client)
    request, verifier = pair(client)
    assert approve(client, request).status_code == 200
    credentials = redeem(app, request, verifier).json()
    identifier = credentials["device_id"]
    csrf = client.cookies["jarvis_csrf"]
    assert client.patch("/api/v1/devices/" + identifier, json={"name": "Renamed device"}, headers={"X-Jarvis-CSRF": csrf}).status_code == 200
    assert client.post("/api/v1/devices/" + identifier + "/revoke", headers={"X-Jarvis-CSRF": csrf}).status_code == 200
    with client_for(app) as native:
        assert native.get("/api/v1/chat/conversations", headers={"Authorization": "Bearer " + credentials["access_token"]}).status_code == 401
        assert native.post("/api/v1/auth/token", json={"refresh_token": credentials["refresh_token"]}).status_code == 401


def test_least_privilege_and_unmapped_new_route(secured):
    app, client, _ = secured
    @app.get("/api/v1/future-sensitive")
    def future_route():
        return {"sensitive": True}
    auth(client)
    request, verifier = pair(client, scopes=["chat:read"])
    assert approve(client, request, scopes=["chat:read"]).status_code == 200
    credentials = redeem(app, request, verifier).json()
    with client_for(app) as native:
        native.headers["Authorization"] = "Bearer " + credentials["access_token"]
        assert native.get("/api/v1/chat/conversations").status_code == 200
        assert native.post("/api/v1/chat", json={"message": "hello"}).status_code == 403
        assert native.get("/api/v1/future-sensitive").status_code == 403


def test_device_removal_deletes_credentials_but_keeps_conversations_and_audit(secured):
    app, client, _ = secured
    auth(client)
    conversation = post(client, "/api/v1/chat", {"message": "Synthetic preserved conversation"}).json()["conversation_id"]
    request, verifier = pair(client)
    assert approve(client, request).status_code == 200
    credentials = redeem(app, request, verifier).json()
    identifier = credentials["device_id"]
    assert client.delete("/api/v1/devices/" + identifier, headers={"X-Jarvis-CSRF": client.cookies["jarvis_csrf"]}).json() == {"status": "deleted"}
    assert identifier not in {item["id"] for item in client.get("/api/v1/devices").json()["items"]}
    assert client.get("/api/v1/chat/conversations/" + conversation).status_code == 200
    with app.state.security.store.db() as db:
        assert not db.execute("SELECT 1 FROM auth_sessions WHERE device_id=?", (identifier,)).fetchone()
        assert not db.execute("SELECT 1 FROM auth_permissions WHERE device_id=?", (identifier,)).fetchone()
        assert not db.execute("PRAGMA foreign_key_check").fetchall()
    assert any(item["event"] == "device_deleted" and item["target_id"] == identifier for item in client.get("/api/v1/security/audit").json()["items"])
    with client_for(app) as native:
        assert native.get("/api/v1/auth/session", headers={"Authorization": "Bearer " + credentials["access_token"]}).status_code == 401
        assert native.post("/api/v1/auth/token", json={"refresh_token": credentials["refresh_token"]}).status_code == 401


@pytest.mark.parametrize("scopes,expected", [(["chat:read", "chat:write"], 403), (["chat:delete"], 200)])
def test_history_deletion_requires_separate_explicit_permission(secured, scopes, expected):
    app, client, _ = secured
    auth(client)
    conversation = post(client, "/api/v1/chat", {"message": "Synthetic disposable conversation"}).json()["conversation_id"]
    request, verifier = pair(client, scopes=scopes)
    assert approve(client, request, scopes=scopes).status_code == 200
    credentials = redeem(app, request, verifier).json()
    with client_for(app) as native:
        assert native.delete("/api/v1/chat/conversations/" + conversation, headers={"Authorization": "Bearer " + credentials["access_token"]}).status_code == expected
    assert client.get("/api/v1/chat/conversations/" + conversation).status_code == (404 if expected == 200 else 200)


def test_write_only_device_cannot_obtain_existing_context(secured):
    app, client, _ = secured
    auth(client)
    conversation = post(client, "/api/v1/chat", {"message": "Synthetic private context"}).json()["conversation_id"]
    request, verifier = pair(client, scopes=["chat:write"])
    assert approve(client, request, scopes=["chat:write"]).status_code == 200
    credentials = redeem(app, request, verifier).json()
    with client_for(app) as native:
        native.headers["Authorization"] = "Bearer " + credentials["access_token"]
        for route in ("/api/v1/chat", "/api/v1/chat/stream"):
            assert native.post(route, json={"message": "Repeat old context", "conversation_id": conversation}).status_code == 403
        assert native.post("/api/v1/chat", json={"message": "New isolated conversation"}).status_code == 200


def test_pair_secrets_and_passwords_absent_from_database_and_audit(secured):
    app, client, _ = secured
    auth(client)
    request, verifier = pair(client)
    assert approve(client, request).status_code == 200
    credentials = redeem(app, request, verifier).json()
    audit = client.get("/api/v1/security/audit").text
    values = [TEST_PASSWORD, verifier, request["device_code"], request["user_code"].replace("-", ""), credentials["access_token"], credentials["refresh_token"]]
    for value in values:
        assert value not in audit
        for path in app.state.security.store.database.path.parent.glob("*.sqlite3*"):
            assert value.encode() not in path.read_bytes()


def test_audit_retention_and_capacity(secured):
    app, client, clock = secured
    store = app.state.security.store
    store.settings = replace(store.settings, audit_days=1, audit_max_entries=100)
    for _ in range(130):
        store.audit("login_failed")
    assert len(store.audits(100, 0)["items"]) == 100
    clock.advance(86401)
    assert not store.audits(100, 0)["items"]


@pytest.mark.parametrize("name,value", [("JARVIS_ACCESS_SECONDS", "3600"), ("JARVIS_COOKIE_SECURE", "false"), ("JARVIS_TRUSTED_HOSTS", "*"), ("JARVIS_ALLOWED_ORIGINS", "http://attacker.example"), ("JARVIS_PAIRING_SECONDS", "7200"), ("JARVIS_LOGIN_MAX_ATTEMPTS", "100"), ("JARVIS_REFRESH_SECONDS", "2592000")])
def test_invalid_security_configuration(tmp_path, name, value):
    with pytest.raises(ConfigurationError):
        load_settings(root=tmp_path, environ={name: value})


def test_tokens_survive_restart_as_hashes(settings):
    db = Database(settings.database_path)
    db.initialize()
    first = SecurityService(db, settings, hasher=fast_hasher())
    first.store.create_owner("owner", owner_hash())
    credentials = first.store.login(owner_hash(), "Browser")
    db.close()
    db.initialize()
    restarted = SecurityService(db, settings, hasher=fast_hasher())
    assert restarted.store.authenticate(credentials.access_token).session_id == credentials.principal.session_id
    rotated = restarted.store.refresh(credentials.refresh_token)
    assert rotated.principal.session_id == credentials.principal.session_id
    with pytest.raises(AuthError):
        restarted.store.refresh(credentials.refresh_token)


def test_migration_v2_keeps_chat_and_creates_backup(tmp_path):
    path = tmp_path / "existing.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        db.executemany("INSERT INTO schema_migrations(version) VALUES (?)", ((1,), (2,)))
        db.execute("CREATE TABLE chat_conversations(id TEXT PRIMARY KEY,title TEXT,created_at TEXT,updated_at TEXT)")
        db.execute("CREATE TABLE chat_turns(id TEXT PRIMARY KEY,conversation_id TEXT,user_text TEXT,assistant_text TEXT,status TEXT,error_code TEXT,sequence INTEGER)")
        db.execute("INSERT INTO chat_conversations VALUES ('existing','keep','now','now')")
        db.execute("INSERT INTO chat_turns VALUES ('turn','existing','hello','saved answer','completed',NULL,1)")
        db.execute("PRAGMA user_version=2")
    database = Database(path)
    database.initialize()
    assert database.check()
    with database.connection() as db:
        assert db.execute("SELECT assistant_text FROM chat_turns").fetchone()[0] == "saved answer"
        assert db.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION == 5
    backup = next(tmp_path.glob("existing.sqlite3.pre-v5-*.bak"))
    with sqlite3.connect(backup) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 2


def test_concurrent_refresh_detects_replay_transactionally(secured):
    from concurrent.futures import ThreadPoolExecutor
    app, client, _ = secured
    auth(client)
    refresh = client.cookies["jarvis_refresh"]
    def rotate():
        try:
            return app.state.security.store.refresh(refresh)
        except AuthError:
            return None
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: rotate(), range(2)))
    successes = [result for result in results if result is not None]
    assert len(successes) == 1
    with pytest.raises(AuthError):
        app.state.security.store.authenticate(successes[0].access_token)


def test_concurrent_pair_redemption_creates_only_one_device(secured):
    from concurrent.futures import ThreadPoolExecutor
    app, client, _ = secured
    auth(client)
    request, verifier = pair(client)
    assert approve(client, request).status_code == 200
    def consume():
        try:
            return app.state.security.store.redeem_pair(request["device_code"], verifier)
        except AuthError:
            return None
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: consume(), range(2)))
    assert sum(result is not None for result in results) == 1
    assert len(app.state.security.store.devices()["items"]) == 2


def test_pair_request_rate_limit_and_proof_attempt_limit(secured):
    app, client, _ = secured
    auth(client)
    request, verifier = pair(client)
    for _ in range(5):
        assert approve(client, request, user_code="WRONG").status_code == 400
    assert approve(client, request).status_code == 409
    assert redeem(app, request, verifier).json()["error"]["code"] == "access_denied"
    for _ in range(4):
        pair(client)
    response = client.post("/api/v1/pairing/requests", json={"device_name": "test", "device_type": "windows", "code_challenge": pkce(token()), "code_challenge_method": "S256"})
    assert response.status_code == 429


def test_new_devices_cannot_request_administrative_or_future_rights(secured):
    _, client, _ = secured
    for scope in ("admin:devices", "calendar:write", "messages:send"):
        response = client.post("/api/v1/pairing/requests", json={"device_name": "test", "device_type": "windows", "scopes": [scope], "code_challenge": pkce(token()), "code_challenge_method": "S256"})
        assert response.status_code == 422


def test_csrf_can_be_reissued_during_session_and_malformed_values_fail_closed(secured):
    from server.security.gate import csrf_value
    _, client, _ = secured
    auth(client)
    previous = client.cookies["jarvis_csrf"]
    assert client.get("/api/v1/auth/csrf").status_code == 200
    assert client.cookies["jarvis_csrf"] != previous
    assert post(client, "/api/v1/chat", {"message": "hello"}).status_code == 200
    with pytest.raises(AuthError, match="csrf_failed"):
        csrf_value({"headers": [(b"cookie", b"jarvis_csrf=" + b"\xff" * 43), (b"x-jarvis-csrf", b"\xff" * 43)]})


def test_revoked_principal_cannot_finish_a_sensitive_mutation(secured):
    app, client, _ = secured
    result = auth(client)
    store = app.state.security.store
    principal = store.authenticate(client.cookies["jarvis_access"])
    store.revoke_session(result["session_id"], principal)
    with pytest.raises(AuthError):
        store.password(owner_hash(), owner_hash(), principal, True)
    with pytest.raises(AuthError):
        store.change_device(result["device_id"], principal, "changed")


def test_refresh_history_is_bounded_and_pruned_after_revocation(secured):
    app, client, clock = secured
    auth(client)
    store = app.state.security.store
    store.MAX_REFRESH_ROTATIONS = 2
    first = store.refresh(client.cookies["jarvis_refresh"])
    with pytest.raises(AuthError):
        store.refresh(first.refresh_token)
    with pytest.raises(AuthError):
        store.authenticate(first.access_token)
    clock.advance(86401)
    store.prune()
    with store.db() as db:
        assert db.execute("SELECT count(*) FROM auth_refresh_tokens").fetchone()[0] == 0


def test_session_revocation_route_and_safe_names(secured):
    app, client, _ = secured
    owner = auth(client)
    request, verifier = pair(client, name="name'; DROP TABLE auth_users; --")
    assert approve(client, request).status_code == 200
    paired = redeem(app, request, verifier).json()
    csrf = client.cookies["jarvis_csrf"]
    assert client.patch("/api/v1/devices/" + paired["device_id"], json={"name": "<img src=x onerror=alert(1)>"}, headers={"X-Jarvis-CSRF": csrf}).status_code == 200
    assert app.state.security.store.owner()["username"] == "owner"
    assert client.delete("/api/v1/auth/sessions/" + paired["session_id"], headers={"X-Jarvis-CSRF": csrf}).status_code == 200
    assert client.get("/api/v1/auth/session").status_code == 200
    assert client.delete("/api/v1/auth/sessions/" + owner["session_id"], headers={"X-Jarvis-CSRF": csrf}).status_code == 200
    assert client.get("/api/v1/auth/session").status_code == 401


@pytest.mark.parametrize("stream", [False, True])
def test_revocation_stops_active_generation(secured, stream):
    import time
    from concurrent.futures import ThreadPoolExecutor
    app, client, _ = secured
    auth(client)
    provider = FakeProvider(("Gedeeltelijk",), wait=True)
    app.state.chat.router.providers["gemini"] = provider
    principal = app.state.security.store.authenticate(client.cookies["jarvis_access"])
    path = "/api/v1/chat/stream" if stream else "/api/v1/chat"
    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(client.post, path, json={"message": "test", "provider": "gemini"})
        for _ in range(100):
            if provider.waiting.is_set():
                break
            time.sleep(0.01)
        assert provider.waiting.is_set()
        app.state.security.store.revoke_session(principal.session_id, principal)
        response = future.result(timeout=5)
    if stream:
        frames = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
        result = frames[-1]
        assert result["type"] == "done"
    else:
        assert response.status_code == 499
        result = response.json()
    assert result["status"] == "cancelled" and result["error"]["code"] == "authentication_expired"
    assert provider.closed and not app.state.chat.active


def test_frontend_has_no_token_storage_or_html_insertion(secured):
    _, client, _ = secured
    for page in ("/login", "/security"):
        response = client.get(page)
        assert response.status_code == 200 and "'self'" in response.headers["content-security-policy"]
    for name in ("auth", "login", "security"):
        source = client.get("/chat/assets/" + name + ".js").text
        assert "localStorage" not in source and "innerHTML" not in source
    source = client.get("/chat/assets/auth.js").text
    assert "navigator.locks" in source and "X-Jarvis-CSRF" in source


def test_untrusted_plain_http_host_cannot_issue_auth_cookies(settings):
    configured = replace(settings, trusted_hosts=("localhost", "127.0.0.1", "future.example"), allowed_origins=("https://future.example",))
    app = make_app(configured)
    with TestClient(app, base_url="http://future.example", client=("127.0.0.1", 40000)) as client:
        assert client.get("/api/v1/auth/csrf", headers={"X-Forwarded-Proto": "https"}).status_code == 403


def test_setup_owner_cli_is_interactive_one_time_and_does_not_echo_password(settings, monkeypatch, capsys):
    import getpass
    import sys
    import server.__main__ as entry
    monkeypatch.setattr(entry, "load_settings", lambda: settings)
    monkeypatch.setattr(sys, "argv", ["server", "setup-owner"])
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "owner")
    monkeypatch.setattr(getpass, "getpass", lambda _: TEST_PASSWORD)
    assert entry.main() == 0
    assert entry.main() == 2
    captured = capsys.readouterr()
    assert TEST_PASSWORD not in captured.out + captured.err
