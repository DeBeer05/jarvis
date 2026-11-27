"""No network/credits: official API mocked, real auth/database and usage limits."""
import asyncio
import base64
from copy import deepcopy
from dataclasses import replace
import io
import json
from types import SimpleNamespace
import wave

import httpx
import pytest

from tests.test_natural_settings_memory import natural as natural
from server.natural.elevenlabs import ElevenLabs


PCM=b'\x00\x00'*2400


@pytest.fixture
def premium(natural):
    app,c=natural;calls=[]
    class Bridge:
        async def request(self,*args):
            output=io.BytesIO()
            with wave.open(output,'wb') as audio:audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(24000);audio.writeframes(PCM)
            return {'audio':base64.b64encode(output.getvalue()).decode()}
    app.state.speech=Bridge()
    settings=replace(app.state.settings,elevenlabs_api_key='synthetic-eleven-credential')
    app.state.settings=app.state.chat.settings=settings
    def handler(request):
        calls.append(request)
        assert request.headers['xi-api-key']==settings.elevenlabs_api_key
        if request.url.path=='/v1/models':return httpx.Response(200,json=[{'model_id':key,'can_do_text_to_speech':True,'can_use_style':key=='eleven_multilingual_v2','can_use_speaker_boost':True,'languages':[{'language_id':'nl'}],'model_rates':{'character_cost_multiplier':.5}} for key in ('eleven_flash_v2_5','eleven_multilingual_v2','eleven_v3','eleven_v4')])
        if request.url.path=='/v2/voices':return httpx.Response(200,json={'voices':[{'voice_id':'SyntheticVoice1','name':'Synthetic male butler','category':'generated'}]})
        if request.url.path=='/v1/user/subscription':return httpx.Response(200,json={'character_count':50,'character_limit':10000,'tier':'synthetic'})
        return httpx.Response(200,content=PCM)
    def factory(**kwargs):return httpx.AsyncClient(transport=httpx.MockTransport(handler),**kwargs)
    provider=ElevenLabs(settings,app.state.natural.tts.usage,client_factory=factory)
    app.state.natural.tts.providers['elevenlabs']=provider
    config=c.get('/api/v1/natural/settings').json()
    response=c.patch('/api/v1/natural/settings/voice',json={'revision':config['revision'],'changes':{'mode':'premium','elevenlabs_voice_id':'SyntheticVoice1','cache':False,'fallback':False}})
    assert response.status_code==200,response.text
    return app,c,provider,calls


def test_dutch_pcm_is_valid_wav_and_only_supported_parameters_are_sent(premium):
    _,c,_,calls=premium
    response=c.post('/api/v1/mobile/speech/synthesize',json={'text':'Goedenavond, uw overzicht staat klaar.'})
    assert response.status_code==200 and response.headers['X-JARVIS-TTS-Provider']=='elevenlabs'
    with wave.open(io.BytesIO(response.content),'rb') as audio:
        assert audio.getframerate()==24000 and audio.getnchannels()==1 and audio.readframes(2400)==PCM
    body=json.loads(next(request.content for request in calls if request.method=='POST'))
    assert body['language_code']=='nl' and body['model_id']=='eleven_flash_v2_5'
    assert 'style' not in body['voice_settings']
    studio=c.get('/api/v1/natural/voice-studio').json()
    assert studio['usage']['monthly_reserved_credits']==len(body['text'])
    assert studio['account']['remaining_credits']==9950
    assert 'synthetic-eleven-credential' not in json.dumps(studio)


@pytest.mark.parametrize('code,expected',[(401,'tts_authentication'),(403,'tts_authentication'),(429,'tts_quota'),(503,'speech_unavailable')])
def test_provider_errors_never_leak_bodies_or_headers(premium,code,expected):
    _,c,provider,_=premium
    provider.client_factory=lambda **kwargs:httpx.AsyncClient(transport=httpx.MockTransport(lambda _:httpx.Response(code,json={'private':'provider diagnostic must stay private'})),**kwargs)
    response=c.post('/api/v1/mobile/speech/synthesize',json={'text':'Een korte test.'})
    assert response.status_code in (429,503) and response.json()['error']['code']==expected
    assert 'diagnostic' not in response.text and 'credential' not in response.text


def test_limit_prevents_synthesis_and_preview_cannot_increase_saved_budget(premium):
    _,c,_,calls=premium
    config=c.get('/api/v1/natural/settings').json()
    c.patch('/api/v1/natural/settings/voice',json={'revision':config['revision'],'changes':{'elevenlabs_daily_limit':0}})
    voice=c.get('/api/v1/natural/settings').json()['settings']['voice'];voice['elevenlabs_daily_limit']=1000000
    response=c.post('/api/v1/natural/voice-studio/preview',json={'text':'Begrensde voorbeeldtekst.','voice':voice})
    assert response.status_code==429 and not any(call.method=='POST' for call in calls)


