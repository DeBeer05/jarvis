from server.natural.private_context import PrivateContext
from tests.test_natural_context import build,client,patch
from tests.test_chat_automation import tools_chat as tools_chat,call,complete_after_decision


def test_history_off_keeps_active_context_only_in_ram_and_never_writes_text(settings):
    app,providers=build(settings)
    with client(app) as c:
        patch(c,"memory",{"history":False})
        first=c.post("/api/v1/chat",json={"message":"Mijn tijdelijke project heet lantaarn"}).json()
        cid=first["conversation_id"]
        c.post("/api/v1/chat",json={"message":"Hoe heet dat project?","conversation_id":cid})
        assert "tijdelijke project heet lantaarn" in str(providers["gemini"].calls[-1])
        assert c.get("/api/v1/chat/conversations/"+cid).json()["turns"]==[]
        with app.state.natural.store.database.connection() as db:
            assert not any(row[0] or row[1] for row in db.execute("SELECT user_text,assistant_text FROM chat_turns"))
            assert "lantaarn" not in db.execute("SELECT title FROM chat_conversations WHERE id=?",(cid,)).fetchone()[0]
        assert not c.get("/api/v1/natural/summaries").json()["items"]
    again,new_providers=build(settings)
    with client(again) as c:
        c.post("/api/v1/chat",json={"message":"Weet je nog hoe het project heet?","conversation_id":cid})
        assert "lantaarn" not in str(new_providers["gemini"].calls[-1])


def test_private_context_is_bounded_user_scoped_and_forgotten_sources_are_removed():
    from types import SimpleNamespace
    clock=[0.];cache=PrivateContext(lambda:clock[0])
    run=SimpleNamespace(conversation_id="one",request_id="turn-one",message="Privé feit",text="Antwoord",status="completed")
    cache.add(1,run,10)
    assert cache.get(1,"one",set(),10) and not cache.get(2,"one",set(),10)
    assert not cache.get(1,"one",{"turn-one"},10)
    for index in range(60):
        run.conversation_id=str(index);cache.add(1,run,10)
    assert len(cache.items)==50
    clock[0]=11.;assert not cache.get(1,"59",set(),10) and not cache.items


def test_exact_proposal_can_be_approved_without_persisting_chat_text(tools_chat):
    app,c,router=tools_chat
    patch(c,"memory",{"history":False})
    router.plans=[{"tool":"CalendarCreate","input":{"summary":"Noah"}}]
    shown=call(c,"Maak morgen om 15:00 een afspraak met Noah").json()
    row=app.state.automation.store.items()[0];executed=[]
    assert "Zal ik dit voor u uitvoeren?" in shown["message"]
    future=complete_after_decision(app,c,row,executed)
    result=call(c,"ja",shown["conversation_id"]).json();future.result(timeout=5)
    assert "afspraak is aangemaakt" in result["message"] and executed==[row["id"]]
    with app.state.natural.store.database.connection() as db:
        assert not any(row[0] or row[1] for row in db.execute("SELECT user_text,assistant_text FROM chat_turns"))
    assert c.get("/api/v1/natural/tasks").status_code==200


def test_retention_clears_expired_text_and_memory_but_keeps_task_receipts(settings):
    import json
    from datetime import datetime,UTC
    app,_=build(settings)
    with client(app) as c:
        patch(c,"privacy",{"history_days":1})
        response=c.post("/api/v1/chat",json={"message":"Synthetische oude inhoud"}).json();cid=response["conversation_id"]
        c.post("/api/v1/natural/memory",json={"content":"Synthetische verlopen voorkeur"})
        principal=app.state.security.store.authenticate(c.cookies.get("jarvis_access"));store=app.state.natural.store
        old=store.clock()-2*86400
        with store.transaction(principal,write=True) as (db,user):
            db.execute("UPDATE chat_turns SET created_at=? WHERE conversation_id=?",(datetime.fromtimestamp(old,UTC).isoformat(),cid))
            db.execute("UPDATE natural_memories SET expires=? WHERE user_id=?",(old,user))
            db.execute("INSERT INTO natural_pending VALUES (?,?,?,?,?,1,?,?,'waiting')",("pending-task",user,cid,"automation_context",json.dumps({"write_question":[{"instruction":"Maak een afspraak","question_hash":"synthetic"}]}),old,old))
        app.state.natural.retention.sweep()
        assert not c.get("/api/v1/chat/conversations/"+cid).json()["turns"]
        assert not c.get("/api/v1/natural/memory").json()["items"]
        with store.transaction(principal) as (db,user):
            assert db.execute("SELECT status FROM chat_turns WHERE id=?",(response["request_id"],)).fetchone()[0]=="completed"
            assert db.execute("SELECT payload FROM natural_pending WHERE id='pending-task'").fetchone()
        assert c.post("/api/v1/chat",json={"message":"Synthetische oude inhoud","request_id":response["request_id"]}).status_code==409


