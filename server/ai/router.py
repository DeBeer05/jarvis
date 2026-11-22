"""One selection policy: fallback only before the first visible answer token."""
from contextlib import aclosing
from server.ai.providers import ProviderError, TextProvider
from server.config import Settings


class AIRouter:
    def __init__(self, settings: Settings, providers: dict | None = None):
        self.settings = settings
        self.providers = providers if providers is not None else {name: TextProvider(name, settings) for name in ("gemini", "groq", "ollama")}

    async def stream(self, messages: list[dict], mode: str):
        preferred = self.settings.preferred_provider
        order = [preferred, "gemini" if preferred == "ollama" else "ollama"] if mode == "auto" else [mode]
        for position, name in enumerate(order):
            provider = self.providers[name]
            started = False
            try:
                async with aclosing(provider.stream(messages)) as source:
                    async for text in source:
                        if not text:
                            continue
                        if not started:
                            started = True
                            yield {"type": "provider", "provider": name, "model": provider.model}
                        yield {"type": "delta", "text": text}
                if not started:
                    raise ProviderError("invalid_response")
                return
            except ProviderError as error:
                if started:
                    raise ProviderError("stream_interrupted", retryable=False) from None
                if position == len(order) - 1 or not error.retryable:
                    raise
                yield {"type": "fallback", "from": name, "to": order[position + 1], "code": error.code, "message": error.message}

    async def availability(self) -> dict:
        import asyncio
        names = tuple(self.providers)
        values = await asyncio.gather(*(self.providers[name].availability() for name in names))
        return {"mode": self.settings.ai_provider, "preferred": self.settings.preferred_provider,
                "profile": self.settings.profile, "providers": dict(zip(names, values))}
