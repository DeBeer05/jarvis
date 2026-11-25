"""Synthetic local STT -> real Ollama -> first sentence PCM and helper cancellation.
No microphone, playback, user database, external account or model downloads.
Run from the server development environment with the existing voice helper installed.
"""
import asyncio,base64,json,sys,tempfile,time,threading
from pathlib import Path
from dataclasses import replace
root=Path(__file__).resolve().parents[1];sys.path[:0]=[str(root),str(root/'desktop-client')]
from scripts.benchmark_conversation import LocalRouter
from server.config import load_settings
from server.app import create_app
from tests.auth_helpers import AuthenticatedTestClient
from jarvis_client.voice.worker import InferenceWorker
from jarvis_client.voice.settings import VoiceSettings

worker=InferenceWorker();voice=VoiceSettings();results=[]
try:
 input_audio,_=worker.synthesize('Ik heb vandaag een drukke dag gehad.',voice,lambda:True)
 with tempfile.TemporaryDirectory(prefix='jarvis-audio-probe-') as temporary:
  settings=replace(load_settings(root=Path(temporary),environ={}),ai_provider='ollama',preferred_provider='ollama',ollama_model='qwen2.5:3b',automations_enabled=False,provider_timeout_seconds=60)
  app=create_app(settings,ai_router=LocalRouter(settings))
  with AuthenticatedTestClient(app,base_url='http://127.0.0.1:8765',client=('127.0.0.1',12345)) as c:
   principal=app.state.security.store.authenticate(c.cookies.get('jarvis_access'))
   async def probe(provider):
    started=time.perf_counter()
    stt=await asyncio.to_thread(worker.transcribe,input_audio,voice,lambda:True)
    transcribed=time.perf_counter()
    run=await app.state.chat.prepare(stt['text'],'ollama',principal=principal,channel='voice')
    first=None;stats=None;generation=None
    async for event in app.state.chat.events(run):
     if event['type']=='speech' and first is None:
      result=await asyncio.to_thread(worker.request,'tts',replace(voice,provider=provider),text=event['text'],supertonic_voice='M3',steps=8,pause_ms=180)
      assert base64.b64decode(result['audio'])[:4]==b'RIFF'
      first=time.perf_counter()-started;stats=result.get('runtime_stats');generation=result['seconds']
    return {'provider':provider,'synthetic_end_pcm_to_first_sentence_pcm_seconds':first,'stt_wall_seconds':transcribed-started,'stt_inference_seconds':stt['seconds'],'ai_first_token_seconds':run.first_token_seconds,'tts_first_sentence_seconds':generation,'total_text_seconds':time.perf_counter()-started,'helper_stats':stats}
   for provider in ('piper','supertonic'):
    record=c.portal.call(probe,provider);results.append(record);print(json.dumps(record),flush=True)
 # Cancel an actual outstanding request of our own warm private helper.
 stopped=[]
 def long_request():
  try:worker.request('tts',replace(voice,provider='supertonic'),text='Dit is een lange synthetische annuleringsproef. '*10,supertonic_voice='M3',steps=8)
  except RuntimeError as error:stopped.append('geannuleerd' in str(error))
 thread=threading.Thread(target=long_request);thread.start()
 assert worker.inflight.wait(5);time.sleep(.15);assert thread.is_alive()
 started=time.perf_counter();worker.cancel();thread.join(5)
 cancellation=time.perf_counter()-started
 assert stopped==[True] and not thread.is_alive()
 audio,_=worker.synthesize('Een verse aanvraag werkt.',voice,lambda:True);assert audio[:4]==b'RIFF'
 report={'records':results,'private_request_cancel_seconds':cancellation,'fresh_request_after_cancel':True,'physical_audio_tested':False,'audio_played':False,'user_db_used':False}
 (root/'.local/experience-benchmark/audio-chain.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
finally:
 worker.cancel()
 deadline=time.monotonic()+8
 while worker.busy and time.monotonic()<deadline:time.sleep(.05)
