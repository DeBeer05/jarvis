"""Phase 7.5 foundations: actual auth/CAS, FTS isolation, privacy and migration."""
from uuid import uuid4

import pytest

from tests.test_security import make_app, client_for
from tests.auth_helpers import fast_hasher,owner_hash,login


@pytest.fixture
def natural(settings):
    app=make_app(settings);app.state.security.hasher=fast_hasher()
    with client_for(app) as client:
        app.state.security.store.create_owner("owner",owner_hash());assert login(client).status_code==200
        yield app,client


def test_settings_are_versioned_strict_and_secrets_absent(natural):
    app,c=natural
    base=c.get("/api/v1/natural/settings").json();assert base["revision"]==0
    updated=c.patch("/api/v1/natural/settings/personality",json={"revision":0,"changes":{"humor":80}})
    assert updated.status_code==200 and updated.json()["revision"]==1
    assert c.patch("/api/v1/natural/settings/general",json={"revision":0,"changes":{"address_name":"Test"}}).status_code==409
    assert c.patch("/api/v1/natural/settings/personality",json={"revision":1,"changes":{"humor":101}}).status_code==422
    assert c.patch("/api/v1/natural/settings/ai",json={"revision":1,"changes":{"api_key":"never-a-setting"}}).status_code==422
    assert c.patch("/api/v1/natural/settings/privacy",json={"revision":1,"changes":{"retain_raw_audio":True}}).status_code==422
    assert c.patch("/api/v1/natural/settings/autonomy",json={"revision":1,"changes":{"actions":{"EmailSend":"allow"}}}).status_code==422
    text=c.get("/api/v1/natural/settings/export").text
    assert "api_key" not in text and "refresh_token" not in text
    assert c.post("/api/v1/natural/settings/reset",json={"revision":1,"category":"personality"}).json()["settings"]["personality"]["humor"]==35


def test_global_settings_sync_but_audio_device_values_are_isolated(natural):
    app,c=natural
    with client_for(app) as other:
        response=other.post("/api/v1/auth/desktop-login",json={"username":"owner","password":"synthetic-owner-passphrase","device_name":"Synthetic Windows","device_id":str(uuid4())})
        assert response.status_code==200
        other.headers["Authorization"]="Bearer "+response.json()["access_token"]
        assert c.patch("/api/v1/natural/settings/general",json={"revision":0,"changes":{"address_name":"Voorbeeld"}}).status_code==200
        assert other.get("/api/v1/natural/settings").json()["settings"]["general"]["address_name"]=="Voorbeeld"
        device=c.get("/api/v1/natural/device-settings").json()["settings"];device["input_device"]=3
        assert c.put("/api/v1/natural/device-settings",json={"revision":0,"settings":device}).status_code==200
        assert other.get("/api/v1/natural/device-settings").json()["settings"]["input_device"]==-1


def test_memory_fts_retrieval_correction_forget_and_source_invalidation(natural):
    app,c=natural;manager=app.state.natural.memory
    principal=app.state.security.store.authenticate(c.cookies.get("jarvis_access"))
    old=manager.save(principal,{"content":"Afspraken liefst na negen uur","key":"appointment_preference"},source_turn="synthetic-source-1")
    new=manager.save(principal,{"content":"Afspraken voortaan na tien uur","key":"appointment_preference"},source_turn="synthetic-source-2")
    found=manager.retrieve(principal,"afspraken",limit=8)
    assert [x["id"] for x in found]==[new["id"]]
    assert old["id"] in [row["id"] for row in manager.list(principal,status="outdated")["items"]]
    assert c.get("/api/v1/natural/memory").status_code==200
    assert c.delete("/api/v1/natural/memory/"+new["id"]).status_code==200
    assert not manager.retrieve(principal,"tien")
    with app.state.natural.store.transaction(principal) as (db,user):
        assert db.execute("SELECT count(*) FROM natural_memory_fts WHERE id=?",(new["id"],)).fetchone()[0]==0
        assert db.execute("SELECT count(*) FROM natural_forgotten WHERE user_id=?",(user,)).fetchone()[0]==2


