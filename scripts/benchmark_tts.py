"""Explicit synthetic TTS comparison; saves no real conversation or microphone audio."""
import base64
import io
import json
import os
from pathlib import Path
import statistics
import sys
import time
import wave
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from providers.voice_pipe import OwnedVoicePipe

TEXTS=["Goedemorgen, meneer. Uw agenda is bijgewerkt en u heeft twee belangrijke berichten ontvangen.","Ik heb uw afspraak verplaatst naar vrijdagmiddag. Alles is geregeld.","Met alle respect, meneer, ik denk dat er een efficiëntere oplossing bestaat.","Er is een urgente melding binnengekomen die uw aandacht vereist.","Uw planning voor vandaag is bijgewerkt. U heeft vanmiddag voldoende vrije tijd.","Uw server beschikt over acht gigabyte werkgeheugen. Ik raad daarom een lichtgewicht model aan."]


def main():
    root=Path(__file__).resolve().parents[1];output=root/'.local/tts-benchmark';output.mkdir(parents=True,exist_ok=True)
    models=Path(os.environ['LOCALAPPDATA'])/'JARVIS/Desktop/models';records=[]
    for provider,voices in [('supertonic',['M1','M2','M3','M4','M5']),('piper',['ronnie','mls'])]:
        worker=OwnedVoicePipe([str(root/'.local/voice-venv/Scripts/python.exe'),str(root/'desktop-client/voice_worker.py')]);previous_cpu=0.
        try:
            for voice in voices:
                for index,text in enumerate(TEXTS):
                    before=time.perf_counter()
                    request={'operation':'tts','models':str(models),'provider':provider,'voice':voice if provider=='piper' else 'ronnie','supertonic_voice':voice,'speed':.95,'steps':8,'pause_ms':180}
                    response=worker.exchange({**request,'text':text},timeout=100)
                    elapsed=time.perf_counter()-before
                    if not response.get('ok'):raise RuntimeError(response.get('code','unknown'))
                    result=response['result'];audio=base64.b64decode(result['audio'])
                    with wave.open(io.BytesIO(audio),'rb') as wav:duration=wav.getnframes()/wav.getframerate()
                    stats=result.get('runtime_stats',{});cpu=stats.get('cpu_seconds',0);delta=max(0,cpu-previous_cpu);previous_cpu=cpu
                    record={'provider':provider,'voice':voice,'text_index':index,'audio_seconds':duration,'time_to_first_audio_seconds':elapsed,'generation_seconds':result['seconds'],'rtf':elapsed/duration,'cpu_one_core_percent':delta/elapsed*100,'ram_bytes':stats.get('ram_bytes'),'peak_ram_bytes':stats.get('peak_ram_bytes'),'device':'cpu','gpu_inference':False}
                    records.append(record);print(json.dumps(record),flush=True)
                    (output/(provider+'-'+voice+'-'+str(index)+'.wav')).write_bytes(audio)
        finally:
            worker.cancel()
            deadline=time.monotonic()+8
            while worker.busy and time.monotonic()<deadline:time.sleep(.05)
    report={'records':records,'subjective_listening_tested':False,'audio_played':False,'microphone_used':False,'hardware':'Ryzen 7 5700X desktop; no mini-PC measurement','first_audio_is_complete_sentence_buffer':True,'median_warm_seconds':{provider:statistics.median(r['time_to_first_audio_seconds'] for r in records if r['provider']==provider and r['text_index']>0) for provider in ('supertonic','piper')}}
    (output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


if __name__=='__main__':main()
