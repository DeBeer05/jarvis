import asyncio
from uuid import uuid4

import pytest

from server.natural.conversation import State,TRANSITIONS,is_ending
from tests.test_natural_settings_memory import natural
from tests.test_security import client_for
from tests.auth_helpers import TEST_PASSWORD


def event(client,session,name):
    return client.post('/api/v1/natural/conversations/'+session['conversation_id']+'/events',json={'event':name,'epoch':session['epoch']})


def test_state_machine_start_turn_interrupt_and_end(natural):
    app,c=natural
    session=c.post('/api/v1/natural/conversations/start',json={}).json()
    assert session['state']=='ACTIVATING' and set(TRANSITIONS)==set(State)
    listening=event(c,session,'listening').json();assert listening['state']=='LISTENING'
    speaking=event(c,listening,'user_speaking').json();assert speaking['state']=='USER_SPEAKING'
    processing=event(c,speaking,'processing').json()
    principal=app.state.security.store.authenticate(c.cookies.get('jarvis_access'))
    thinking=c.portal.call(app.state.natural.conversations.transition,principal,session['conversation_id'],State.THINKING,session['epoch'])
    answer=event(c,thinking,'assistant_speaking').json()
    interrupted=event(c,answer,'interrupted').json()
    assert interrupted['state']=='INTERRUPTED' and interrupted['epoch']==session['epoch']+1
    assert event(c,answer,'listening').status_code==409,'Old callbacks cannot revive audio'
    assert event(c,interrupted,'listening').status_code==200
    assert event(c,interrupted,'ending').status_code==200
    assert c.get('/api/v1/natural/conversations/'+session['conversation_id']+'/state').json()['state']=='STANDBY'


def test_device_handoff_is_explicit_and_epoch_protected(natural):
    app,c=natural;session=c.post('/api/v1/natural/conversations/start',json={}).json()
    event(c,session,'listening')
    with client_for(app) as other:
        credentials=other.post('/api/v1/auth/desktop-login',json={'username':'owner','password':TEST_PASSWORD,'device_name':'Synthetic other device','device_id':str(uuid4())}).json()
        other.headers['Authorization']='Bearer '+credentials['access_token']
        assert other.post('/api/v1/natural/conversations/start',json={'conversation_id':session['conversation_id']}).status_code==409
        taken=other.post('/api/v1/natural/conversations/start',json={'conversation_id':session['conversation_id'],'takeover':True}).json()
        assert taken['epoch']>session['epoch'] and event(c,session,'user_speaking').status_code==409
        assert event(other,taken,'listening').status_code==200
        assert c.get('/api/v1/natural/conversations/'+session['conversation_id']+'/state').json()['device_id']==taken['device_id']


def test_idle_timeout_recovery_and_live_settings(natural):
    app,c=natural;clock=[app.state.natural.store.clock()]
    app.state.natural.store.clock=lambda:clock[0]
    config=c.get('/api/v1/natural/settings').json()
    assert c.patch('/api/v1/natural/settings/conversations',json={'revision':config['revision'],'changes':{'inactivity_seconds':10}}).status_code==200
    session=c.post('/api/v1/natural/conversations/start',json={}).json();event(c,session,'listening')
    clock[0]+=11
    assert c.get('/api/v1/natural/conversations/'+session['conversation_id']+'/state').json()['state']=='STANDBY'
    new=c.post('/api/v1/natural/conversations/start',json={'conversation_id':session['conversation_id']}).json()
    app.state.natural.conversations.recover()
    assert c.get('/api/v1/natural/conversations/'+session['conversation_id']+'/state').json()['state']=='RECONNECTING'
    assert event(c,new,'listening').status_code==409
    assert c.patch('/api/v1/natural/settings/conversations',json={'revision':1,'changes':{'enabled':False}}).status_code==200
    assert c.post('/api/v1/natural/conversations/start',json={}).status_code==400


