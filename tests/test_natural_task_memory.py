"""No external accounts: restart reference continuity and no restored approval power."""
from server.app import create_app
from server.chat_service import Generation
from tests.auth_helpers import AuthenticatedTestClient
from tests.test_chat_automation import PlannedRouter


def client(app):return AuthenticatedTestClient(app,base_url="http://127.0.0.1:8765",client=("127.0.0.1",12345))


def test_slot_question_survives_restart_and_approval_authority_does_not(settings):
    router=PlannedRouter(settings);app=create_app(settings,ai_router=router)
    with client(app) as c:
        c.portal.call(app.state.automation.scheduler.stop)
        router.plans=[{"clarification":"Wanneer en hoe lang wil je afspreken?"}]
        first=c.post("/api/v1/chat",json={"message":"Maak een afspraak met Noah","provider":"ollama"}).json()
        cid=first["conversation_id"]
        principal=app.state.security.store.authenticate(c.cookies.get("jarvis_access"))
        run=Generation("synthetic",cid,"ollama","",principal=principal)
        app.state.chat.automation_chat.remember(run,"pending",[{"id":"not-an-approval","shown":123,"nonce":"never-persist"}])
        assert c.get("/api/v1/natural/tasks").json()["items"][0]["questions"]
        with app.state.natural.store.transaction(principal) as (db,user):
            payload=db.execute("SELECT payload FROM natural_pending WHERE kind='automation_context'").fetchone()[0]
            assert "never-persist" not in payload and "shown" not in payload
    again_router=PlannedRouter(settings);again=create_app(settings,ai_router=again_router)
    with client(again) as c:
        c.portal.call(again.state.automation.scheduler.stop)
        again_router.plans=[{"clarification":"Wat is het onderwerp?"}]
        reply=c.post("/api/v1/chat",json={"message":"Vrijdag om drie uur, twee uur lang","conversation_id":cid,"provider":"ollama"}).json()
        assert reply["status"]=="completed" and "onderwerp" in reply["message"]
        instruction=again_router.planning_calls[-1][0][-1]["content"]
        assert "Maak een afspraak met Noah" in instruction and "Vrijdag om drie" in instruction
        principal=again.state.security.store.authenticate(c.cookies.get("jarvis_access"))
        run=Generation("synthetic",cid,"ollama","",principal=principal)
        memory=again.state.chat.automation_chat.memory(run)
        assert "pending" not in memory and "decision" not in memory


def test_task_resume_can_be_disabled(settings):
    router=PlannedRouter(settings);app=create_app(settings,ai_router=router)
    with client(app) as c:
        c.portal.call(app.state.automation.scheduler.stop)
        router.plans=[{"clarification":"Wanneer?"}]
        first=c.post("/api/v1/chat",json={"message":"Maak een afspraak","provider":"ollama"}).json()
        assert c.patch("/api/v1/natural/settings/tasks",json={"revision":0,"changes":{"resume":False}}).status_code==200
        app.state.chat.automation_chat.references.clear()
        principal=app.state.security.store.authenticate(c.cookies.get("jarvis_access"))
        run=Generation("synthetic",first["conversation_id"],"ollama","",principal=principal)
        assert app.state.natural.tasks.load(run)=={}
