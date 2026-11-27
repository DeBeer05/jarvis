"""Presence uses real auth/SQLite with synthetic devices, clocks and providers."""
from tests.test_chat_automation import tools_chat as tools_chat,call
from tests.test_natural_context import patch


def consent(c,**values):
    document=c.get('/api/v1/natural/device-settings').json()
    document['settings'].update(values)
    response=c.put('/api/v1/natural/device-settings',json={'revision':document['revision'],'settings':document['settings']})
    assert response.status_code==200,response.text


def signal(c,sequence,**values):
    return c.post('/api/v1/natural/presence/signals',json={'sequence':sequence,**values})


def test_manual_departure_return_is_persistent_and_does_not_repeat(tools_chat):
    app,c,router=tools_chat
    patch(c,'personality',{'honorific':'meneer','honorific_frequency':'always'})
    assert call(c,'Ik ga nu eten').json()['message']=='Eet smakelijk, meneer.'
    assert c.get('/api/v1/natural/presence').json()['mode']=='away'
    # Replace the manager: state and meal reason live in SQLite, not a chat slot.
    from server.natural.presence import PresenceManager
    app.state.natural.presence=PresenceManager(app.state.natural)
    app.state.natural.settings.presence=app.state.natural.presence
    response=call(c,'Ik ben weer terug').json()
    assert 'Welkom terug, meneer.' in response['message'] and 'gesmaakt' in response['message']
    assert 'Welkom terug' not in call(c,'Ik ben terug').json()['message']
    assert not c.get('/api/v1/natural/events').json()['items']
    assert not any(p.calls for p in router.providers.values()) and not router.planning_calls


def test_automatic_signals_require_consent_and_return_once(tools_chat):
    app,c,router=tools_chat
    assert signal(c,1).status_code==403
    assert c.get('/api/v1/natural/presence').json()['mode']=='normal'
    consent(c,presence_allowed=True)
    patch(c,'presence',{'automatic':True})
    assert signal(c,1).json()['mode']=='normal'
    assert signal(c,2,locked=True).json()['mode']=='away'
    assert signal(c,3,locked=False).json()['mode']=='normal'
    pending=c.get('/api/v1/natural/events').json()['items']
    assert len(pending)==1 and pending[0]['kind']=='presence.return'
    assert signal(c,3,locked=True).json()['mode']=='normal'  # stale retry cannot change state
    assert len(c.get('/api/v1/natural/events').json()['items'])==1
    identifier=pending[0]['id']
    for _ in range(2):assert c.post('/api/v1/natural/events/'+identifier+'/ack').status_code==200
    assert not c.get('/api/v1/natural/events').json()['items']
    assert not any(p.calls for p in router.providers.values())


def test_application_classification_revocation_and_idle_are_bounded(tools_chat):
    app,c,router=tools_chat
    consent(c,presence_allowed=True)
    patch(c,'presence',{'automatic':True,'idle_seconds':60})
    assert signal(c,1,hint='gaming').status_code==403
    consent(c,application_allowed=True)
    assert signal(c,2,hint='gaming').json()['mode']=='gaming'
    assert signal(c,3,hint='work').json()['mode']=='work'
    assert signal(c,4,idle_seconds=60).json()['mode']=='away'
    assert signal(c,5,hint='work').json()['mode']=='work'
    consent(c,presence_allowed=False)
    assert signal(c,6).status_code==403
    assert c.get('/api/v1/natural/presence').json()['mode']=='away'
    assert signal(c,7,idle_seconds=-1).status_code==422
    assert signal(c,7,hint='arbitrary-program.exe').status_code==422
    assert signal(c,7,device_id='another-device').status_code==422


