import asyncio
import json
import time
from collections.abc import Callable
from contextlib import aclosing

import httpx

from providers.llm_openai import OpenAICompatLLM, TextStreamError
from server.config import Settings
from server.ai.policy import current_policy

MESSAGES = {
    "authentication_expired": "Je sessie is verlopen of ingetrokken. Log opnieuw in.",
    "not_configured": "Gemini is nog niet ingesteld. Voeg lokaal een geldige GEMINI_API_KEY toe en herstart de server.",
    "groq_not_configured": "Groq is nog niet ingesteld. Voeg lokaal een GROQ_API_KEY toe en herstart de server.",
    "unavailable": "De AI-provider is niet bereikbaar. Controleer de verbinding of start Ollama.",
    "model_missing": "Het ingestelde model is niet beschikbaar. Controleer de modelnaam of download het Ollama-model.",
    "authentication": "De AI-provider weigert de sleutel of toegang. Controleer de lokale configuratie.",
    "quota_exceeded": "Het quota van de AI-provider is bereikt. Probeer later opnieuw of gebruik Ollama.",
    "rate_limited": "De AI-provider ontvangt te veel verzoeken. Wacht even en probeer opnieuw.",
    "timeout": "De AI-provider antwoordde niet op tijd. Probeer opnieuw of kies een andere provider.",
    "content_filtered": "De provider heeft dit antwoord geweigerd. Pas je bericht aan.",
    "invalid_response": "De provider gaf een onvolledig of ongeldig antwoord.",
    "overloaded": "Het AI-model is tijdelijk overbelast. Probeer later opnieuw of kies een andere provider.",
    "provider_error": "De AI-provider gaf een technische fout. Probeer opnieuw.",
    "stream_interrupted": "Het antwoord is onderweg onderbroken. Er is geen tweede antwoord gestart.",
    "response_limit": "Het antwoord bereikte de ingestelde maximale grootte.",
}


class ProviderError(Exception):
    def __init__(self, code: str, *, retryable: bool = True):
        super().__init__(code)
        self.code, self.message, self.retryable = code, MESSAGES[code], retryable


class TextProvider:
    def __init__(self, name: str, settings: Settings, client_factory: Callable | None = None):
        self.name, self.settings = name, settings
        self._model = {"gemini": settings.gemini_model, "groq": settings.groq_model, "ollama": settings.ollama_model}[name]
        self.key = settings.gemini_api_key if name == "gemini" else settings.groq_api_key if name == "groq" else ""
        self.client_factory = client_factory or httpx.AsyncClient
        self._availability: tuple[float, dict] | None = None
        self._probe_lock = asyncio.Lock()

    @property
    def model(self):
        policy = current_policy.get()
        return (getattr(policy, self.name + "_model") if policy else "") or self._model

    async def availability(self, *, refresh: bool = False) -> dict:
        if self.name in ("gemini", "groq"):
            return {"configured": bool(self.key), "available": None if self.key else False,
                    "state": "not_verified" if self.key else "not_configured", "model": self.model}
        async with self._probe_lock:
            if not refresh and self._availability and self._availability[1]["model"] == self.model and time.monotonic() - self._availability[0] < 15:
                return self._availability[1]
            result = {"configured": True, "available": False, "model": self.model, "state": "unavailable", "models": []}
            try:
                async with self.client_factory(timeout=2, trust_env=False, follow_redirects=False) as client:
                    async with client.stream("GET", self.settings.ollama_base_url + "/api/tags") as response:
                        response.raise_for_status()
                        body = bytearray()
                        async for part in response.aiter_bytes():
                            if len(body) + len(part) > 262144:
                                raise ValueError
                            body.extend(part)
                    rows = json.loads(body).get("models", [])
                models = [row["name"] for row in rows[:100] if isinstance(row, dict) and isinstance(row.get("name"), str) and len(row["name"]) <= 128]
                available = self.model in models or self.model + ":latest" in models
                result.update(available=available, state="available" if available else "model_missing", models=models)
            except (httpx.HTTPError, ValueError, TypeError, AttributeError):
                pass
            self._availability = (time.monotonic(), result)
            return result

    async def stream(self, messages: list[dict]):
        policy = current_policy.get()
        # Defense in depth if a caller directly uses a cloud provider.
        if policy and policy.offline and self.name != "ollama":
            raise ProviderError("unavailable", retryable=False)
        timeout = min(self.settings.provider_timeout_seconds, policy.timeout_seconds) if policy else self.settings.provider_timeout_seconds
        if self.name in ("gemini", "groq") and not self.key:
            raise ProviderError("groq_not_configured" if self.name == "groq" else "not_configured")
        if self.name == "ollama":
            status = await self.availability()
            if not status["available"]:
                raise ProviderError(status["state"])
        config = {
            "base_url": {"gemini": "https://generativelanguage.googleapis.com/v1beta/openai", "groq": "https://api.groq.com/openai/v1", "ollama": self.settings.ollama_base_url + "/v1"}[self.name],
            "api_key": self.key,
            "model": self.model, "timeout": timeout,
            "tools": False, "vision": False, "strict_text": True,
            "max_output_tokens": policy.maximum_answer_tokens if policy else self.settings.max_output_tokens,
            "async_client_factory": self.client_factory,
        }
        if self.name == "ollama":
            config["think"] = False
            # The OpenAI endpoint cannot configure Ollama's num_ctx. Reserve
            # input, output and role overhead explicitly, without changing model.
            context=policy.context_tokens if policy else 6000
            output=policy.maximum_answer_tokens if policy else self.settings.max_output_tokens
            config.update(ollama_chat=True,context_tokens=((context+output+256+1023)//1024)*1024)
        if self.name == "groq":
            config["use_completion_tokens"] = True
            if self.model.startswith("openai/gpt-oss-"):
                config.update(think=True, include_reasoning=False)
        transport = OpenAICompatLLM(config)
        try:
            deadline = time.monotonic() + timeout
            temperature = policy.temperature if policy else (0.2 if self.name == "ollama" else None)
            async with aclosing(transport.chat(messages, tools=None, stream=True, temperature=temperature)) as source:
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError
                    try:
                        # Each __anext__ can run in a different task during cancellation.
                        # Never leave a task-bound asyncio.timeout context across a yield.
                        chunk = await asyncio.wait_for(anext(source), remaining)
                    except StopAsyncIteration:
                        break
                    if chunk.get("text"):
                        yield chunk["text"]
        except (TimeoutError, httpx.TimeoutException):
            raise ProviderError("timeout") from None
        except TextStreamError as error:
            code = "provider_error"
            if error.kind == "content_filtered":
                raise ProviderError("content_filtered", retryable=False) from None
            if error.status_code == 429:
                code = "quota_exceeded" if "quota" in json.dumps(error.body).lower() else "rate_limited"
            elif error.status_code in (401, 403):
                code = "authentication"
            elif error.status_code == 503:
                code = "overloaded"
            elif error.status_code == 404:
                code = "model_missing"
            elif error.kind in ("invalid_stream", "incomplete_stream"):
                code = "invalid_response"
            raise ProviderError(code, retryable=error.status_code != 400) from None
        except (httpx.HTTPError, OSError):
            raise ProviderError("unavailable") from None
        except (ValueError, TypeError):
            raise ProviderError("invalid_response") from None