def test_memory_sync_off_scopes_search_edits_and_clear_to_origin_device(natural):
    app,c=natural
    first=c.post("/api/v1/natural/memory",json={"content":"Project sterrenlicht gebruikt Python"}).json()
    config=c.get("/api/v1/natural/settings").json()
    assert c.patch("/api/v1/natural/settings/memory",json={"revision":config["revision"],"changes":{"synchronize":False}}).status_code==200
    with client_for(app) as other:
        login=other.post("/api/v1/auth/desktop-login",json={"username":"owner","password":"synthetic-owner-passphrase","device_name":"Synthetic other","device_id":str(uuid4())})
        other.headers["Authorization"]="Bearer "+login.json()["access_token"]
        assert other.get("/api/v1/natural/memory").json()["items"]==[]
        assert other.post("/api/v1/natural/memory/search",json={"query":"sterrenlicht"}).json()["items"]==[]
        assert other.delete("/api/v1/natural/memory/"+first["id"]).status_code==400
        assert other.put("/api/v1/natural/memory/"+first["id"],json={"content":"Changed","revision":first["revision"]}).status_code==400
        second=other.post("/api/v1/natural/memory",json={"content":"Project vuurtoren gebruikt Kotlin"}).json()
        principal=app.state.security.store.authenticate(login.json()["access_token"])
        assert not app.state.natural.memory.retrieve(principal,"sterrenlicht")
        assert len(app.state.natural.memory.retrieve(principal,"vuurtoren"))==1
        assert other.put("/api/v1/natural/memory/"+second["id"],json={"content":"Project vuurtoren gebruikt Java","revision":second["revision"]}).status_code==200
        assert other.post("/api/v1/natural/memory/clear",json={"confirmed":True}).status_code==200
        assert [m["id"] for m in c.get("/api/v1/natural/memory").json()["items"]]==[first["id"]]
        config=c.get("/api/v1/natural/settings").json()
        assert c.patch("/api/v1/natural/settings/memory",json={"revision":config["revision"],"changes":{"synchronize":True}}).status_code==200
        assert other.get("/api/v1/natural/memory").json()["items"][0]["id"]==first["id"]


def test_sensitive_memory_requires_explicit_consent_and_revision(natural):
    app,c=natural
    payload={"content":"Mijn medicatie moet worden besproken","category":"person","sensitivity":"sensitive"}
    assert c.post("/api/v1/natural/memory",json=payload).status_code==400
    payload["consent_sensitive"]=True
    row=c.post("/api/v1/natural/memory",json=payload).json()
    assert row["sensitivity"]=="sensitive"
    update={**payload,"content":"Mijn medicatievoorkeur is gewijzigd","revision":row["revision"]}
    assert c.put("/api/v1/natural/memory/"+row["id"],json=update).status_code==200
    assert c.put("/api/v1/natural/memory/"+row["id"],json=update).status_code==409
    assert not app.state.natural.memory.retrieve(app.state.security.store.authenticate(c.cookies.get("jarvis_access")),"medicatie")
    assert c.post("/api/v1/natural/memory/clear",json={"confirmed":False}).status_code==400
    assert c.post("/api/v1/natural/memory/clear",json={"confirmed":True}).json()["original_conversations_retained"]
    assert c.get("/api/v1/natural/memory").json()["items"]==[]


def test_natural_routes_authentication_and_revoked_devices(natural):
    app,c=natural
    with client_for(app) as anonymous:
        assert anonymous.get("/api/v1/natural/settings").status_code==401
        assert anonymous.get("/api/v1/natural/memory").status_code==401
    assert c.post("/api/v1/natural/memory",json={"content":"Test","user_id":2}).status_code==422
    principal=app.state.security.store.authenticate(c.cookies.get("jarvis_access"))
    with app.state.natural.store.transaction(principal,write=True) as (db,user):db.execute("UPDATE auth_devices SET revoked_at=1 WHERE id=?",(principal.device_id,))
    assert c.get("/api/v1/natural/settings").status_code==401


def test_settings_offer_only_supported_voice_providers_and_installed_choices(natural,monkeypatch):
    app,c=natural
    capabilities={"runtime_installed":False,"whisper_models":{"whisper-small":True,"whisper-base":False,"whisper-tiny":False},"voices":{"ronnie":True,"mls":False}}
    monkeypatch.setattr("server.natural.capabilities.voice_capabilities",lambda:capabilities)
    schema=c.get("/api/v1/natural/settings/schema").json()
    voice=schema["user"]["$defs"]["Voice"]["properties"]
    assert voice["tts_provider"]["enum"]==["auto","piper","supertonic"]
    assert voice["tts_provider"]["x-unavailable"]==["supertonic"]
    assert voice["whisper_model"]["x-unavailable"]==["whisper-base","whisper-tiny"]
    assert c.patch("/api/v1/natural/settings/voice",json={"revision":0,"changes":{"tts_provider":"xtts"}}).status_code==422
    assert c.patch("/api/v1/natural/settings/voice",json={"revision":0,"changes":{"whisper_model":"whisper-tiny"}}).status_code==400
    assert c.patch("/api/v1/natural/settings/voice",json={"revision":0,"changes":{"voice":"mls"}}).status_code==400
    assert c.patch("/api/v1/natural/settings/voice",json={"revision":0,"changes":{"speed":1.2}}).status_code==200
