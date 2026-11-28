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
        old_access=c.cookies.get('jarvis_access')
        document=c.get('/api/v1/natural/settings').json()
        assert c.patch('/api/v1/natural/settings/autonomy',json={'revision':document['revision'],'changes':{'actions':{'CalendarCreate':'ask'}}}).status_code==200
        run=Generation("synthetic",cid,"ollama","",principal=principal)
        app.state.chat.automation_chat.remember(run,"pending",[{"id":"not-an-approval","shown":123,"nonce":"never-persist"}])
        assert c.get("/api/v1/natural/tasks").json()["items"][0]["questions"]
        with app.state.natural.store.transaction(principal) as (db,user):
            payload=db.execute("SELECT payload FROM natural_pending WHERE kind='automation_context'").fetchone()[0]
            assert "never-persist" not in payload and "shown" not in payload
    again_router=PlannedRouter(settings);again=create_app(settings,ai_router=again_router)
    with client(again) as c:
        c.portal.call(again.state.automation.scheduler.stop)
        c.headers['Authorization']='Bearer '+old_access
        again_router.plans=[{"clarification":"Wat is het onderwerp?"}]
        reply=c.post("/api/v1/chat",json={"message":"Vrijdag om drie uur, twee uur lang","conversation_id":cid,"provider":"ollama"}).json()
        assert reply["status"]=="completed" and "wijzigingsvoorstel" in reply["message"]
        assert not again_router.planning_calls
        principal=again.state.security.store.authenticate(old_access)
        run=Generation("synthetic",cid,"ollama","",principal=principal)
        memory=again.state.chat.automation_chat.memory(run)
        assert memory['pending'][0]['session']==principal.session_id and 'nonce' not in memory['pending'][0]


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


def test_slot_questions_follow_user_policy_and_configured_timezone(settings):
    router=PlannedRouter(settings);app=create_app(settings,ai_router=router)
    with client(app) as c:
        c.portal.call(app.state.automation.scheduler.stop)
        assert c.patch("/api/v1/natural/settings/tasks",json={"revision":0,"changes":{"combine_questions":False}}).status_code==200
        assert c.patch("/api/v1/natural/settings/general",json={"revision":1,"changes":{"timezone":"Asia/Tokyo"}}).status_code==200
        router.plans=[{"clarification":"Wanneer wil je afspreken?"}]
        response=c.post("/api/v1/chat",json={"message":"Maak een afspraak met Noah","provider":"ollama"}).json()
        assert response["status"]=="completed"
        assert 'Op welke datum' in response['message'] and 'hoe laat' not in response['message']
        assert not router.planning_calls


def test_calendar_results_are_displayed_in_configured_timezone(settings):
    router=PlannedRouter(settings);app=create_app(settings,ai_router=router)
    with client(app) as c:
        c.portal.call(app.state.automation.scheduler.stop)
        assert c.patch("/api/v1/natural/settings/general",json={"revision":0,"changes":{"timezone":"Asia/Tokyo"}}).status_code==200
        async def events(_):return {"items":[{"id":"synthetic","summary":"Test","start":{"dateTime":"2030-01-01T12:00:00+00:00"},"end":{"dateTime":"2030-01-01T13:00:00+00:00"}}]}
        app.state.automation.integrations.events=events
        result=c.post("/api/v1/chat",json={"message":"Wat staat er morgen in mijn agenda?","provider":"ollama"}).json()
        assert result["status"]=="completed" and "01-01 21:00" in result["message"] and "01-01 22:00" in result["message"]


def test_natural_create_and_free_form_title_keep_all_previous_slots(settings):
    router=PlannedRouter(settings);app=create_app(settings,ai_router=router)
    with client(app) as c:
        c.portal.call(app.state.automation.scheduler.stop)
        document=c.get('/api/v1/natural/settings').json()
        assert c.patch('/api/v1/natural/settings/autonomy',json={'revision':document['revision'],'changes':{'actions':{'CalendarCreate':'ask'}}}).status_code==200
        router.plans=[{"clarification":"Wat is de titel?"}]
        first=c.post("/api/v1/chat",json={"message":"Ik wil morgen om drie uur een afspraak maken","provider":"ollama"}).json()
        cid=first["conversation_id"]
        router.plans=[{"clarification":"Hoe lang duurt de afspraak?"}]
        title=c.post("/api/v1/chat",json={"message":"Bioscoop met Noah","conversation_id":cid,"provider":"ollama"}).json()
        assert title["status"]=="completed" and "wijzigingsvoorstel" in title["message"]
        assert not router.planning_calls
        jobs=app.state.automation.store.items()
        assert len(jobs)==1 and jobs[0]["tool"]=="CalendarCreate" and jobs[0]["status"]=="approval"
        import json
        from datetime import datetime,timedelta
        payload=json.loads(jobs[0]['payload'])
        assert payload['summary']=='Bioscoop met Noah'
        assert datetime.fromisoformat(payload['end'])-datetime.fromisoformat(payload['start'])==timedelta(hours=1)


def test_capabilities_are_server_facts_and_open_tasks_use_local_route(settings):
    router=PlannedRouter(settings);app=create_app(settings,ai_router=router)
    app.state.automation.integrations.status=lambda:{"connected":True,"features":["calendar_read","calendar_write","gmail_read","gmail_compose"]}
    with client(app) as c:
        response=c.post("/api/v1/chat",json={"message":"Wat kan je allemaal doen?","provider":"ollama"}).json()
        assert response["status"]=="completed" and "je agenda opvragen" in response["message"] and "afspraken voorbereiden" in response["message"]
        assert not router.planning_calls
        tasks=c.post("/api/v1/chat",json={"message":"Welke taken staan nog open?","provider":"ollama"}).json()
        assert "geen openstaande" in tasks["message"] and not router.planning_calls
