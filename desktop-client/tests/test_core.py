import json
import os
import secrets
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from jarvis_client.api import ApiClient, ClientError, challenge
from jarvis_client.connection import backoff
from jarvis_client.platform_services import LocalAgent, NotificationCenter, Startup
from jarvis_client.settings import Preferences, SettingsStore, endpoint
from jarvis_client.vault import WindowsVault


def credentials():
    return {"access_token": secrets.token_urlsafe(32), "refresh_token": secrets.token_urlsafe(32), "token_type": "Bearer", "expires_in": 300}


def test_source_entrypoint_does_not_depend_on_working_directory_or_pythonpath(tmp_path):
    import subprocess
    import sys
    from pathlib import Path
    environment=dict(os.environ);environment.pop('PYTHONPATH',None);environment['QT_QPA_PLATFORM']='offscreen'
    entry=Path(__file__).resolve().parents[1]/'run_client.py'
    result=subprocess.run([sys.executable,str(entry),'--help'],cwd=tmp_path,env=environment,capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stderr
    assert 'JARVIS Windows desktop client' in result.stdout


def test_personal_list_queries_are_closed_and_authenticated(vault):
    seen=[]
    api=ApiClient('http://127.0.0.1:8765',vault,transport=httpx.MockTransport(lambda request:(seen.append(request),httpx.Response(200,json={}))[1]))
    api._install(credentials())
    for path in ('events?history=true','life-items?kind=shopping','life-items/00000000-0000-0000-0000-000000000001?revision=2'):
        api.request('GET','/api/v1/natural/'+path)
    assert len(seen)==3 and all(request.headers.get('Authorization','').startswith('Bearer ') for request in seen)
    for path in ('events?history=true&other=1','life-items?kind=unknown','life-items?kind=shopping&secret=x'):
        with pytest.raises(ValueError):api.request('GET','/api/v1/natural/'+path)
    assert len(seen)==3;api.close()


@pytest.mark.parametrize("url", ["http://192.168.1.4:8765", "http://example.com", "https://user:pass@example.com", "https://example.com/path", "https://example.com?token=x", "https://example.com:99999", "file:///test", None])
def test_untrusted_or_credential_bearing_origins_rejected(url):
    with pytest.raises(ValueError):
        endpoint(url)


def test_profiles_and_settings_preserve_only_non_secrets(tmp_path):
    store = SettingsStore(tmp_path)
    value = Preferences(remote_url="https://jarvis.example.com", connection_mode="auto", theme="light", notifications=False)
    store.save(value)
    assert store.load() == value
    assert value.candidates() == ["http://127.0.0.1:8765", "https://jarvis.example.com"]
    assert not any(word in store.path.read_text() for word in ("access_token", "refresh_token", "password"))
    store.path.write_text('{"refresh_token":"unexpected"}', encoding="utf-8")
    with pytest.raises(ValueError):
        store.load()
    assert store.path.exists()


def test_pkce_matches_rfc7636_vector():
    assert challenge("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk") == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


def test_pairing_uses_windows_type_proof_and_minimal_scopes(vault):
    issued = credentials()
    requests = []
    def server(request):
        requests.append(request)
        body = json.loads(request.content) if request.content else {}
        if request.url.path.endswith("/requests"):
            assert body["device_type"] == "windows"
            assert "chat:delete" not in body["scopes"] and "admin:account" not in body["scopes"]
            assert body["code_challenge_method"] == "S256"
            return httpx.Response(200, json={"device_code": secrets.token_urlsafe(32), "user_code": "ABCDE-23456", "expires_in": 300, "interval": 5, "verification_uri": "https://evil.example"})
        if request.url.path.endswith("/token"):
            assert "code_verifier" in body and "cookie" not in request.headers
            assert challenge(body["code_verifier"]) == json.loads(requests[0].content)["code_challenge"]
            return httpx.Response(200, json=issued)
        return httpx.Response(200, json={"session_id": "synthetic-session", "permissions": ["chat:read"]})
    clock = [100.0]
    api = ApiClient("http://127.0.0.1:8765", vault, transport=httpx.MockTransport(server), clock=lambda: clock[0])
    public = api.begin_pair("Test Windows")
    assert "device_code" not in public and "evil" not in public["verification_uri"]
    assert api.poll_pair() == {"pending": True}
    clock[0] += 5
    assert api.poll_pair()["session_id"] == "synthetic-session"
    assert vault.load(api.origin) == issued["refresh_token"]
    api.close()


@pytest.mark.parametrize("code", ["authorization_pending", "slow_down", "access_denied", "expired_token"])
def test_pairing_pending_backoff_and_rejection(vault, code):
    clock = [100.0]
    api = ApiClient("http://127.0.0.1:8765", vault, transport=httpx.MockTransport(lambda request: httpx.Response(400, json={"error": {"code": code}})), clock=lambda: clock[0])
    api.pairing = {"secret": secrets.token_urlsafe(32), "verifier": secrets.token_urlsafe(32), "deadline": 200, "next": 100, "interval": 5}
    if code in ("authorization_pending", "slow_down"):
        assert api.poll_pair()["pending"]
        assert api.pairing["next"] == 100 + (10 if code == "slow_down" else 5)
    else:
        with pytest.raises(ClientError):
            api.poll_pair()
        assert api.pairing is None
    api.close()


def test_refresh_serialized_across_threads_and_old_token_not_durable(vault):
    origin = "http://127.0.0.1:8765"
    vault.save(origin, secrets.token_urlsafe(32))
    issued = credentials()
    calls = []
    def server(request):
        assert vault.load(origin) is None
        calls.append(request)
        time.sleep(0.02)
        return httpx.Response(200, json=issued)
    api = ApiClient(origin, vault, transport=httpx.MockTransport(server))
    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(lambda _: api.headers(), range(4)))
    assert len(calls) == 1
    assert all(row["Authorization"] == "Bearer " + issued["access_token"] for row in results)
    assert vault.load(origin) == issued["refresh_token"]
    api.close()


