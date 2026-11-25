"""Opt-in real local conversation benchmark using synthetic HTTP sessions only.

No user database, cloud keys, microphone, accounts or model downloads. Raw
synthetic transcripts stay in the explicitly chosen local output directory.
"""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from server.ai.providers import TextProvider
from server.ai.router import AIRouter
from server.app import create_app
from server.config import load_settings
from tests.auth_helpers import AuthenticatedTestClient


STORY=[
    'Mijn schilderproject heet Koperlicht. Ik gebruik koper en blauw.',
    'Ik heb vandaag echt een lange dag gehad.',
    'Vooral druk. Ik heb nauwelijks tijd voor mezelf gehad.',
    'Misschien ga ik morgen iets leuks doen.',
    'Misschien kan ik met een vriend ergens heen.',
    'Ik heb eigenlijk geen zin in die afspraak morgen.',
    'Die mail van gisteren maakte me aan het lachen.',
    'Ik bedoel vooral dat de schrijver zo droog uit de hoek kwam.',
    'Een beetje droge humor vind ik wel prettig.',
    'Mijn agenda voelt deze week nogal vol.',
    'Laten we even over iets anders praten: ik speel ook gitaar.',
    'Blues is op het moment mijn favoriete muziek.',
    'Soms klinkt mijn gitaar alsof hij ook een lange dag heeft gehad.',
    'Ik wil niets regelen; gewoon even hardop nadenken.',
    'Ik twijfel tussen een rustige avond en nog even schilderen.',
    'Toch liever rustig. Morgen is er ook weer een dag.',
    'Die herinneringen aan onze vorige vakantie zijn wel fijn.',
    'We zaten toen aan zee en het waaide nogal.',
    'Ik denk dat ik zulke kleuren in mijn schilderij kan gebruiken.',
    'Hoe heet mijn schilderproject ook alweer en welke kleuren gebruik ik?',
]


class LocalRouter(AIRouter):
    def __init__(self,settings):
        super().__init__(settings,{'ollama':TextProvider('ollama',settings)})
        self.planning_calls=0
        self.contexts=[]

    async def bounded_result(self,messages,mode=None):
        self.planning_calls+=1
        return await super().bounded_result(messages,mode)

    async def stream(self,messages,mode):
        self.contexts.append(messages)
        async for event in super().stream(messages,mode):yield event


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-local',action='store_true',help='Explicitly run the already installed local model')
    parser.add_argument('--turns',type=int,nargs='+',default=[20,50],choices=[20,50])
    parser.add_argument('--output',type=Path,default=Path('.local/experience-benchmark/report.json'))
    args=parser.parse_args()
    if not args.run_local:parser.error('--run-local is required; no inference was started')
    reports=[]
    with tempfile.TemporaryDirectory(prefix='jarvis-experience-') as temporary:
        settings=replace(load_settings(root=Path(temporary),environ={}),ai_provider='ollama',
            preferred_provider='ollama',ollama_model='qwen2.5:3b',automations_enabled=False,
            requests_per_minute=120,provider_timeout_seconds=60,ai_timeout_seconds=90)
        router=LocalRouter(settings);app=create_app(settings,ai_router=router)
        with AuthenticatedTestClient(app,base_url='http://127.0.0.1:8765',client=('127.0.0.1',12345)) as client:
            document=client.get('/api/v1/natural/settings').json()
            assert client.patch('/api/v1/natural/settings/personality',json={'revision':document['revision'],
                'changes':{'profile':'classic_butler','honorific':'meneer','honorific_frequency':'occasionally'}}).status_code==200
            for count in args.turns:
                cid=None;records=[];before_plans=router.planning_calls
                for index in range(count):
                    message=STORY[index] if index<len(STORY) else (
                        'Welke naam en kleuren had mijn schilderproject aan het begin van ons gesprek?'
                        if index==count-1 else f'Ik denk verder over kleur en gitaarmuziek, gedachte {index+1}.')
                    start=time.perf_counter();cpu=time.process_time();first=None;text='';status='error'
                    with client.stream('POST','/api/v1/chat/stream',json={'message':message,'provider':'ollama',
                        **({'conversation_id':cid} if cid else {})}) as response:
                        response.raise_for_status()
                        for line in response.iter_lines():
                            if not line.startswith('data: '):continue
                            event=json.loads(line[6:])
                            if event['type']=='meta':cid=event['conversation_id']
                            if event['type']=='delta':
                                if first is None:first=time.perf_counter()-start
                                text+=event['text']
                            if event['type']=='done':status=event['status']
                    elapsed=time.perf_counter()-start
                    record={'turn':index+1,'user':message,'assistant':text,'status':status,
                        'http_total_seconds':elapsed,'buffered_http_first_delta_seconds':first,
                        'harness_cpu_one_core_percent':(time.process_time()-cpu)/elapsed*100}
                    records.append(record)
                    print(json.dumps({'scenario_turns':count,'turn':index+1,'status':status,'seconds':round(elapsed,3)}),flush=True)
                principal=app.state.security.store.authenticate(client.cookies.get('jarvis_access'))
                with app.state.natural.store.transaction(principal) as (db,user):
                    timing=[dict(row) for row in db.execute('SELECT event,metric FROM natural_diagnostics WHERE user_id=? AND event IN (?,?) ORDER BY id DESC LIMIT ?',
                        (user,'ai_first_token_ms','response_total_ms',count*2))]
                reports.append({'turns':count,'records':records,'server_timing_events':timing,
                    'median_http_seconds':statistics.median(r['http_total_seconds'] for r in records),
                    'planner_calls':router.planning_calls-before_plans,'jobs':len(app.state.automation.store.items()),
                    'opening_topic_in_final_context':'Koperlicht' in str(router.contexts[-1]),
                    'model_recalled_opening_topic':'koperlicht' in records[-1]['assistant'].casefold(),
                    'exact_duplicate_answers':len(records)-len({r['assistant'] for r in records}),
                    'answers_ending_in_question':sum(r['assistant'].rstrip().endswith('?') for r in records),
                    'resources':app.state.natural.diagnostics.resources(),
                    'context_characters':sum(len(m['content']) for m in router.contexts[-1])})
    result={'model':'qwen2.5:3b','local_only':True,'microphone_used':False,'tts_used':False,
        'human_acceptance':False,'http_client_buffers_sse':True,'reports':reports}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if all(r['status']=='completed' for report in reports for r in report['records']) else 1


if __name__=='__main__':raise SystemExit(main())