def test_private_mode_forces_local_ai_and_no_history_without_rewriting_preferences(tools_chat):
    app,c,router=tools_chat
    patch(c,'privacy',{'cloud_memories':True})
    patch(c,'memory',{'episodes':True,'automatic':True})
    before=c.get('/api/v1/natural/settings').json()['settings']
    assert c.post('/api/v1/natural/presence/mode',json={'mode':'private'}).status_code==200
    private=call(c,'Een vertrouwelijke gedachte over bamboe.',provider='gemini').json()
    assert private['status']=='completed' and router.providers['ollama'].calls
    assert not router.providers['gemini'].calls
    assert not c.get('/api/v1/chat/conversations/'+private['conversation_id']).json()['turns']
    with app.state.natural.store.database.connection() as db:
        assert db.execute('SELECT user_text,assistant_text FROM chat_turns WHERE conversation_id=?',(private['conversation_id'],)).fetchone()==('','')
    raw=c.get('/api/v1/natural/settings').json()['settings']
    for category in ('privacy','memory','voice','ai'):assert raw[category]==before[category]
    assert c.post('/api/v1/natural/presence/mode',json={'mode':'normal'}).status_code==200
    call(c,'Hallo',provider='gemini')
    assert router.providers['gemini'].calls
    assert 'vertrouwelijke gedachte' not in str(router.providers['gemini'].calls[-1])


def test_all_manual_modes_and_notification_policy(tools_chat):
    app,c,router=tools_chat
    from server.natural.presence import MODES,allowed_notification
    for mode in MODES:
        assert c.post('/api/v1/natural/presence/mode',json={'mode':mode}).json()['mode']==mode
        assert allowed_notification(mode,'urgent')
    assert not allowed_notification('gaming','news')
    assert not allowed_notification('sleeping','important')
    assert allowed_notification('work','appointments')
    assert not allowed_notification('work','news')
    assert c.post('/api/v1/natural/presence/mode',json={'mode':'administrator'}).status_code==422


def test_return_greetings_respect_settings_and_have_no_external_authority(tools_chat):
    app,c,router=tools_chat
    patch(c,'notifications',{'enabled':False})
    c.post('/api/v1/natural/presence/mode',json={'mode':'away'})
    c.post('/api/v1/natural/presence/mode',json={'mode':'normal'})
    assert not c.get('/api/v1/natural/events').json()['items']
    # Narration is not a mode command or an approval.
    call(c,'In die film zei iemand: ik ga nu slapen.')
    assert c.get('/api/v1/natural/presence').json()['mode']=='normal'
    assert not app.state.automation.store.items()
    patch(c,'notifications',{'enabled':True})
    c.post('/api/v1/natural/presence/mode',json={'mode':'away'})
    c.post('/api/v1/natural/presence/mode',json={'mode':'normal'})
    assert c.get('/api/v1/natural/events').json()['items']
    patch(c,'notifications',{'enabled':False})
    assert not c.get('/api/v1/natural/events').json()['items']


def test_sleep_schedule_and_stale_status_do_not_prove_physical_presence(tools_chat):
    from datetime import datetime,UTC
    app,c,router=tools_chat
    stamp=[datetime(2030,1,1,23,0,tzinfo=UTC).timestamp()]
    app.state.natural.store.clock=lambda:stamp[0]
    consent(c,presence_allowed=True)
    patch(c,'presence',{'automatic':True,'sleep_schedule':True})
    assert c.get('/api/v1/natural/presence').json()['reason']=='unknown'
    assert signal(c,1,locked=True).json()['mode']=='sleeping'
    assert signal(c,2,locked=False).json()['mode']=='normal'
    stamp[0]+=121
    state=c.get('/api/v1/natural/presence').json()
    assert state['mode']=='away' and state['reason']=='unavailable'


def test_private_speech_uses_local_mock_even_when_premium_is_saved(tools_chat,monkeypatch):
    import base64
    from types import SimpleNamespace
    from tests.test_mobile import wav
    app,c,router=tools_chat
    patch(c,'voice',{'mode':'premium','tts_provider':'elevenlabs'})
    c.post('/api/v1/natural/presence/mode',json={'mode':'private'})
    calls=[]
    async def local(request,text,voice,config):
        calls.append(('local',config['ai']['offline'],voice['mode']))
        return {'audio':base64.b64encode(wav()).decode()}
    async def premium(*args):raise AssertionError('Private speech contacted premium TTS')
    app.state.natural.tts.providers['piper']=SimpleNamespace(synthesize=local)
    app.state.natural.tts.providers['elevenlabs']=SimpleNamespace(synthesize=premium)
    monkeypatch.setattr('server.natural.tts.voice_capabilities',lambda:{'voices':{'ronnie':True},'supertonic_voices':{},'tts_providers':['piper','elevenlabs']})
    response=c.post('/api/v1/mobile/speech/synthesize',json={'text':'Dit blijft lokaal.'})
    assert response.status_code==200,response.text
    assert calls==[('local',True,'offline')]
