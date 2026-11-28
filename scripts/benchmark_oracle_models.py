"""Real private-VM inference benchmark, exclusively fictional Dutch prompts."""
import argparse
import json
from pathlib import Path
import statistics
import time
import urllib.request

MODELS=('qwen2.5:3b','qwen3.5:4b','qwen3:4b','qwen2.5:7b')
CASES=(
    ('butler','Ik ga nu eten. Wens mij smakelijk eten, in één korte zin.','smakelijk'),
    ('reasoning','Ik vertrek om 14:20. De rit duurt 35 minuten en ik wil 10 minuten eerder aankomen. Mijn afspraak is om 15:00. Ben ik op tijd? Leg kort uit.','14:15'),
    ('context','Mijn fictieve schilderij heet Koperlicht. De kleuren zijn koper en blauw. Hoe heet het en welke kleuren gebruik ik?','koperlicht'),
)


def request(path,body=None):
    data=json.dumps(body).encode() if body is not None else None
    return urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:11434'+path,data=data,headers={'Content-Type':'application/json'}),timeout=900)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--models",nargs="+",default=MODELS);args=parser.parse_args()
    records=[]
    models=args.models
    for model in models:
        with request('/api/pull',{'model':model,'stream':False}) as response:
            if json.load(response).get('status')!='success':raise RuntimeError('Model download not confirmed')
        for case,prompt,expected in CASES:
            started=time.perf_counter();first=None;text='';final={}
            with request('/api/chat',{'model':model,'messages':[{'role':'system','content':'U bent een professionele Nederlandse butler. Spreek met u/uw en meneer. Antwoord kort en nauwkeurig. Geen tools en geen uitvoeringsclaims.'},{'role':'user','content':prompt}],'think':False,'stream':True,'keep_alive':'30m','options':{'num_ctx':2048,'num_predict':96,'num_thread':2,'temperature':0,'seed':42}}) as response:
                for raw in response:
                    row=json.loads(raw);content=row.get('message',{}).get('content','')
                    if content and first is None:first=time.perf_counter()-started
                    text+=content
                    if row.get('done'):final=row
            record={'model':model,'case':case,'cold':case=='butler','first_token_s':first,'total_s':time.perf_counter()-started,'text':text,'expected_marker':expected,'marker_present':expected in text.casefold(),'eval_count':final.get('eval_count'),'eval_duration_ns':final.get('eval_duration'),'prompt_eval_duration_ns':final.get('prompt_eval_duration'),'load_duration_ns':final.get('load_duration')}
            if record['eval_duration_ns']:record['tokens_per_second']=record['eval_count']/(record['eval_duration_ns']/1e9)
            records.append(record)
            Path('/var/lib/jarvis-ai/benchmark.json').write_text(json.dumps({'scope':'real Oracle ARM64 CPU, fictional prompts; no STT/TTS claim','records':records},indent=2),encoding='utf-8')
        with request('/api/generate',{'model':model,'keep_alive':0}) as response:response.read()
    summary={model:{'median_first_token_s':statistics.median(row['first_token_s'] for row in records if row['model']==model),'marker_hits':sum(row['marker_present'] for row in records if row['model']==model)} for model in models}
    print(json.dumps({'summary':summary,'records':records}))


if __name__=='__main__':main()
