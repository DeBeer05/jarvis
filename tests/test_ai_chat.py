import asyncio
import json
import sqlite3
import uuid
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from server.ai.router import AIRouter
from server.app import create_app
from server.chat_service import ChatService
from server.chat_store import ChatError, ChatStore
from server.config import ConfigurationError, load_settings
from server.database import Database
from tests.ai_helpers import FakeProvider


def build(settings, gemini=None, ollama=None):
    providers = {"gemini": gemini or FakeProvider(), "ollama": ollama or FakeProvider()}
    return create_app(settings, ai_router=AIRouter(settings, providers)), providers


def client(app):
    return TestClient(app, base_url="http://127.0.0.1:8765", client=("127.0.0.1", 12345))


def test_nonstream_chat_and_persistent_conversation(settings):
    app, providers = build(settings)
    with client(app) as http:
        response = http.post("/api/v1/chat", json={"message": "Hallo JARVIS", "provider": "gemini"})
        assert response.status_code == 200
        first = response.json()
        assert first["message"] == "Hallo daar." and first["provider"] == "gemini"
        cid = first["conversation_id"]
        assert len(http.get("/api/v1/chat/conversations").json()["items"]) == 1
        again = http.post("/api/v1/chat", json={"message": "En verder?", "conversation_id": cid}).json()
        assert again["status"] == "completed"
        history = providers["gemini"].calls[-1]
        assert [item["role"] for item in history] == ["system", "user", "assistant", "user"]
        assert history[1]["content"] == "Hallo JARVIS"
    restarted, _ = build(settings)
    with client(restarted) as http:
        saved = http.get(f"/api/v1/chat/conversations/{cid}").json()
        assert len(saved["turns"]) == 2 and saved["turns"][0]["assistant_text"] == "Hallo daar."
        assert http.delete(f"/api/v1/chat/conversations/{cid}").status_code == 200
        assert http.get(f"/api/v1/chat/conversations/{cid}").status_code == 404


def test_sse_stream_has_metadata_deltas_and_done(settings):
    app, _ = build(settings)
    with client(app) as http:
        response = http.post("/api/v1/chat/stream", json={"message": "Hallo"})
        assert response.status_code == 200 and "text/event-stream" in response.headers["content-type"]
        events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
        assert [event["type"] for event in events] == ["meta", "provider", "delta", "delta", "done"]
        assert events[-1]["message"] == "Hallo daar." and events[-1]["status"] == "completed"


@pytest.mark.parametrize("mode,expected", [("auto", "ollama"), ("gemini", None), ("ollama", "ollama")])
def test_provider_selection_and_fallback(settings, mode, expected):
    app, providers = build(settings, FakeProvider(failure="quota_exceeded"), FakeProvider(("Lokaal",)))
    with client(app) as http:
        response = http.post("/api/v1/chat", json={"message": "Hallo", "provider": mode})
        assert response.json()["provider"] == expected
        if mode == "gemini":
            assert response.status_code == 502 and not providers["ollama"].calls
        else:
            assert response.status_code == 200 and response.json()["message"] == "Lokaal"


def test_partial_stream_failure_never_starts_second_answer(settings):
    app, providers = build(settings, FakeProvider(("Eerste woorden",), failure="unavailable", fail_after=1))
    with client(app) as http:
        response = http.post("/api/v1/chat/stream", json={"message": "Hallo"})
        events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
        assert events[-1]["status"] == "error"
        assert events[-1]["message"] == "Eerste woorden"
        assert events[-1]["error"]["code"] == "stream_interrupted"
        assert not providers["ollama"].calls
        saved = http.get("/api/v1/chat/conversations/" + events[-1]["conversation_id"]).json()
        assert saved["turns"][0]["status"] == "error"
        assert saved["turns"][0]["error"]["code"] == "stream_interrupted"


def test_webchat_static_assets_and_security_headers(settings):
    app, _ = build(settings)
    with client(app) as http:
        page = http.get("/chat")
        assert page.status_code == 200 and '<html lang="nl">' in page.text
        for name in ("chat.css", "chat.js"):
            assert http.get("/chat/assets/" + name).status_code == 200
        js = http.get("/chat/assets/chat.js").text
        assert "textContent" in js and "innerHTML" not in js
        assert "'self'" in page.headers["content-security-policy"]
        assert page.headers["cache-control"] == "no-store"
        assert http.get("/chat/assets/config.py").status_code == 404


