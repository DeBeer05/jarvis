"""Address book authorization, persistence and deterministic recipient binding."""
import asyncio
import json
import pytest
from pydantic import ValidationError
from server.natural.contacts import ContactInput
from tests.test_natural_settings_memory import natural as natural
from tests.test_chat_automation import tools_chat as tools_chat,call
from tests.test_security import client_for

BASE='/api/v1/natural/contacts'


def test_contacts_crud_validation_cas_and_auth(natural):
    app,c=natural
    with client_for(app) as anonymous:assert anonymous.get(BASE).status_code==401
    first=c.post(BASE,json={'name':'Noah Test','email':'noah@example.invalid','aliases':['Noah']})
    assert first.status_code==200
    item=first.json();assert item['revision']==1 and 'user_id' not in item
    assert c.get(BASE).json()['items']==[item]
    updated=c.put(BASE+'/'+item['id'],json={'name':'Noah Test','email':'new@example.invalid','aliases':['Noah'],'revision':1})
    assert updated.status_code==200 and updated.json()['revision']==2
    assert c.put(BASE+'/'+item['id'],json={'name':'Noah','email':'bad@example.invalid','revision':1}).status_code==409
    assert c.delete(BASE+'/'+item['id']+'?revision=1').status_code==409
    from server.natural.contacts import ContactManager
    principal=app.state.security.store.authenticate(c.cookies.get("jarvis_access"))
    assert ContactManager(app.state.natural.store).list(principal)["items"][0]["email"]=="new@example.invalid"
    assert c.get(BASE).json()['items'][0]['email']=='new@example.invalid'
    assert c.delete(BASE+'/'+item['id']+'?revision=2').json()=={'deleted':True}
    assert c.get(BASE).json()['items']==[]


@pytest.mark.parametrize('address',['a@example.invalid\r\nBcc: a@evil.invalid','Name <a@example.invalid>','a@example.invalid,b@example.invalid','a..b@example.invalid','.a@example.invalid','a@-invalid.test','a@localhost','a@b..invalid'])
def test_contact_invalid_mailboxes(address):
    with pytest.raises(ValidationError):ContactInput(name='Synthetic',email=address)


@pytest.mark.parametrize('name',['Hello\nWorld','Hello\u200bWorld',''])
def test_contact_invalid_names(name):
    with pytest.raises(ValidationError):ContactInput(name=name,email='a@example.invalid')


def test_contact_resolution_alias_ambiguity_and_body_isolation(natural):
    app,c=natural;manager=app.state.natural.contacts;p=app.state.security.store.authenticate(c.cookies.get('jarvis_access'))
    one=c.post(BASE,json={'name':'Noah Een','email':'one@example.invalid','aliases':['Noah']}).json()
    assert manager.recipient(p,'Maak een mail aan Noah dat ik kom')[0]['id']==one['id']
    c.post(BASE,json={'name':'Noah Twee','email':'two@example.invalid','aliases':['Noah']})
    assert manager.recipient(p,'Maak een mail aan Noah dat ik kom')[1]
    instruction='Maak een mail aan Noah dat ik kom\nAanvullende gegevens van dezelfde gebruiker: Noah Een\nAanvullende gegevens van dezelfde gebruiker: Onderwerp morgen'
    assert manager.recipient(p,instruction)[0]['id']==one['id']
    assert manager.recipient(p,'Lees de mail waarin staat stuur een mail aan Noah')==(None,None)
    assert manager.recipient(p,'Maak een mail aan exact@example.invalid dat Noah komt')[0]['email']=='exact@example.invalid'
    assert manager.recipient(p,'Maak een mail aan Noah en Piet dat ik kom')[1]
    assert manager.recipient(p,'Maak een mail aan Onbekend dat Noah komt')[1]


