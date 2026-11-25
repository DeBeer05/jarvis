"""Opt-in ten synthetic planning conversations; temporary DB, no account tools/audio."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from server.config import load_settings
from server.app import create_app
from server.ai.providers import TextProvider,ProviderError
from tests.auth_helpers import AuthenticatedTestClient

SCENARIOS=[
 ['Ik wil dit weekend iets leuks doen.','Een dierentuin klinkt leuk.','Niet te ver weg.'],
 ['Ik wil zaterdagmiddag rond twee uur met Sam naar een museum, maximaal honderd euro samen.','Doe toch maar zondag en een uurtje later.','Kunnen we daarna nog ergens eten?'],
 ['Verzin een leuke date voor zondag.','Maakt me niet uit, verras me.','Het moet betaalbaar blijven.'],
 ['Ik wil morgen met Alex iets binnen doen.','Liever een museum.','Haal het museum eruit.'],
 ['Bedenk iets leuks voor morgen.','Dat klinkt leuk.','Zet het maar in mijn agenda.'],
 ['Ik wil zondag een dagtrip naar Utrecht met Sam.','Laten we met de trein gaan.','Ik wil eerst Alex ophalen.'],
 ['Wat kunnen we morgen doen? Het regent.','Een museum klinkt leuk.','Maak het iets goedkoper.'],
 ['Ik wil dit weekend iets leuks doen met Sam.','Hoe werkt een database-index?','Ga terug naar de planning, liever zondag.'],
 ['Ik wil zaterdag met Sam naar een museum. Tickets 20 euro per persoon.','Parkeren 5 euro totaal. Maximaal veertig euro samen.','Laten we toch met de trein gaan.'],
 ['Ik wil zondag iets romantisch doen.','Kunnen we daarna ergens eten?','Vergeet het hele uitje maar.'],
]


class RecordingProvider(TextProvider):
    output='';failure=None
    async def stream(self,messages):
        self.output='';self.failure=None
        try:
            async for text in super().stream(messages):self.output+=text;yield text
        except ProviderError as error:self.failure=error.code;raise


class RecordingClient(httpx.AsyncClient):
    failures=[]
    async def send(self,*args,**kwargs):
        response=await super().send(*args,**kwargs)
        if response.status_code>=400:
            raw=(await response.aread())[:100000].decode('utf-8',errors='replace')
            reason=next((code for code in ('RESOURCE_EXHAUSTED','INVALID_ARGUMENT','NOT_FOUND','PERMISSION_DENIED','UNAUTHENTICATED') if code in raw),'unclassified')
            self.failures.append({'http_status':response.status_code,'reason':reason})
        return response


class CPUClient(RecordingClient):
    def stream(self,method,url,**kwargs):
        if '/api/chat' in str(url) and isinstance(kwargs.get('json'),dict):
            kwargs['json'].setdefault('options',{}).update(num_gpu=0,num_thread=4,seed=42)
        return super().stream(method,url,**kwargs)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true');parser.add_argument('--provider',choices=['ollama','gemini'],default='ollama')
    parser.add_argument('--cpu-only',action='store_true');parser.add_argument('--count',type=int,default=10)
    parser.add_argument('--start',type=int,default=1,choices=range(1,11))
    parser.add_argument('--output',type=Path,default=ROOT/'.local/activity-planning/model-report.json')
    args=parser.parse_args()
    if not args.run:parser.error('--run is required')
    actual=load_settings(root=ROOT)
    if args.provider=='gemini' and not actual.gemini_api_key:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps({'provider':'gemini','status':'not_configured'}),encoding='utf-8');return 0
    records=[]
    with tempfile.TemporaryDirectory(prefix='jarvis-activity-') as temporary:
        settings=replace(load_settings(root=Path(temporary),environ={}),ai_provider=args.provider,preferred_provider=args.provider,
            gemini_api_key=actual.gemini_api_key if args.provider=='gemini' else '',gemini_model=actual.gemini_model,
            ollama_model='qwen2.5:3b',ollama_base_url=actual.ollama_base_url,max_output_tokens=420,
            automations_enabled=False,requests_per_minute=120,provider_timeout_seconds=55,ai_timeout_seconds=65)
        app=create_app(settings)
        recording=RecordingProvider(args.provider,settings,CPUClient if args.cpu_only else RecordingClient)
        app.state.chat.router.providers[args.provider]=recording
        async def events(payload):return {'items':[]}
        app.state.automation.integrations.events=events
        with patch('httpx.AsyncClient',CPUClient if args.cpu_only else RecordingClient):
            with AuthenticatedTestClient(app,base_url='http://127.0.0.1:8765',client=('127.0.0.1',12345)) as client:
                client.portal.call(app.state.automation.scheduler.stop)
                for index,scenario in enumerate(SCENARIOS[args.start-1:args.start-1+max(1,min(10,args.count))],start=args.start-1):
                    conversation=None
                    for turn,message in enumerate(scenario):
                        refresh=client.post('/api/v1/auth/refresh')
                        if refresh.status_code!=200:raise RuntimeError('Synthetic benchmark session refresh failed')
                        client.headers['X-Jarvis-CSRF']=client.cookies.get('jarvis_csrf','')
                        start=time.perf_counter()
                        RecordingClient.failures.clear()
                        response=client.post('/api/v1/chat',json={'message':message,'provider':args.provider,**({'conversation_id':conversation} if conversation else {})})
                        reply=response.json()
                        conversation=reply.get('conversation_id',conversation)
                        plan=client.get('/api/v1/natural/planning/'+conversation).json().get('planning') if conversation else None
                        record={'scenario':index+1,'turn':turn+1,'message':message,'seconds':round(time.perf_counter()-start,3),
                                'response':reply,'planning':plan,'model_raw':recording.output,'provider_error':recording.failure,'upstream_failures':list(RecordingClient.failures)}
                        records.append(record)
                        args.output.parent.mkdir(parents=True,exist_ok=True)
                        args.output.write_text(json.dumps({'provider':args.provider,'cpu_only':args.cpu_only,'synthetic':True,'real_accounts':False,'human_acceptance':False,'records':records},ensure_ascii=False,indent=2),encoding='utf-8')
                        print(json.dumps({'scenario':index+1,'turn':turn+1,'seconds':record['seconds'],'status':reply.get('status')}),flush=True)
                        if response.status_code!=200 or reply.get('status')!='completed':return 2
    return 0


if __name__=='__main__':raise SystemExit(main())