def test_gratitude_with_continuation_is_not_end_command():
    phrases=['Bedankt JARVIS','Dat was alles','Je mag stoppen','Tot later']
    assert is_ending('Bedankt JARVIS!',phrases)
    assert is_ending('dat was alles.',phrases)
    assert not is_ending('Bedankt JARVIS, maar wat staat er morgen gepland?',phrases)
    assert not is_ending('Kun je zeggen "tot later"?',phrases)


def test_client_cannot_claim_executing_state_or_foreign_conversation(natural):
    app,c=natural;session=c.post('/api/v1/natural/conversations/start',json={}).json()
    assert event(c,session,'EXECUTING_ACTION').status_code==422
    with app.state.natural.store.transaction(app.state.security.store.authenticate(c.cookies.get('jarvis_access')),write=True) as (db,user):
        db.execute('UPDATE natural_conversation_owners SET user_id=2 WHERE conversation_id=?',(session['conversation_id'],))
    assert c.get('/api/v1/natural/conversations/'+session['conversation_id']+'/state').status_code==400


def test_ten_voice_turns_use_one_conversation_and_real_lifecycle(natural):
    app,c=natural
    session=c.post('/api/v1/natural/conversations/start',json={}).json()
    assert event(c,session,'listening').status_code==200
    for index in range(10):
        assert event(c,session,'processing').status_code==200
        response=c.post('/api/v1/chat',json={'message':f'Synthetische spreekbeurt {index}','channel':'voice','session_epoch':session['epoch'],'conversation_id':session['conversation_id']})
        assert response.status_code==200 and response.json()['status']=='completed'
        assert response.json()['conversation_id']==session['conversation_id']
        state=c.get('/api/v1/natural/conversations/'+session['conversation_id']+'/state').json()
        assert state['state']=='ASSISTANT_SPEAKING'
        assert event(c,session,'listening').status_code==200
    history=c.get('/api/v1/chat/conversations/'+session['conversation_id']).json()
    assert len(history['turns'])==10
    assert event(c,session,'ending').status_code==200


def test_heartbeat_cannot_extend_idle_conversation_forever(natural):
    app,c=natural;clock=[app.state.natural.store.clock()]
    app.state.natural.store.clock=lambda:clock[0]
    c.patch('/api/v1/natural/settings/conversations',json={'revision':0,'changes':{'inactivity_seconds':10}})
    session=c.post('/api/v1/natural/conversations/start',json={}).json();event(c,session,'listening')
    clock[0]+=11
    assert event(c,session,'heartbeat').status_code==409
    state=c.get('/api/v1/natural/conversations/'+session['conversation_id']+'/state').json()
    assert state['state']=='STANDBY' and state['epoch']>session['epoch']


def test_handoff_rejects_old_audio_before_any_new_turn_is_stored(natural):
    app,c=natural;session=c.post('/api/v1/natural/conversations/start',json={}).json();event(c,session,'listening')
    with client_for(app) as other:
        credentials=other.post('/api/v1/auth/desktop-login',json={'username':'owner','password':TEST_PASSWORD,'device_name':'Synthetic takeover','device_id':str(uuid4())}).json()
        other.headers['Authorization']='Bearer '+credentials['access_token']
        taken=other.post('/api/v1/natural/conversations/start',json={'conversation_id':session['conversation_id'],'takeover':True}).json()
        stale=c.post('/api/v1/chat',json={'message':'Oude invoer mag niet starten','channel':'voice','session_epoch':session['epoch'],'conversation_id':session['conversation_id']})
        assert stale.status_code==409 and not app.state.chat.active
        assert c.get('/api/v1/chat/conversations/'+session['conversation_id']).json()['turns']==[]
        event(other,taken,'listening');event(other,taken,'processing')
        fresh=other.post('/api/v1/chat',json={'message':'Nieuwe invoer','channel':'voice','session_epoch':taken['epoch'],'conversation_id':taken['conversation_id']})
        assert fresh.status_code==200 and fresh.json()['status']=='completed'
