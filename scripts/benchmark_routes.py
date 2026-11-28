"""Measured authenticated routing/approval latency; synthetic accounts/providers only."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server.app import create_app
from server.config import load_settings
from server.ai.router import AIRouter
from tests.ai_helpers import FakeProvider
from tests.auth_helpers import AuthenticatedTestClient


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path);parser.add_argument('--samples',type=int,default=3);args=parser.parse_args()
    if not 1<=args.samples<=5:parser.error('Use 1–5 samples')
    values=[]
    with tempfile.TemporaryDirectory(prefix='jarvis-route-bench-') as temporary:
        settings=replace(load_settings(root=Path(temporary),environ={}),automations_enabled=False,ai_provider='ollama',preferred_provider='ollama')
        providers={key:FakeProvider(('Synthetisch modelantwoord.',)) for key in ('ollama','gemini','groq')}
        app=create_app(settings,ai_router=AIRouter(settings,providers));calls={'weather':0,'calendar':0}
        with AuthenticatedTestClient(app,base_url='http://127.0.0.1:8765',client=('127.0.0.1',12345)) as client:
            engine=app.state.automation
            doc=client.get('/api/v1/natural/settings').json()
            doc['settings']['autonomy']['actions'].update(CalendarCreate='ask',CalendarUpdate='ask')
            doc['settings']['briefings']['location']='Testplaats'
            response=client.put('/api/v1/natural/settings',json={'revision':doc['revision'],'settings':doc['settings']});response.raise_for_status()
            async def calendar(tool,payload,key):
                calls['calendar']+=1
                return {'id':'synthetic'+str(calls['calendar']),'etag':'version1','summary':payload['summary'],'start':{'dateTime':payload['start']},'end':{'dateTime':payload['end']}}
            async def events(_):return {'items':[]}
            async def weather(*_):
                calls['weather']+=1
                return {'location':'Testplaats','values':{'temperature_2m':12,'precipitation':0,'wind_speed_10m':8},'units':{'temperature_2m':'°C','precipitation':'mm','wind_speed_10m':'km/h'},'observed_at':'2026-11-28T12:00'}
            engine.integrations.change=calendar;engine.integrations.events=events;app.state.natural.briefings.sources.weather=weather
            def turn(text,cid=None):
                started=time.perf_counter();response=client.post('/api/v1/chat',json={'message':text,'provider':'ollama',**({'conversation_id':cid} if cid else {})});response.raise_for_status()
                return response.json(),(time.perf_counter()-started)*1000
            for _ in range(args.samples):
                proposed,_=turn('Maak morgen om 14:00 een afspraak die Synthetische proef heet')
                result,approval_ms=turn('ja',proposed['conversation_id'])
                before=sum(len(provider.calls) for provider in providers.values());previous_weather=calls['weather']
                _,weather_ms=turn('Hoe is het weer?',result['conversation_id'])
                values.append({'approval_ms':round(approval_ms,3),'weather_ms':round(weather_ms,3),'weather_llm_calls':sum(len(provider.calls) for provider in providers.values())-before,'weather_source_calls':calls['weather']-previous_weather,'calendar_verified_before_reply':calls['calendar']>len(values)})
                client.portal.call(engine.tick)
    report={'scope':'synthetic authenticated HTTP, mocked external APIs and LLM; not microphone/model latency','samples':values,'median_approval_ms':statistics.median(row['approval_ms'] for row in values),'median_weather_ms':statistics.median(row['weather_ms'] for row in values)}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))


if __name__=='__main__':main()
