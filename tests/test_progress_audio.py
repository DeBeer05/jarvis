import base64
import io
import wave
from copy import deepcopy
from types import SimpleNamespace

from server.natural.models import UserSettings
from server.natural.progress_phrases import PHRASES,Selector,category,spoken,voice_key
from tests.test_natural_settings_memory import natural as natural
from tests.test_natural_context import patch


def wav():
    output=io.BytesIO()
    with wave.open(output,'wb') as audio:
        audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(24000);audio.writeframes(b'\0\0'*2400)
    return output.getvalue()


def test_catalogue_is_unique_and_selection_has_cooldown_without_model():
    assert len(PHRASES)==len({item['text'] for item in PHRASES.values()})==100
    config=UserSettings().model_dump();clock=[100.];selector=Selector(lambda:clock[0])
    first=selector.choose('device','calendar',list(PHRASES),config)
    assert first.startswith('calendar-') and selector.choose('device','calendar',list(PHRASES),config) is None
    clock[0]+=46
    assert selector.choose('device','calendar',list(PHRASES),config)!=first
    assert category('Bekijk mijn agenda')=='calendar'


def test_voice_changes_invalidate_cache_but_budget_change_does_not():
    config=UserSettings().model_dump();bootstrap=SimpleNamespace(elevenlabs_voice_id='voice')
    original=voice_key(config,bootstrap);changed=deepcopy(config)
    changed['voice']['elevenlabs_daily_limit']+=3000
    assert voice_key(changed,bootstrap)==original
    changed['voice']['speed']=1.1
    assert voice_key(changed,bootstrap)!=original
    assert spoken(PHRASES['general-00'],config)=='Een ogenblik.'


def test_prepare_real_wavs_is_idempotent_scoped_and_get_never_synthesizes(natural):
    app,c=natural;calls=[]
    class Synth:
        async def synthesize(self,request,text,voice,config):
            calls.append(text);return {'audio':base64.b64encode(wav()).decode()}
    app.state.natural.tts.providers['piper']=Synth()
    patch(c,'voice',{'mode':'manual','tts_provider':'piper'})
    response=c.post('/api/v1/natural/progress-audio/prepare',json={})
    assert response.status_code==200 and '"status": "completed"' in response.text and len(calls)==100
    manifest=c.get('/api/v1/natural/progress-audio').json()
    assert len(manifest['items'])==100
    assert c.get('/api/v1/natural/progress-audio/general-00').content==wav()
    assert c.get('/api/v1/natural/progress-audio/not-an-id').status_code==404
    c.post('/api/v1/natural/progress-audio/prepare',json={})
    assert len(calls)==100
