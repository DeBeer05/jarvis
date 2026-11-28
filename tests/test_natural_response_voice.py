"""Response/voice security and spoken output, with no real audio devices/accounts."""
import asyncio
import base64
import json
from types import SimpleNamespace
from copy import deepcopy
import pytest
from providers.speech_format import format_speech
from server.natural.models import UserSettings
from server.natural.responses import mode_for,extractive,response_prompt
from server.natural.tts import TTSRouter
from server.security.types import AuthError
from tests.test_natural_settings_memory import natural as natural
from tests.test_chat_automation import tools_chat as tools_chat,call
from tests.test_mobile import wav


def test_dutch_format_preserves_values_and_removes_markup():
    text=format_speech('**Afspraak** op 2026-11-25 om 15:30. €25,50, 8 GB, 12 km en 20%. [Bron](https://example.invalid/secret).')
    for value in ('vijfentwintig november','half vier','vijfentwintig euro en vijftig cent','acht gigabyte','twaalf kilometer','twintig procent','Bron'):assert value in text
    assert 'https' not in text and '*' not in text
    assert 'a@example.invalid' in format_speech('Aan: <a@example.invalid>')
    assert format_speech('{"private_id":"example"}')=='De technische gegevens staan op het scherm.'
    assert 'print' not in format_speech('```python\nprint(1)\n```')


def test_response_modes_and_critical_information_are_not_word_truncation():
    config=UserSettings().model_dump()
    assert mode_for(config,'Vraag',True)=='short' and mode_for(config,'Vraag',False)=='balanced'
    assert mode_for(config,'Lees de volledige mail voor',True)=='full'
    result=extractive('Eerste zin. Tweede zin. Achtergrond. Extra uitleg. De deadline is morgen. Mogelijk zijn er kosten.', 'ultrashort')
    assert 'deadline' in result and 'kosten' in result and 'Achtergrond' not in result
    config['personality']['profile']='classic_butler'
    assert 'butler' in response_prompt(config,'Vraag',True)
    assert 'hooguit af en toe' in response_prompt(config,'Vraag',True)
    config['personality']['honorific_frequency']='off'
    assert 'Gebruik geen aanspreekvorm' in response_prompt(config,'Vraag',True)


def test_temporary_and_permanent_spoken_settings_are_closed_local_commands(tools_chat):
    app,c,router=tools_chat
    before=c.get('/api/v1/natural/settings').json()
    answer=call(c,'Geef kortere antwoorden').json()
    assert 'tijdelijk' in answer['message']
    assert c.get('/api/v1/natural/settings').json()['revision']==before['revision']
    call(c,'Geef voortaan kortere antwoorden',answer['conversation_id'])
    assert c.get('/api/v1/natural/settings').json()['settings']['responses']['mode']=='short'
    call(c,'Je hoeft me voortaan geen meneer te noemen',answer['conversation_id'])
    assert c.get('/api/v1/natural/settings').json()['settings']['personality']['honorific_frequency']=='off'
    assert not router.planning_calls and not app.state.automation.store.items()
    principal=app.state.security.store.authenticate(c.cookies.get('jarvis_access'))
    config=app.state.natural.responses.apply(principal,'other-conversation',before['settings'])
    assert config['responses']['mode']=='auto'


def test_butler_address_policy_applies_to_text_and_voice():
    config=UserSettings().model_dump()
    config['personality'].update(profile='classic_butler',honorific='meneer',honorific_frequency='always')
    UserSettings.model_validate(config)
    for voice in (False,True):
        prompt=response_prompt(config,'Ik ben terug van het eten',voice)
        for phrase in ('u en uw','ieder antwoord','Britse humor','bij terugkomst','geverifieerde bronnen','geen nieuwe rechten'):
            assert phrase.casefold() in prompt.casefold()
        assert 'hooguit af en toe' not in prompt
    config['personality']['honorific_frequency']='occasionally'
    assert 'hooguit af en toe' in response_prompt(config,'Hallo',False)
    config['personality']['honorific_frequency']='off'
    assert 'Gebruik geen aanspreekvorm' in response_prompt(config,'Hallo',True)


def test_always_address_command_persists_without_model_or_automation(tools_chat):
    app,c,router=tools_chat
    before=c.get('/api/v1/natural/settings').json()['settings']
    answer=call(c,'Spreek mij voortaan altijd aan met meneer').json()
    assert 'opgeslagen' in answer['message']
    saved=c.get('/api/v1/natural/settings').json()['settings']
    assert saved['personality']['honorific']=='meneer'
    assert saved['personality']['honorific_frequency']=='always'
    for category in ('voice','autonomy','notifications','privacy'):
        assert saved[category]==before[category]
    assert not router.planning_calls and not app.state.automation.store.items()


