"""Opt-in one short billed TTS sample through authenticated backend, isolated DB."""
import argparse
from dataclasses import replace
import io
import json
from pathlib import Path
import sys
import tempfile
import time
import wave

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from server.config import load_settings
from server.app import create_app
from tests.auth_helpers import AuthenticatedTestClient


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true');parser.add_argument('--voice-id',required=True)
    args=parser.parse_args()
    if not args.run:parser.error('Pass --run to authorize this one credit-consuming sample')
    actual=load_settings()
    output=ROOT/'.local/elevenlabs';output.mkdir(exist_ok=True,parents=True)
    with tempfile.TemporaryDirectory(prefix='jarvis-elevenlabs-') as temporary:
        settings=replace(load_settings(root=Path(temporary),environ={}),elevenlabs_api_key=actual.elevenlabs_api_key,automations_enabled=False)
        app=create_app(settings)
        with AuthenticatedTestClient(app,base_url='http://127.0.0.1:8765',client=('127.0.0.1',12345)) as client:
            config=client.get('/api/v1/natural/settings').json()
            changed=client.patch('/api/v1/natural/settings/voice',json={'revision':config['revision'],'changes':{'mode':'premium','elevenlabs_voice_id':args.voice_id,'elevenlabs_daily_limit':200,'elevenlabs_monthly_limit':200,'fallback':False,'cache':False}})
            assert changed.status_code==200,'Settings rejected'
            text='Goedenavond. Ik ben JARVIS. Uw persoonlijke assistent staat voor u klaar.'
            started=time.perf_counter();response=client.post('/api/v1/mobile/speech/synthesize',json={'text':text});seconds=time.perf_counter()-started
            if response.status_code!=200:
                print(json.dumps({'success':False,'http_status':response.status_code,'error':response.json().get('error',{}).get('code')}));return 2
            assert response.headers['X-JARVIS-TTS-Provider']=='elevenlabs','Fallback is not premium acceptance'
            with wave.open(io.BytesIO(response.content),'rb') as audio:
                rate=audio.getframerate();frames=audio.getnframes();raw=audio.readframes(frames)
                assert rate==24000 and frames>0 and any(raw),'Invalid/silent audio'
            (output/'voice-sample.wav').write_bytes(response.content)
            report={'success':True,'provider':'elevenlabs','model':'eleven_flash_v2_5','characters_requested':len(text),'seconds_to_complete_audio':round(seconds,3),'audio_seconds':round(frames/rate,3),'sample_rate':rate,'human_listening_acceptance':False,'real_google_accounts':False}
            (output/'live-test.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
    return 0


if __name__=='__main__':raise SystemExit(main())