@pytest.mark.parametrize('mode',['local','offline'])
def test_local_and_offline_modes_never_contact_elevenlabs(premium,mode):
    app,c,_,calls=premium
    class Bridge:
        async def request(self,*args):
            target=io.BytesIO()
            with wave.open(target,'wb') as audio:audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(24000);audio.writeframes(PCM)
            return {'audio':base64.b64encode(target.getvalue()).decode()}
    app.state.speech=Bridge()
    config=c.get('/api/v1/natural/settings').json()
    c.patch('/api/v1/natural/settings/voice',json={'revision':config['revision'],'changes':{'mode':mode}})
    result=c.post('/api/v1/mobile/speech/synthesize',json={'text':'Uitsluitend lokaal.'})
    assert result.status_code==200 and result.headers['X-JARVIS-TTS-Provider']!='elevenlabs' and not calls


def test_cache_hit_does_not_make_another_paid_request(premium):
    _,c,_,calls=premium
    config=c.get('/api/v1/natural/settings').json()
    c.patch('/api/v1/natural/settings/voice',json={'revision':config['revision'],'changes':{'cache':True}})
    for _ in range(2):assert c.post('/api/v1/mobile/speech/synthesize',json={'text':'Hetzelfde stemvoorbeeld.'}).status_code==200
    assert sum(call.method=='POST' for call in calls)==1


def test_cancel_closes_upstream_and_keeps_conservative_credit_reservation(premium):
    app,c,provider,calls=premium
    principal=app.state.security.store.authenticate(c.cookies.get('jarvis_access'))
    config=c.get('/api/v1/natural/settings').json()['settings']
    request=SimpleNamespace(state=SimpleNamespace(principal=principal))
    closed=[];stream_state={}
    class Hanging(httpx.AsyncByteStream):
        async def __aiter__(self):
            stream_state['started'].set()
            yield PCM
            await asyncio.Event().wait()
        async def aclose(self):closed.append(True)
    original=provider.client_factory
    def factory(**kwargs):
        def handler(request):
            if request.method=='POST':return httpx.Response(200,stream=Hanging())
            if request.url.path=='/v1/user/subscription':return httpx.Response(200,json={'character_count':0,'character_limit':10000})
            # Reuse bounded cached metadata, avoiding unrelated requests here.
            raise AssertionError('unexpected metadata request')
        return httpx.AsyncClient(transport=httpx.MockTransport(handler),**kwargs)
    async def scenario():
        await provider.inspect()
        provider.client_factory=factory
        async def metadata(**kwargs):return provider.metadata
        provider.inspect=metadata
        started=asyncio.Event();stream_state['started']=started
        task=asyncio.create_task(provider.synthesize(request,'Annuleerbare tekst.',config['voice'],config))
        try:
            # Reservation precedes HTTP: wait for an actual open stream, not a timer.
            await asyncio.wait_for(started.wait(),timeout=15)
        finally:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):await task
    c.portal.call(scenario)
    assert closed and provider.usage.usage(principal,config)['monthly_reserved_credits']==len('Annuleerbare tekst.')
    provider.client_factory=original


def test_sensitive_text_is_local_and_recognizable_secret_is_never_transmitted(premium):
    app,c,_,calls=premium
    config=deepcopy(c.get('/api/v1/natural/settings').json()['settings'])
    assert config['voice']['elevenlabs_sensitive_local']
    result=c.post('/api/v1/mobile/speech/synthesize',json={'text':'Uw medicatie is besproken.'})
    assert result.status_code in (200,429,503) and not any(call.method=='POST' for call in calls)
    result=c.post('/api/v1/mobile/speech/synthesize',json={'text':'sleutel sk_'+'a'*32})
    assert result.status_code==422 and not any(call.method=='POST' for call in calls)


def test_voice_secret_dpapi_roundtrip_and_config_redaction(tmp_path):
    from server.voice_secrets import save_secret,read_secret
    from server.config import load_settings
    target=tmp_path/'private.bin';value='synthetic-protected-voice-key'
    save_secret(target,value);assert read_secret(target)==value
    config=load_settings(root=tmp_path,environ={'ELEVENLABS_API_KEY_FILE':str(target)})
    assert config.elevenlabs_api_key==value and value not in repr(config)


def test_offline_voice_enforces_local_llm_policy():
    from server.natural.models import UserSettings
    from server.ai.policy import RequestPolicy
    config=UserSettings().model_dump();config['voice']['mode']='offline'
    assert RequestPolicy.from_document({'revision':1,'settings':config}).order('gemini','gemini')==['ollama']