def test_memory_expiry_cleanup_can_be_disabled_without_retrieving_expired_facts(settings):
    app,_=build(settings)
    with client(app) as c:
        patch(c,"memory",{"prune_expired":False})
        c.post("/api/v1/natural/memory",json={"content":"Project lantaarn"})
        principal=app.state.security.store.authenticate(c.cookies.get("jarvis_access"));store=app.state.natural.store
        with store.transaction(principal,write=True) as (db,user):db.execute("UPDATE natural_memories SET expires=? WHERE user_id=?",(store.clock()-1,user))
        app.state.natural.retention.sweep()
        assert c.get("/api/v1/natural/memory").json()["items"]
        assert not app.state.natural.memory.retrieve(principal,"project lantaarn")


def test_automatic_preferences_are_opt_in_and_respect_ask_profile_and_sensitivity(settings):
    app,_=build(settings)
    with client(app) as c:
        c.post("/api/v1/chat",json={"message":"Ik plan afspraken liever na tien uur"})
        assert not c.get("/api/v1/natural/memory").json()["items"]
        patch(c,"memory",{"automatic":True})
        c.post("/api/v1/chat",json={"message":"Ik plan afspraken liever na tien uur"})
        proposed=c.get("/api/v1/natural/memory").json()["items"]
        assert len(proposed)==1 and proposed[0]["status"]=="proposed" and not proposed[0]["explicit"]
        principal=app.state.security.store.authenticate(c.cookies.get("jarvis_access"))
        assert not app.state.natural.memory.retrieve(principal,"afspraken")
        patch(c,"autonomy",{"profile":"within_rules"})
        c.post("/api/v1/chat",json={"message":"Ik plan afspraken liever na elf uur"})
        active=app.state.natural.memory.retrieve(principal,"afspraak")
        assert len(active)==1 and "elf" in active[0]["content"]
        c.post("/api/v1/chat",json={"message":"Ik plan afspraken liever bij de psycholoog"})
        c.post("/api/v1/chat",json={"message":"Ik gebruik liever een onbekend medicijn"})
        c.post("/api/v1/chat",json={"message":"Ik hou van mijn politieke partij"})
        assert len(c.get("/api/v1/natural/memory").json()["items"])==2


def test_profile_change_applies_preset_but_keeps_explicit_slider_edits(settings):
    app,_=build(settings)
    with client(app) as c:
        patch(c,"personality",{"profile":"professional","humor":23})
        values=c.get("/api/v1/natural/settings").json()["settings"]["personality"]
        assert values["formality"]==85 and values["humor"]==23
        patch(c,"personality",{"humor":42})
        assert c.get("/api/v1/natural/settings").json()["settings"]["personality"]["humor"]==42


def test_remember_this_and_forget_that_bind_one_visible_memory_and_remove_list_echo(settings):
    app,providers=build(settings)
    with client(app) as c:
        first=c.post("/api/v1/chat",json={"message":"Mijn tijdelijke voorkeur is programmeren in Python","provider":"ollama"}).json();cid=first["conversation_id"]
        remembered=c.post("/api/v1/chat",json={"message":"Onthou dit.","conversation_id":cid,"provider":"ollama"}).json()
        assert "onthouden" in remembered["message"]
        shown=c.post("/api/v1/chat",json={"message":"Wat weet je nog over mij?","conversation_id":cid,"provider":"ollama"}).json()
        assert "programmeren in Python" in shown["message"]
        forgotten=c.post("/api/v1/chat",json={"message":"Vergeet dat.","conversation_id":cid,"provider":"ollama"}).json()
        assert "verwijderd" in forgotten["message"] and not c.get("/api/v1/natural/memory").json()["items"]
        c.post("/api/v1/chat",json={"message":"Ga verder","conversation_id":cid,"provider":"ollama"})
        assert "programmeren in Python" not in str(providers["ollama"].calls[-1])


def test_generic_forget_cannot_choose_between_multiple_or_changed_memories(settings):
    app,_=build(settings)
    with client(app) as c:
        c.post("/api/v1/natural/memory",json={"content":"Voorkeur één"})
        c.post("/api/v1/natural/memory",json={"content":"Voorkeur twee"})
        shown=c.post("/api/v1/chat",json={"message":"Wat weet je nog over mij?"}).json()
        assert "Welke herinnering" in c.post("/api/v1/chat",json={"message":"Vergeet dat","conversation_id":shown["conversation_id"]}).json()["message"]
        assert len(c.get("/api/v1/natural/memory").json()["items"])==2
        c.post("/api/v1/natural/memory/clear",json={"confirmed":True})
        saved=c.post("/api/v1/chat",json={"message":"Onthoud dat mijn project lantaarn heet"}).json()
        item=c.get("/api/v1/natural/memory").json()["items"][0]
        c.put("/api/v1/natural/memory/"+item["id"],json={"revision":item["revision"],"content":"Het project heet nu atlas"})
        reply=c.post("/api/v1/chat",json={"message":"Vergeet dat","conversation_id":saved["conversation_id"]}).json()
        assert "verwijderd" not in reply["message"] and c.get("/api/v1/natural/memory").json()["items"]
