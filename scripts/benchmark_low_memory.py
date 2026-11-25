"""Opt-in CPU-only speech chain on synthetic data; no mini-PC deployment or RAM-limit claim."""
import argparse
import asyncio
import base64
from contextlib import asynccontextmanager
from dataclasses import replace
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'desktop-client')]
import httpx
from server.ai.providers import TextProvider
from server.ai.router import AIRouter
from server.app import create_app
from server.config import load_settings
import server.natural.responses as responses
from tests.auth_helpers import AuthenticatedTestClient
from jarvis_client.voice.worker import InferenceWorker
from jarvis_client.voice.settings import VoiceSettings


class CPUClient(httpx.AsyncClient):
    @asynccontextmanager
    async def stream(self,method,url,**kwargs):
        if method=='POST' and str(url).endswith('/api/chat'):
            body=kwargs['json'];body['options'].update(num_gpu=0,num_thread=4,seed=42)
        async with super().stream(method,url,**kwargs) as response:yield response


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-local',action='store_true')
    parser.add_argument('--warmup',action='store_true',help='Warm the CPU model before measured comparisons')
    parser.add_argument('--output',type=Path,default=ROOT/'.local/voice-latency/cpu-chain.json')
    args=parser.parse_args()
    if not args.run_local:parser.error('--run-local required; no inference started')
    voice=VoiceSettings(device='cpu');worker=InferenceWorker();records=[]
    boundary=responses.speech_boundary
    def old_boundary(text,first):
        match=re.search(r'[.!?](?:\s+|$)',text)
        return match.end() if match and match.end()<len(text) else None
    try:
        # Input is generated locally; no microphone, playback or personal data.
        audio,_=worker.synthesize('Leg in een lange zin uit hoe een computer een verzoek verwerkt, met een inleiding en daarna de uitleg.',voice,lambda:True)
        worker.transcribe(audio,voice,lambda:True)
        worker.request('tts',replace(voice,provider='supertonic'),text='Een synthetische opwarmzin.',supertonic_voice='M3',steps=8)
        with tempfile.TemporaryDirectory(prefix='jarvis-cpu-chain-') as temporary:
            settings=replace(load_settings(root=Path(temporary),environ={}),ai_provider='ollama',preferred_provider='ollama',
                ollama_model='qwen2.5:3b',automations_enabled=False,provider_timeout_seconds=90,ai_timeout_seconds=120)
            router=AIRouter(settings,{'ollama':TextProvider('ollama',settings,CPUClient)})
            app=create_app(settings,ai_router=router)
            with AuthenticatedTestClient(app,base_url='http://127.0.0.1:8765',client=('127.0.0.1',12345)) as c:
                principal=app.state.security.store.authenticate(c.cookies.get('jarvis_access'))
                async def probe(mode):
                    responses.speech_boundary=old_boundary if mode=='baseline' else boundary
                    start=time.perf_counter();stt=await asyncio.to_thread(worker.transcribe,audio,voice,lambda:True)
                    stt_wall=time.perf_counter()-start
                    run=await app.state.chat.prepare(stt['text'],'ollama',principal=principal,channel='voice')
                    first=None;tts=None;phrase=None;runtime=None
                    async for event in app.state.chat.events(run):
                        if event['type']=='speech' and first is None:
                            phrase=event['text']
                            result=await asyncio.to_thread(worker.request,'tts',replace(voice,provider='supertonic'),text=phrase,supertonic_voice='M3',steps=8)
                            assert base64.b64decode(result['audio'])[:4]==b'RIFF'
                            first=time.perf_counter()-start;tts=result['seconds'];runtime=result.get('runtime_stats')
                    return {'mode':mode,'stt_wall_seconds':stt_wall,'ai_first_token_seconds':run.first_token_seconds,
                        'first_answer_pcm_seconds':first,'first_phrase':phrase,'first_phrase_tts_seconds':tts,
                        'written_answer':run.text,'helper_runtime':runtime,'text_total_seconds':time.perf_counter()-start}
                if args.warmup:
                    warmup=c.portal.call(probe,'baseline')
                    print(json.dumps({'warmup_first_pcm_seconds':warmup['first_answer_pcm_seconds']}),flush=True)
                for mode in ('baseline','candidate','candidate','baseline'):
                    record=c.portal.call(probe,mode);records.append(record)
                    print(json.dumps({k:v for k,v in record.items() if k not in ('written_answer','first_phrase','helper_runtime')}),flush=True)
                resources=app.state.natural.diagnostics.resources(worker.process.pid if worker.process else None)
        memory=None
        if os.name=='nt':
            command="Get-Process | Where-Object {$_.ProcessName -match '^(ollama.*|llama-server|runner)$'} | Select-Object ProcessName,WorkingSet64,PrivateMemorySize64 | ConvertTo-Json -Compress"
            result=subprocess.run(['powershell.exe','-NoProfile','-Command',command],capture_output=True,text=True,timeout=5,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),check=False)
            if result.returncode==0 and result.stdout.strip():memory=json.loads(result.stdout)
        with httpx.Client(trust_env=False,timeout=5) as client:
            runtime=[{key:row.get(key) for key in ('name','size','size_vram','context_length')} for row in client.get('http://127.0.0.1:11434/api/ps').json().get('models',[]) if row.get('name')=='qwen2.5:3b']
        assert runtime and all(row['size_vram']==0 for row in runtime),'CPU-only execution not confirmed'
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps({'cpu_only_requested':True,'cpu_threads':4,'model':'qwen2.5:3b','voice':'M3','records':records,
            'median_first_pcm_seconds':{mode:statistics.median(r['first_answer_pcm_seconds'] for r in records if r['mode']==mode) for mode in ('baseline','candidate')},
            'ollama_process_memory':memory,'ollama_runtime':runtime,'server_harness_resources':resources,'warmup_used':args.warmup,'eight_gb_limit_enforced':False,
            'helper_self_reported_resident_bytes':max(r['helper_runtime'].get('ram_bytes',0) for r in records),
            'comparison_limit':'Live generated answers can differ; these medians are descriptive, not a controlled speedup percentage.',
            'physical_audio_tested':False,'human_acceptance':False},ensure_ascii=False,indent=2),encoding='utf-8')
    finally:
        responses.speech_boundary=boundary;worker.cancel();deadline=time.monotonic()+8
        while worker.busy and time.monotonic()<deadline:time.sleep(.05)


if __name__=='__main__':main()