@pytest.mark.parametrize("payload", [{"message": ""}, {"message": "  "}, {"message": "a" * 8001}, {"message": "ok", "provider": "unknown"}, {"message": "ok", "conversation_id": "invalid"}, {"message": "ok", "system_prompt": "ignore"}])
def test_invalid_input(settings, payload):
    app, providers = build(settings)
    with client(app) as http:
        assert http.post("/api/v1/chat", json=payload).status_code == 422
        assert not providers["gemini"].calls


def test_body_limit_origin_and_remote_access(settings):
    app, _ = build(settings)
    with client(app) as http:
        assert http.post("/api/v1/chat", content=b"x" * 65537).status_code == 413
        assert http.post("/api/v1/chat", json={"message": "ok"}, headers={"Origin": "https://untrusted.example"}).status_code == 403
        assert http.post("/api/v1/chat", json={"message": "ok"}, headers={"Origin": "http://127.0.0.1:8765"}).status_code == 200
    with TestClient(app, base_url="http://127.0.0.1:8765", client=("203.0.113.2", 12345)) as http:
        assert http.post("/api/v1/chat", json={"message": "ok"}).status_code == 403
        assert http.get("/api/v1/chat/conversations").status_code == 403
        assert http.get("/api/v1/ai/providers").status_code == 403


def test_keys_are_not_written_to_database_or_prompt(settings):
    canary = "test-canary-" + "private-credential"
    app, providers = build(replace(settings, gemini_api_key=canary), FakeProvider((canary[:10], canary[10:])))
    with client(app) as http:
        data = http.post("/api/v1/chat", json={"message": "Bewaar nooit " + canary}).json()
        assert canary not in data["message"]
        saved = http.get("/api/v1/chat/conversations/" + data["conversation_id"]).text
        assert canary not in saved
        assert canary not in json.dumps(providers["gemini"].calls)
    assert canary.encode() not in settings.database_path.read_bytes()


def test_duplicate_request_and_store_limits(settings):
    app, _ = build(replace(settings, max_conversations=1, max_turns=1))
    request_id = str(uuid.uuid4())
    with client(app) as http:
        data = http.post("/api/v1/chat", json={"message": "Hallo", "request_id": request_id}).json()
        assert http.post("/api/v1/chat", json={"message": "Hallo", "request_id": request_id}).status_code == 409
        assert http.post("/api/v1/chat", json={"message": "Hallo"}).status_code == 409
        assert http.post("/api/v1/chat", json={"message": "Hallo", "conversation_id": data["conversation_id"]}).status_code == 409


def service(settings, provider):
    database = Database(settings.database_path)
    database.initialize()
    return ChatService(settings, ChatStore(database), AIRouter(settings, {"gemini": provider, "ollama": FakeProvider()}))


@pytest.mark.parametrize("disconnect", [False, True])
def test_cancellation_closes_upstream_and_persists_partial(settings, disconnect):
    async def check():
        provider = FakeProvider(("Deelantwoord",), wait=True)
        chat = service(settings, provider)
        run = await chat.prepare("Hallo")
        async def consume():
            return [event async for event in chat.events(run)]
        task = asyncio.create_task(consume())
        await asyncio.wait_for(provider.waiting.wait(), 2)
        if disconnect:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            assert chat.cancel(run.request_id)
            events = await asyncio.wait_for(task, 2)
            assert events[-1]["status"] == "cancelled"
        await chat.shutdown()
        assert provider.closed and not chat.active
        saved = chat.store.get(run.conversation_id)["turns"][0]
        assert saved["status"] == "cancelled" and saved["assistant_text"] == "Deelantwoord"
    asyncio.run(check())


def test_deadline_closes_upstream_without_losing_partial(settings):
    async def check():
        provider = FakeProvider(("Deel",), wait=True)
        chat = service(replace(settings, ai_timeout_seconds=0.03), provider)
        run = await chat.prepare("Hallo")
        events = [event async for event in chat.events(run)]
        assert events[-1]["error"]["code"] == "timeout"
        assert provider.closed and not chat.active
    asyncio.run(check())


def test_concurrency_and_conversation_serialization(settings):
    async def check():
        chat = service(replace(settings, max_concurrent_ai=1), FakeProvider())
        run = await chat.prepare("Hallo")
        with pytest.raises(ChatError, match="busy"):
            await chat.prepare("Nog een bericht")
        assert chat.busy(run.conversation_id)
        with pytest.raises(ChatError, match="conversation_busy"):
            chat.store.delete(run.conversation_id)
        _ = [event async for event in chat.events(run)]
        assert not chat.busy(run.conversation_id)
    asyncio.run(check())