def test_voice_stream_has_separate_speech_and_keeps_full_email_and_deadline(tools_chat):
    app,c,router=tools_chat
    async def search(_):return {'messages':[{'id':'mail1'}]}
    body='De uitnodiging is binnen. We plannen een gesprek. Dit is extra achtergrond. Nog meer achtergrond. De deadline is vrijdag.'
    async def read(identifier,include=False):return {'id':identifier,'payload':{'headers':[{'name':'Subject','value':'Sollicitatie'}],'mimeType':'text/plain','body':{'data':base64.urlsafe_b64encode(body.encode()).decode()}}}
    app.state.automation.integrations.mail_search=search;app.state.automation.integrations.mail_read=read
    router.plans=[{'tool':'EmailSearch','input':{'query':'in:inbox'}}]
    first=call(c,'Toon mijn mail').json()
    session=c.post('/api/v1/natural/conversations/start',json={'conversation_id':first['conversation_id']}).json()
    for name in ('listening','processing'):assert c.post('/api/v1/natural/conversations/'+session['conversation_id']+'/events',json={'event':name,'epoch':session['epoch']}).status_code==200
    response=c.post('/api/v1/chat/stream',json={'message':'Wat staat er in die sollicitatie','channel':'voice','provider':'ollama','conversation_id':session['conversation_id'],'session_epoch':session['epoch']})
    assert response.status_code==200,response.text
    events=[json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
    assert events[0]['speech_protocol']==1 and events[-1]['status']=='completed'
    written=''.join(event['text'] for event in events if event['type']=='delta')
    speech=''.join(event['text'] for event in events if event['type']=='speech')
    assert 'Nog meer achtergrond' in written and 'Nog meer achtergrond' not in speech
    assert 'deadline' in speech and 'uitnodiging' in speech
    assert 'De deadline' in c.get('/api/v1/chat/conversations/'+session['conversation_id']).json()['turns'][-1]['assistant_text']


def test_full_detail_override_and_approval_safety():
    from server.natural.responses import IntelligentResponseManager
    config=UserSettings().model_dump();manager=IntelligentResponseManager(None)
    run=SimpleNamespace(natural_context={'settings':config},message='Lees alles voor',response_data=None,wait_state=None)
    original='Eerste zin. Tweede zin. Derde zin. Vierde zin.'
    assert manager.summarize(run,original)==original
    run.message='Maak een mail';run.wait_state='WAITING_FOR_APPROVAL'
    assert manager.summarize(run,original)==original


def test_tts_fallback_is_once_and_pinned_for_whole_utterance(monkeypatch):
    import server.mobile as mobile
    import server.natural.tts as module
    config=UserSettings().model_dump();calls=[]
    monkeypatch.setattr(module,'voice_capabilities',lambda:{'voices':{'ronnie':True},'supertonic_voices':{'M1':True}})
    async def preferences(_):return {}
    async def inference(request,operation,payload):
        calls.append(payload)
        if payload['provider']=='supertonic':raise AuthError('speech_unavailable','Synthetic failure',503)
        return {'audio':base64.b64encode(wav()).decode()}
    monkeypatch.setattr(mobile,'audio_preferences',preferences);monkeypatch.setattr(mobile,'inference_call',inference)
    request=SimpleNamespace(state=SimpleNamespace(principal=SimpleNamespace(session_id='s',device_id='d')))
    async def scenario():
        router=TTSRouter()
        first=await router.synthesize(request,'Zin een',config,'same-utterance')
        second=await router.synthesize(request,'Zin twee',config,'same-utterance')
        assert first['selected_provider']==second['selected_provider']=='piper'
        assert [item['provider'] for item in calls]==['supertonic','piper','piper']
    asyncio.run(scenario())


def test_tts_never_switches_after_successful_audio_or_retries_revocation(monkeypatch):
    import server.mobile as mobile
    import server.natural.tts as module
    config=UserSettings().model_dump();calls=[]
    monkeypatch.setattr(module,'voice_capabilities',lambda:{'voices':{'ronnie':True},'supertonic_voices':{'M1':True}})
    async def preferences(_):return {}
    async def inference(request,operation,payload):
        calls.append(payload)
        if len(calls)>1:raise AuthError('speech_unavailable','Synthetic failure',503)
        return {'audio':'synthetic'}
    monkeypatch.setattr(mobile,'audio_preferences',preferences);monkeypatch.setattr(mobile,'inference_call',inference)
    request=SimpleNamespace(state=SimpleNamespace(principal=SimpleNamespace(session_id='s',device_id='d')))
    async def scenario():
        router=TTSRouter();await router.synthesize(request,'Zin een',config,'one')
        with pytest.raises(AuthError):await router.synthesize(request,'Zin twee',config,'one')
        assert len(calls)==2 and all(item['provider']=='supertonic' for item in calls)
    asyncio.run(scenario())


def test_voice_studio_preview_is_authenticated_and_never_saves_settings(natural):
    app,c=natural
    class Bridge:
        async def request(self,operation,payload):return {'audio':base64.b64encode(wav()).decode(),'seconds':.01}
    app.state.speech=Bridge()
    document=c.get('/api/v1/natural/settings').json()
    voice=deepcopy(document['settings']['voice']);voice.update(mode='manual',tts_provider='piper')
    response=c.post('/api/v1/natural/voice-studio/preview',json={'text':'Dit is een synthetisch stemvoorbeeld.','voice':voice})
    assert response.status_code==200 and response.json()['microphone_used'] is False
    assert c.get('/api/v1/natural/settings').json()==document
    assert c.post('/api/v1/natural/voice-studio/preview',json={'text':'Test','voice':{'api_key':'never'}}).status_code==422


def test_speech_cache_is_scoped_and_memory_revision_invalidates(monkeypatch):
    import server.mobile as mobile
    import server.natural.tts as module
    config=UserSettings().model_dump();calls=[];version=[1]
    monkeypatch.setattr(module,'voice_capabilities',lambda:{'voices':{'ronnie':True},'supertonic_voices':{}})
    async def preferences(_):return {}
    async def inference(request,operation,payload):calls.append(payload);return {'audio':'synthetic'}
    monkeypatch.setattr(mobile,'audio_preferences',preferences);monkeypatch.setattr(mobile,'inference_call',inference)
    principal=SimpleNamespace(session_id='session',device_id='device')
    context=SimpleNamespace(context=SimpleNamespace(memory_version=lambda _:version[0]))
    request=SimpleNamespace(state=SimpleNamespace(principal=principal),app=SimpleNamespace(state=SimpleNamespace(natural=context)))
    async def scenario():
        router=TTSRouter()
        await router.synthesize(request,'Zelfde tekst',config)
        assert (await router.synthesize(request,'Zelfde tekst',config))['cache_hit'] and len(calls)==1
        version[0]+=1
        assert not (await router.synthesize(request,'Zelfde tekst',config)).get('cache_hit') and len(calls)==2
        principal.session_id='different-session'
        assert not (await router.synthesize(request,'Zelfde tekst',config)).get('cache_hit') and len(calls)==3
    asyncio.run(scenario())


def test_dutch_calendar_and_iso_timestamp_pronunciation_keeps_date_and_zone():
    assert 'vijfentwintig november' in format_speech('25-11 15:30')
    assert 'vijfentwintig november' in format_speech('25-11-2026 15:30')
    result=format_speech('2026-11-25T14:30:00Z',timezone='Europe/Amsterdam')
    assert 'half vier' in result and 'vijfentwintig november' in result
    assert 'nul zes een twee drie vier vijf zes zeven acht' in format_speech('Bel 0612345678')


@pytest.mark.parametrize("parts",[["```json\n{\"field\":\"first. ","More raw metadata\"}\n```"],["[1, 2, ","3]"]])
def test_stream_never_speaks_partial_code_fences_or_raw_json(parts):
    from server.chat_service import Generation
    from server.natural.responses import IntelligentResponseManager
    run=Generation('synthetic','conversation','ollama','Test',natural_context={'settings':UserSettings().model_dump()})
    async def source():
        for part in parts:yield {'type':'delta','text':part}
    async def scenario():
        events=[event async for event in IntelligentResponseManager(None).stream(run,source())]
        spoken=''.join(e['text'] for e in events if e['type']=='speech')
        assert 'field' not in spoken and 'metadata' not in spoken and '[1' not in spoken
        assert ''.join(e['text'] for e in events if e['type']=='delta')==''.join(parts)
    asyncio.run(scenario())


def test_generic_followup_does_not_reopen_mail_after_unrelated_chat(tools_chat):
    app,c,router=tools_chat
    async def search(_):return {"messages":[{"id":"mail1"}]}
    async def read(identifier,body=False):return {"id":identifier,"payload":{"headers":[],"mimeType":"text/plain","body":{"data":base64.urlsafe_b64encode(b'Synthetic body').decode()}}}
    app.state.automation.integrations.mail_search=search;app.state.automation.integrations.mail_read=read
    router.plans=[{"tool":"EmailSearch","input":{"query":"in:inbox"}}]
    first=call(c,"Toon mijn mail").json()
    call(c,"Hallo",first['conversation_id'])
    before=len(router.planning_calls)
    follow=call(c,"Wat bedoel je?",first['conversation_id']).json()
    assert follow['message']=='Gewone chat.' and len(router.planning_calls)==before


def test_response_profile_changes_are_versioned_and_preserve_authority(natural):
    app,c=natural
    before=c.get('/api/v1/natural/settings').json()
    response=c.patch('/api/v1/natural/settings/responses',json={'revision':before['revision'],'changes':{'profile':'technical'}})
    assert response.status_code==200
    after=response.json()['settings']
    assert after['responses']['technical_detail']==85 and after['responses']['written']=='extended'
    assert after['autonomy']==before['settings']['autonomy']
