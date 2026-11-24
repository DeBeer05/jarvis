import asyncio
from dataclasses import replace

from server.ai.policy import RequestPolicy,use_policy
from server.ai.router import AIRouter
from server.natural.models import UserSettings
from tests.ai_helpers import FakeProvider


def test_streaming_preference_buffers_until_success_and_keeps_requests_independent(settings):
    base=RequestPolicy.from_document({"revision":1,"settings":UserSettings().model_dump(mode="json")})
    async def run():
        router=AIRouter(settings,{"gemini":FakeProvider(("Een ","antwoord."))})
        async def collect(policy):
            with use_policy(policy):return [event async for event in router.stream([],"gemini")]
        buffered=await collect(replace(base,streaming=False))
        streamed=await collect(replace(base,streaming=True))
        assert [row["text"] for row in buffered if row["type"]=="delta"]==["Een antwoord."]
        assert [row["text"] for row in streamed if row["type"]=="delta"]==["Een ","antwoord."]
    asyncio.run(run())


def test_failed_buffer_is_never_shown_before_allowed_fallback(settings):
    config=UserSettings().model_dump(mode="json");config["ai"].update(provider="gemini",fallback="ollama",streaming=False)
    policy=RequestPolicy.from_document({"revision":1,"settings":config})
    async def run():
        router=AIRouter(settings,{"gemini":FakeProvider(("Onvolledige tekst",),failure="unavailable",fail_after=1),"ollama":FakeProvider(("Lokaal antwoord",))})
        with use_policy(policy):events=[event async for event in router.stream([],"auto")]
        assert [event["text"] for event in events if event["type"]=="delta"]==["Lokaal antwoord"]
        assert any(event["type"]=="fallback" for event in events)
    asyncio.run(run())