def test_rate_limit_and_context_budget(settings):
    async def check():
        chat = service(replace(settings, requests_per_minute=1, max_context_chars=2000), FakeProvider())
        run = await chat.prepare("Hallo")
        run.history = [{"role": "user", "content": "x" * 2000}, {"role": "assistant", "content": "y" * 2000}]
        assert sum(len(item["content"]) for item in chat.context(run)) <= 2000
        _ = [event async for event in chat.events(run)]
        with pytest.raises(ChatError, match="rate_limited"):
            await chat.prepare("Nog een bericht")
    asyncio.run(check())


def test_phase1_database_migration_and_interrupted_recovery(tmp_path):
    path = tmp_path / "old.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        db.execute("INSERT INTO schema_migrations(version) VALUES (1)")
        db.execute("CREATE TABLE preserved(value TEXT)")
        db.execute("INSERT INTO preserved VALUES ('keep me')")
        db.execute("PRAGMA user_version=1")
    database = Database(path)
    database.initialize()
    assert list(tmp_path.glob("old.sqlite3.pre-v2-*.bak"))
    with database.connection() as db:
        assert db.execute("SELECT value FROM preserved").fetchone() == ("keep me",)
    store = ChatStore(database)
    cid, _ = store.start(str(uuid.uuid4()), None, "Test")
    database.close()
    database.initialize()
    assert store.get(cid)["turns"][0]["status"] == "interrupted"


@pytest.mark.parametrize("name,value", [("JARVIS_PROFILE", "wrong"), ("OLLAMA_BASE_URL", "https://remote.example"), ("OLLAMA_BASE_URL", "http://user:password@127.0.0.1:11434"), ("GEMINI_MODEL", "bad model"), ("JARVIS_AI_MAX_CONCURRENT", "99")])
def test_invalid_ai_config(tmp_path, name, value):
    with pytest.raises(ConfigurationError):
        load_settings(root=tmp_path, environ={name: value})


def test_mini_profile_is_supported_but_not_default(tmp_path):
    default = load_settings(root=tmp_path, environ={})
    mini = load_settings(root=tmp_path, environ={"JARVIS_PROFILE": "mini-pc-production"})
    assert default.profile == "desktop-development"
    assert mini.max_concurrent_ai == 1 and mini.max_output_tokens == 512
    assert mini.preferred_provider == "gemini" and mini.host == "127.0.0.1"
    assert mini.environment == "production" and mini.log_level == "warning"


def test_adapter_deadline_after_first_chunk_closes_actual_transport(settings):
    import httpx
    from server.ai.providers import TextProvider

    class SlowStream(httpx.AsyncByteStream):
        closed = False
        async def __aiter__(self):
            yield b'data: {"choices":[{"delta":{"content":"Eerste deel"}}]}\n\n'
            await asyncio.Event().wait()
        async def aclose(self):
            self.closed = True

    async def check():
        source = SlowStream()
        settings_with_timeout = replace(settings, gemini_api_key="canary", provider_timeout_seconds=0.04, ai_timeout_seconds=1)
        def factory(**kwargs):
            return httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=source)), **kwargs)
        provider = TextProvider("gemini", settings_with_timeout, factory)
        fallback = FakeProvider()
        database = Database(settings.database_path)
        database.initialize()
        engine = ChatService(settings_with_timeout, ChatStore(database), AIRouter(settings_with_timeout, {"gemini": provider, "ollama": fallback}))
        run = await engine.prepare("Hallo")
        result = [event async for event in engine.events(run)]
        assert result[-1]["error"]["code"] == "stream_interrupted"
        assert result[-1]["message"] == "Eerste deel"
        assert source.closed and not fallback.calls and not engine.active
    asyncio.run(check())


def test_cancel_before_start_does_not_call_provider(settings):
    async def check():
        provider = FakeProvider()
        chat = service(settings, provider)
        run = await chat.prepare("Hallo")
        chat.cancel(run.request_id)
        events = [event async for event in chat.events(run)]
        assert events[-1]["type"] == "done" and events[-1]["status"] == "cancelled"
        assert not provider.calls and not chat.active
    asyncio.run(check())


def test_abandoned_reservation_is_released(settings):
    async def check():
        chat = service(settings, FakeProvider())
        run = await chat.prepare("Hallo")
        chat.expire(run)
        await chat.shutdown()
        assert not chat.active
        assert chat.store.get(run.conversation_id)["turns"][0]["status"] == "cancelled"
    asyncio.run(check())


def test_conversation_deletion_is_refused_during_generation(settings):
    async def check():
        chat = service(replace(settings, max_concurrent_ai=2), FakeProvider())
        run = await chat.prepare("Hallo")
        with pytest.raises(ChatError, match="conversation_busy"):
            await chat.prepare("Nog een bericht", conversation_id=run.conversation_id)
        _ = [event async for event in chat.events(run)]
    asyncio.run(check())