def test_ambiguous_refresh_failure_never_replays_old_token(vault):
    origin = "http://127.0.0.1:8765"
    vault.save(origin, secrets.token_urlsafe(32))
    calls = []
    def server(request):
        calls.append(request)
        raise httpx.ReadTimeout("synthetic transport failure")
    api = ApiClient(origin, vault, transport=httpx.MockTransport(server))
    for _ in range(2):
        with pytest.raises(ClientError):
            api.headers()
    assert len(calls) == 1 and vault.load(origin) is None and api.access is None
    api.close()


@pytest.mark.parametrize("revoke", [False, True])
def test_logout_or_device_revocation_forgets_credentials(vault, revoke):
    seen = []
    api = ApiClient("http://127.0.0.1:8765", vault, transport=httpx.MockTransport(lambda request: (seen.append(request.url.path), httpx.Response(200, json={}))[1]))
    api._install(credentials())
    api.logout(revoke)
    assert seen == ["/api/v1/auth/disconnect" if revoke else "/api/v1/auth/logout"]
    assert vault.load(api.origin) is None and api.access is None
    api.close()


def test_invalid_authentication_clears_saved_session(vault):
    api = ApiClient("http://127.0.0.1:8765", vault, transport=httpx.MockTransport(lambda request: httpx.Response(401, json={"error": {"code": "authentication_required"}})))
    api._install(credentials())
    with pytest.raises(ClientError):
        api.session()
    assert vault.load(api.origin) is None
    api.close()


def test_tokens_are_bound_to_exact_server_origin(vault):
    a = ApiClient("http://127.0.0.1:8765", vault)
    a._install(credentials())
    b = ApiClient("https://other.example", vault, transport=httpx.MockTransport(lambda request: pytest.fail("Tokens must not be sent to another origin")))
    with pytest.raises(ClientError):
        b.headers()
    assert vault.load(a.origin)
    a.close()
    b.close()


@pytest.mark.parametrize("complete", [True, False])
def test_sse_stream_is_incremental_and_requires_done(vault, complete):
    events = [{"type": "meta", "conversation_id": "synthetic"}, {"type": "delta", "text": "Hallo"}]
    if complete:
        events.append({"type": "done", "message": "Hallo", "status": "completed", "error": None})
    payload = "".join("event: " + event["type"] + "\ndata: " + json.dumps(event) + "\n\n" for event in events)
    seen = []
    def server(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, text=payload)
    api = ApiClient("http://127.0.0.1:8765", vault, transport=httpx.MockTransport(server))
    api._install(credentials())
    received = []
    if complete:
        assert api.stream("hello", None, "auto", received.append)["completed"]
    else:
        with pytest.raises(ClientError, match="vóór"):
            api.stream("hello", None, "auto", received.append)
    assert received[1]["text"] == "Hallo" and len(seen) == 1
    assert "request_id" in seen[0]
    api.close()


def test_redirects_and_wrong_server_identity_are_rejected(vault):
    for response in (httpx.Response(302, headers={"Location": "https://evil.example"}), httpx.Response(200, json={"service": "other", "status": "ok"})):
        api = ApiClient("https://jarvis.example", vault, transport=httpx.MockTransport(lambda request: response))
        with pytest.raises(ClientError):
            api.probe()
        api.close()


def test_local_agent_has_only_explicit_non_shell_capability():
    agent = LocalAgent()
    for action in ("system_info", "shell", "delete_file"):
        with pytest.raises(PermissionError):
            agent.run(action, set())
    with pytest.raises(PermissionError):
        agent.run("shell", {"shell"})
    assert "cpu_threads" in agent.run("system_info", {"system_info"})


def test_notification_preferences_deduplication_and_bounded_history():
    seen, clock = [], [100.0]
    center = NotificationCenter(lambda *args: seen.append(args), clock=lambda: clock[0])
    assert center.publish("lost", "Offline") and not center.publish("lost", "Offline")
    center.enabled = False
    clock[0] += 61
    assert center.publish("lost", "Offline") and len(seen) == 1
    for index in range(110):
        center.publish(str(index), "Generic status")
    assert len(center.items) == 100
    assert 60 <= backoff(100) <= 60.4


@pytest.mark.skipif(os.name != "nt", reason="Windows-native credential store")
def test_real_windows_credential_manager_isolated_roundtrip():
    vault = WindowsVault("JARVIS/tests/" + secrets.token_hex(12) + "/")
    origin = "https://synthetic.example"
    secret = secrets.token_urlsafe(32)
    try:
        vault.save(origin, secret)
        assert vault.load(origin) == secret
    finally:
        vault.delete(origin)
    assert vault.load(origin) is None


def test_startup_command_only_starts_client(monkeypatch):
    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setattr("sys.executable", r"C:\Program Files\JARVIS\JARVIS.exe")
    command = Startup.command()
    assert command.startswith('"C:\\Program Files\\JARVIS\\JARVIS.exe"') and "--minimized" in command
    assert "server" not in command
