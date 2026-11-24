from uuid import uuid4
import asyncio
from contextlib import aclosing,suppress
from server.chat_service import Generation
from server.natural.store import Conflict


from server.natural.conversation import State,TRANSITIONS,is_ending
from tests.test_natural_settings_memory import natural as natural
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
    assert processing['state']=='PROCESSING'
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


def test_takeover_releases_reserved_voice_turn_before_returning(natural):
    app,c=natural
    session=c.post('/api/v1/natural/conversations/start',json={}).json()
    event(c,session,'listening');event(c,session,'processing')
    principal=app.state.security.store.authenticate(c.cookies.get('jarvis_access'))
    async def scenario():
        run=await app.state.chat.prepare("Synthetisch",principal=principal,conversation_id=session['conversation_id'],channel='voice',session_epoch=session['epoch'])
        taken=await app.state.natural.conversations.claim(principal,session['conversation_id'],takeover=True)
        assert run.cancel.is_set() and not app.state.chat.busy(session['conversation_id'])
        return taken
    taken=c.portal.call(scenario)
    assert taken['epoch']>session['epoch']
    event(c,taken,'listening');event(c,taken,'processing')
    reply=c.post('/api/v1/chat',json={'message':'Nieuwe beurt','channel':'voice','session_epoch':taken['epoch'],'conversation_id':taken['conversation_id']})
    assert reply.status_code==200


def test_takeover_waits_for_cleanup_without_holding_state_lock(natural):
    app,c=natural;session=c.post('/api/v1/natural/conversations/start',json={}).json()
    principal=app.state.security.store.authenticate(c.cookies.get('jarvis_access'))
    async def scenario():
        run=Generation('synthetic-cleanup',session['conversation_id'],'ollama','',principal=principal,channel='voice',session_epoch=session['epoch'],started=True)
        app.state.chat.active[run.request_id]=run
        async def cleanup():
            await run.cancel.wait()
            try:await app.state.natural.conversations.transition(principal,session['conversation_id'],State.LISTENING,session['epoch'])
            except Conflict:pass
            await asyncio.sleep(.05)
            app.state.chat.active.pop(run.request_id,None)
        pending=asyncio.create_task(cleanup())
        taken=await asyncio.wait_for(app.state.natural.conversations.claim(principal,session['conversation_id'],takeover=True),2)
        await pending
        assert not app.state.chat.busy(session['conversation_id'])
        return taken
    assert c.portal.call(scenario)['epoch']>session['epoch']


def test_repeated_disconnect_cannot_interrupt_final_cleanup(natural):
    app,c=natural;session=c.post('/api/v1/natural/conversations/start',json={}).json()
    event(c,session,'listening');event(c,session,'processing')
    principal=app.state.security.store.authenticate(c.cookies.get('jarvis_access'))
    async def scenario():
        run=await app.state.chat.prepare('Synthetisch',principal=principal,conversation_id=session['conversation_id'],channel='voice',session_epoch=session['epoch'])
        yielded=asyncio.Event();cleanup=asyncio.Event();release=asyncio.Event();never=asyncio.Event()
        original=app.state.natural.phase
        async def delayed_phase(current,target):
            if target==State.LISTENING:
                cleanup.set();await release.wait()
            return await original(current,target)
        app.state.natural.phase=delayed_phase
        async def consume():
            async with aclosing(app.state.chat.events(run)) as source:
                async for item in source:
                    if item['type']=='delta':yielded.set();await never.wait()
        task=asyncio.create_task(consume())
        try:
            await asyncio.wait_for(yielded.wait(),2)
            task.cancel();await asyncio.wait_for(cleanup.wait(),2)
            task.cancel()
            with suppress(asyncio.CancelledError):await task
            release.set()
            if app.state.chat.persistence_tasks:await asyncio.gather(*list(app.state.chat.persistence_tasks))
            assert run.request_id not in app.state.chat.active
            assert app.state.chat.store.get(run.conversation_id)['turns'][-1]['status']=='cancelled'
        finally:
            release.set();app.state.natural.phase=original
            if not task.done():task.cancel()
    c.portal.call(scenario)


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
