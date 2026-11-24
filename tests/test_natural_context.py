"""End-to-end synthetic chat, privacy boundaries and request-local AI policy."""
import asyncio
from dataclasses import replace

import pytest

from server.ai.policy import RequestPolicy, current_policy, use_policy
from server.ai.providers import TextProvider, ProviderError
from server.ai.router import AIRouter
from server.app import create_app
from tests.ai_helpers import FakeProvider
from tests.auth_helpers import AuthenticatedTestClient


def client(app):
    return AuthenticatedTestClient(app,base_url="http://127.0.0.1:8765",client=("127.0.0.1",12345))


def build(settings):
    providers={name:FakeProvider(("Antwoord.",)) for name in ("gemini","groq","ollama")}
    return create_app(settings,ai_router=AIRouter(settings,providers)),providers


def patch(c,category,changes):
    revision=c.get("/api/v1/natural/settings").json()["revision"]
    response=c.patch("/api/v1/natural/settings/"+category,json={"revision":revision,"changes":changes})
    assert response.status_code==200


def test_explicit_memory_commands_survive_restart_without_cloud_call(settings):
    app,providers=build(settings)
    with client(app) as c:
        saved=c.post("/api/v1/chat",json={"message":"Onthoud dat ik liever afspraken na tien uur plan"}).json()
        assert saved["status"]=="completed" and saved["model"]=="memory"
        assert not any(p.calls for p in providers.values())
    again,_=build(settings)
    with client(again) as c:
        reply=c.post("/api/v1/chat",json={"message":"Wat weet je nog over mij?"}).json()
        assert "na tien uur" in reply["message"]
        forgotten=c.post("/api/v1/chat",json={"message":"Vergeet afspraken na tien uur"}).json()
        assert "verwijderd" in forgotten["message"]
        assert c.get("/api/v1/natural/memory").json()["items"]==[]


def test_memory_cloud_consent_local_offline_and_sensitive_filter(settings):
    app,providers=build(settings)
    with client(app) as c:
        c.post("/api/v1/natural/memory",json={"content":"Project lantaarn gebruikt Python"})
        c.post("/api/v1/natural/memory",json={"content":"Project lantaarn medische voorkeur","sensitivity":"sensitive","consent_sensitive":True})
        payload={"message":"Vertel over project lantaarn","provider":"gemini"}
        assert c.post("/api/v1/chat",json=payload).json()["status"]=="completed"
        assert "Project lantaarn gebruikt Python" not in str(providers["gemini"].calls[-1])
        patch(c,"privacy",{"cloud_memories":True})
        c.post("/api/v1/chat",json=payload)
        assert "Project lantaarn gebruikt Python" in str(providers["gemini"].calls[-1])
        assert "medische voorkeur" not in str(providers["gemini"].calls[-1])
        before=len(providers["gemini"].calls)
        patch(c,"ai",{"offline":True})
        patch(c,"memory",{"sensitive":True})
        result=c.post("/api/v1/chat",json=payload).json()
        assert result["provider"]=="ollama" and len(providers["gemini"].calls)==before
        assert "medische voorkeur" in str(providers["ollama"].calls[-1])


def test_offline_covers_internal_automation_calls_and_failed_local_fallback(settings):
    app,providers=build(settings)
    class InternalCall:
        def candidate(self,run):return True
        async def stream(self,run):
            text=await app.state.chat.router.bounded_text([{"role":"user","content":"synthetic planner"}],"gemini")
            yield {"type":"delta","text":text}
    app.state.chat.automation_chat=InternalCall()
    with client(app) as c:
        patch(c,"ai",{"offline":True})
        assert c.post("/api/v1/chat",json={"message":"synthetic"}).json()["status"]=="completed"
        assert not providers["gemini"].calls and len(providers["ollama"].calls)==1
        providers["ollama"].failure="unavailable"
        assert c.post("/api/v1/chat",json={"message":"synthetic again"}).json()["status"]=="error"
        assert not providers["gemini"].calls


def test_forgotten_memory_cannot_reenter_through_history_or_summary(settings):
    app,providers=build(settings)
    with client(app) as c:
        memory=c.post("/api/v1/natural/memory",json={"content":"Het project heet lantaarn"}).json()
        first=c.post("/api/v1/chat",json={"message":"Wat heet het project?","provider":"ollama"}).json()
        cid=first["conversation_id"]
        principal=app.state.security.store.authenticate(c.cookies.get("jarvis_access"))
        summary=app.state.natural.context.summarize(principal,cid,force=True)
        assert summary and c.get("/api/v1/natural/summaries").json()["items"]
        assert c.delete("/api/v1/natural/memory/"+memory["id"]).status_code==200
        assert not c.get("/api/v1/natural/summaries").json()["items"]
        c.post("/api/v1/chat",json={"message":"Ga verder","provider":"ollama","conversation_id":cid})
        assert "Wat heet het project?" not in str(providers["ollama"].calls[-1])


def test_summary_versions_and_voice_personality_are_real_context(settings):
    app,providers=build(settings)
    with client(app) as c:
        patch(c,"personality",{"profile":"concise","brevity":100})
        reply=c.post("/api/v1/chat",json={"message":"Hallo","channel":"voice"}).json()
        context=str(providers["gemini"].calls[-1])
        assert "Kort en zakelijk" in context and "spreek" in context.casefold()
        principal=app.state.security.store.authenticate(c.cookies.get("jarvis_access"))
        summary=app.state.natural.context.summarize(principal,reply["conversation_id"],force=True)
        body={"revision":summary["revision"],"content":"Een bewerkbare lokale samenvatting"}
        assert c.put("/api/v1/natural/summaries/"+summary["id"],json=body).status_code==200
        assert c.put("/api/v1/natural/summaries/"+summary["id"],json=body).status_code==409


def test_budget_rejection_releases_only_new_reservation(settings):
    app,_=build(settings)
    with client(app) as c:
        patch(c,"ai",{"context_tokens":1024})
        response=c.post("/api/v1/chat",json={"message":"lange invoer "*500})
        assert response.status_code==422 and not app.state.chat.active
        assert c.post("/api/v1/chat",json={"message":"Kort"}).json()["status"]=="completed"


def test_provider_policy_is_task_local_and_direct_cloud_guard(settings):
    from server.natural.models import UserSettings
    config=UserSettings().model_dump(mode="json")
    policy=RequestPolicy.from_document({"revision":1,"settings":config})
    local=replace(policy,offline=True,ollama_model="synthetic-local")
    provider=TextProvider("ollama",settings)
    async def run():
        async def one(selected):
            with use_policy(selected):
                await asyncio.sleep(0)
                assert current_policy.get() is selected
                return provider.model
        assert await asyncio.gather(one(local),one(policy))==["synthetic-local",settings.ollama_model]
        assert current_policy.get() is None
        with use_policy(local):
            with pytest.raises(ProviderError):
                await anext(TextProvider("gemini",settings).stream([]))
    asyncio.run(run())
