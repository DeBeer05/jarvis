"""Explicit local CPU decoder comparison; synthetic WAV only, no microphone or downloads."""
import argparse
import json
import os
from pathlib import Path
import re
import statistics
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from providers.voice_pipe import OwnedVoicePipe

TEXTS=[
 'Zet de afspraak op vrijdag om half vier.',
 'Nee, toch liever donderdag om kwart over twee.',
 'Mijn schilderproject heet Koperlicht en ik gebruik koper en blauw.',
 'Ik heb vandaag een lange dag gehad en wil rustig praten.',
 'Stuur niets, ik wil alleen een concept bekijken.',
 'Hoeveel is zeven plus vijf?',
 'De deadline is op zevenentwintig november.',
 'Nee, annuleer dat voorstel.',
]


def normalized(text):
    numbers=dict(zip('nul een twee drie vier vijf zes zeven acht negen tien elf twaalf dertien veertien vijftien zestien zeventien achttien negentien twintig'.split(),map(str,range(21))))
    numbers['zevenentwintig']='27'
    return [numbers.get(word,word) for word in re.findall(r'\w+',text.casefold())]


def distance(left,right):
    previous=list(range(len(right)+1))
    for i,a in enumerate(left,1):
        current=[i]
        for j,b in enumerate(right,1):current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(a!=b)))
        previous=current
    return previous[-1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-local',action='store_true')
    parser.add_argument('--rounds',type=int,default=2,choices=range(1,5))
    parser.add_argument('--candidate',choices=('greedy','text-only'),default='text-only')
    parser.add_argument('--output',type=Path,default=ROOT/'.local/voice-latency/stt.json')
    args=parser.parse_args()
    if not args.run_local:parser.error('--run-local required; no inference started')
    models=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.local/share')))/'JARVIS/Desktop/models'
    worker=OwnedVoicePipe([str(ROOT/'.local/voice-venv/Scripts/python.exe'),str(ROOT/'desktop-client/voice_worker.py')])
    def request(operation,**values):
        result=worker.exchange({'operation':operation,'models':str(models),'device':'cpu','model':'whisper-small','profile':'desktop',**values},timeout=100)
        if not result.get('ok'):raise RuntimeError('Synthetic benchmark failed: '+result.get('code','unknown'))
        return result['result']
    records=[]
    try:
        clips=[request('tts',provider='piper',voice='ronnie',text=text)['audio'] for text in TEXTS]
        cold=request('stt',audio=clips[0],beam_size=3)
        for round_index in range(args.rounds):
            for index,clip in enumerate(clips):
                for mode in (('baseline','candidate') if (round_index+index)%2==0 else ('candidate','baseline')):
                    beam=1 if mode=='candidate' and args.candidate=='greedy' else 3
                    started=time.perf_counter();result=request('stt',audio=clip,beam_size=beam,without_timestamps=mode=='candidate' and args.candidate=='text-only')
                    expected=normalized(TEXTS[index]);actual=normalized(result['text'])
                    record={'round':round_index,'clip':index,'beam':beam,'mode':mode,'seconds':result['seconds'],
                        'wall_seconds':time.perf_counter()-started,'text':result['text'],
                        'word_errors':distance(expected,actual),'reference_words':len(expected),'runtime':result.get('runtime_stats',{})}
                    records.append(record);print(json.dumps({key:record[key] for key in ('round','clip','beam','mode','seconds','word_errors')}),flush=True)
        summary={mode:{'median_seconds':statistics.median(r['seconds'] for r in records if r['mode']==mode),
            'word_errors':sum(r['word_errors'] for r in records if r['mode']==mode),
            'reference_words':sum(r['reference_words'] for r in records if r['mode']==mode),
            'peak_ram_bytes':max(r['runtime'].get('peak_ram_bytes',0) for r in records if r['mode']==mode)} for mode in ('baseline','candidate')}
        report={'synthetic_cpu_only':True,'human_accuracy_tested':False,'microphone_used':False,'cold_stt_seconds':cold['seconds'],
            'candidate':args.candidate,'texts':TEXTS,'summary':summary,'records':records}
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    finally:
        worker.cancel();deadline=time.monotonic()+8
        while worker.busy and time.monotonic()<deadline:time.sleep(.05)


if __name__=='__main__':main()
