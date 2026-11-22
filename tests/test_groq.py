import asyncio
import json
import logging
from dataclasses import replace

import httpx
import pytest
from fastapi.testclient import TestClient
from tests.auth_helpers import AuthenticatedTestClient

from server.ai.providers import ProviderError, TextProvider
from server.ai.router import AIRouter
from server.app import create_app
from server.config import ConfigurationError, load_settings
from server.logging_config import configure_logging, close_logging
from server.redaction import redact
from tests.ai_helpers import FakeProvider


def http_factory(handler):
    return lambda **kwargs: httpx.AsyncClient(transport=httpx.MockTransport(handler), **kwargs)


def wire_response(text):
    return httpx.Response(200, text='data: ' + json.dumps({"choices": [{"delta": {"content": text}}]}) + '\n\ndata: [DONE]\n\n')


def local_client(app):
    return AuthenticatedTestClient(app, base_url="http://127.0.0.1:8765", client=("127.0.0.1", 10000))


def test_groq_uses_shared_transport_and_official_contract(settings):
    key = "groq-canary-" + "test-only"
    configured = replace(settings, groq_api_key=key)
    calls = []

    def handler(request):
        calls.append(request)
        assert str(request.url) == "https://api.groq.com/openai/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer " + key
        body = json.loads(request.content)
        assert body["model"] == "openai/gpt-oss-120b" and body["stream"] is True
        assert body["max_completion_tokens"] == configured.max_output_tokens
        assert body["reasoning_effort"] == "low" and body["include_reasoning"] is False
        assert "max_tokens" not in body and "tools" not in body
        return wire_response("Groq antwoordt.")

    async def check():
        provider = TextProvider("groq", configured, http_factory(handler))
        assert (await provider.availability())["available"] is None
        assert [text async for text in provider.stream([{"role": "user", "content": "Hallo"}])] == ["Groq antwoordt."]
    asyncio.run(check())
    assert len(calls) == 1


def test_missing_groq_key_makes_no_network_request(settings):
    def unexpected(request):
        pytest.fail("Missing Groq key must not contact a provider")

    async def check():
        provider = TextProvider("groq", settings, http_factory(unexpected))
        assert (await provider.availability())["state"] == "not_configured"
        with pytest.raises(ProviderError, match="groq_not_configured"):
            _ = [text async for text in provider.stream([])]
    asyncio.run(check())


def test_explicit_groq_api_redacts_both_configured_keys(settings):
    groq_key = "groq-canary-" + "do-not-store"
    gemini_key = "gemini-canary-" + "do-not-store"
    configured = replace(settings, groq_api_key=groq_key, gemini_api_key=gemini_key)
    gemini, ollama = FakeProvider(), FakeProvider()

    def handler(request):
        assert groq_key not in request.content.decode() and gemini_key not in request.content.decode()
        return wire_response("Hallo " + groq_key + " " + gemini_key)

    groq = TextProvider("groq", configured, http_factory(handler))
    app = create_app(configured, ai_router=AIRouter(configured, {"gemini": gemini, "groq": groq, "ollama": ollama}))
    with local_client(app) as client:
        response = client.post("/api/v1/chat", json={"message": "Niet opslaan: " + groq_key + gemini_key, "provider": "groq"})
        assert response.status_code == 200
        result = response.json()
        assert result["provider"] == "groq" and result["model"] == configured.groq_model
        saved = client.get("/api/v1/chat/conversations/" + result["conversation_id"]).text
        assert groq_key not in saved and gemini_key not in saved
        assert groq_key not in result["message"] and gemini_key not in result["message"]
    assert not gemini.calls and not ollama.calls
    assert groq_key.encode() not in settings.database_path.read_bytes()


@pytest.mark.parametrize("partial", [False, True])
def test_groq_preferred_fallback_never_contacts_gemini(settings, partial):
    configured = replace(settings, preferred_provider="groq")
    gemini = FakeProvider()
    groq = FakeProvider(("Deel",), failure="rate_limited", fail_after=1 if partial else 0)
    ollama = FakeProvider(("Lokaal",))
    app = create_app(configured, ai_router=AIRouter(configured, {"gemini": gemini, "groq": groq, "ollama": ollama}))
    with local_client(app) as client:
        result = client.post("/api/v1/chat", json={"message": "Hallo", "provider": "auto"}).json()
        assert result["provider"] == ("groq" if partial else "ollama")
        assert result["status"] == ("error" if partial else "completed")
        if partial:
            assert result["error"]["code"] == "stream_interrupted" and not ollama.calls
        else:
            assert result["message"] == "Lokaal" and ollama.calls
    assert not gemini.calls


def test_groq_configuration_and_secret_repr(tmp_path):
    settings = load_settings(root=tmp_path, environ={"JARVIS_AI_PROVIDER": "groq", "JARVIS_AI_PREFERRED_PROVIDER": "groq", "GROQ_API_KEY": "private-canary-value"})
    assert settings.ai_provider == settings.preferred_provider == "groq"
    assert settings.groq_model == "openai/gpt-oss-120b"
    assert "private-canary-value" not in repr(settings)
    with pytest.raises(ConfigurationError, match="GROQ_MODEL"):
        load_settings(root=tmp_path, environ={"GROQ_MODEL": "invalid model"})


def test_groq_key_redacted_from_logs_and_recognizable_pasted_keys(settings):
    canary = "groq-private-" + "canary"
    configured = replace(settings, groq_api_key=canary)
    handlers = configure_logging(configured, console=False)
    try:
        logging.getLogger("jarvis.server").warning("canary %s", canary)
    finally:
        close_logging(handlers)
    assert canary not in settings.log_path.read_text(encoding="utf-8")
    assert "[REDACTED]" in settings.log_path.read_text(encoding="utf-8")
    recognizable = "gsk_" + "T" * 48
    assert recognizable not in redact("voorbeeld " + recognizable)


def test_provider_status_exposes_groq_without_credentials_or_network(settings):
    configured = replace(settings, groq_api_key="groq-private-" + "canary")
    providers = {"gemini": FakeProvider(), "groq": TextProvider("groq", configured), "ollama": FakeProvider()}
    with local_client(create_app(configured, ai_router=AIRouter(configured, providers))) as client:
        status = client.get("/api/v1/ai/providers")
        assert status.json()["providers"]["groq"] == {"configured": True, "available": None, "state": "not_verified", "model": configured.groq_model}
        assert configured.groq_api_key not in status.text
        assert client.get("/api/v1/status").json()["ai_providers"]["groq"] == {"configured": True, "available": None}
        assert '<option value="groq">Groq</option>' in client.get("/chat").text