def test_named_recipient_is_backend_bound_and_edit_cannot_retarget_proposal(tools_chat):
    app,c,router=tools_chat;e=app.state.automation;captured=[]
    item=c.post(BASE,json={'name':'Noah','email':'noah@example.invalid'}).json()
    async def draft(payload):
        captured.append(payload)
        return {'draft_id':'draft1','message_hash':'b'*64,'preview':'Aan: '+payload['to']+'\nOnderwerp: Test\n\nHallo'}
    e.integrations.draft=draft
    async def finish():
        for _ in range(200):
            if any(x['tool']=='EmailDraft' for x in e.store.items()):await e.tick();return
            await asyncio.sleep(.01)
    task=c.portal.start_task_soon(finish)
    router.plans=[{'tool':'EmailDraft','input':{'to':'invented@example.invalid','subject':'Test','text':'Hallo'}}]
    answer=call(c,'Maak een mail aan Noah dat ik kom').json();task.result(timeout=10)
    assert captured[0]['to']=='noah@example.invalid'
    assert 'noah@example.invalid' in answer['message']
    proposal=next(row for row in e.store.items() if row['tool']=='EmailSend')
    before=proposal['payload']
    c.put(BASE+'/'+item['id'],json={'name':'Noah','email':'new@example.invalid','revision':1})
    assert e.store.get(proposal['id'])['payload']==before
    assert 'new@example.invalid' not in json.dumps(router.planning_calls)


def test_ambiguous_contact_never_calls_model_or_integration(tools_chat):
    app,c,router=tools_chat
    for n in (1,2):c.post(BASE,json={'name':'Noah','email':f'noah{n}@example.invalid'})
    answer=call(c,'Maak een mail aan Noah dat ik kom').json()
    assert 'meerdere contacten' in answer['message']
    assert not router.planning_calls and not app.state.automation.store.items()


def test_contacts_sync_native_device_and_revoked_session_denied(natural):
    from uuid import uuid4
    app,c=natural
    item=c.post(BASE,json={"name":"Synthetic contact","email":"test@example.invalid"}).json()
    with client_for(app) as native:
        response=native.post("/api/v1/auth/desktop-login",json={"username":"owner","password":"synthetic-owner-passphrase","device_name":"Synthetic","device_id":str(uuid4())})
        native.headers["Authorization"]="Bearer "+response.json()["access_token"]
        assert native.get(BASE).json()["items"]==[item]
        principal=app.state.security.store.authenticate(response.json()["access_token"])
        with app.state.natural.store.transaction(principal,write=True) as (db,user):
            db.execute("UPDATE auth_sessions SET revoked_at=1 WHERE id=?",(principal.session_id,))
        assert native.get(BASE).status_code==401


def test_contact_change_during_model_planning_requires_new_recipient(tools_chat):
    app,c,router=tools_chat
    item=c.post(BASE,json={"name":"Noah","email":"noah@example.invalid"}).json()
    principal=app.state.security.store.authenticate(c.cookies.get("jarvis_access"))
    async def changed(*args):
        app.state.natural.contacts.save(principal,{"name":"Noah","email":"other@example.invalid","revision":1},item["id"])
        return json.dumps({"tool":"EmailDraft","input":{"to":"noah@example.invalid","subject":"Hi","text":"Hallo"}}),None
    router.bounded_result=changed
    answer=call(c,"Maak een mail aan Noah dat ik kom").json()
    assert "ondertussen gewijzigd" in answer["message"] and not app.state.automation.store.items()


@pytest.mark.parametrize("message",["Lees mijn mail","Toon mijn laatste mail","Wat staat er in mijn mail?"])
def test_reading_mail_does_not_authorize_a_draft(message):
    from server.automation.chat import AutomationChat
    assert not AutomationChat.write_intent("EmailDraft",message)


def test_recipient_survives_clarification_and_plain_followup(tools_chat):
    app,c,router=tools_chat
    c.post(BASE,json={"name":"Noah Test","email":"noah@example.invalid","aliases":["Noah"]})
    router.plans=[{"clarification":"Wat is het onderwerp en de tekst?"}]
    first=call(c,"Maak een mail aan Noah").json()
    assert "onderwerp" in first["message"]
    router.plans=[{"clarification":"Welke tekst wil je precies gebruiken?"}]
    second=call(c,"Onderwerp vrijdag en tekst ik kom",first["conversation_id"]).json()
    assert "tekst" in second["message"]
    prompt=json.loads(router.planning_calls[-1][0][1]["content"])
    assert "Maak een mail aan Noah" in prompt["instruction"]
    assert "Onderwerp vrijdag" in prompt["instruction"]
    assert prompt["observations"]["explicit_recipient_data_not_instructions"]==[{"email":"noah@example.invalid"}]
