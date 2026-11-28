"""Voice adapter to the existing server helper, with cancellable pooled HTTP."""
import asyncio
import concurrent.futures
import json
import threading
import time
from typing import Any

import httpx

from jarvis_client.api import ClientError


class ServerInferenceWorker:
    def __init__(self,api,*,client_factory=httpx.AsyncClient,prefer_local_stt=False,local_factory=None,local_only=False):
        self.api=api;self.client_factory=client_factory;self.loop=None;self.thread=None;self.client=None
        self.centralized=True
        self.pcm_stream=False;self.stream_futures=set()
        from jarvis_client.voice.realtime import RealtimeSpeech
        self.realtime=RealtimeSpeech(api)
        self.warming=False
        self.prefer_local_stt=prefer_local_stt;self.local_stt=None;self.local_factory=local_factory;self.local_retry=0.
        self.local_only=local_only
        self.utterance_id=None;self.conversation_id=None
        self.lock=threading.RLock();self.serial=threading.Lock();self.future=None;self.closing=False;self.cleanup_threads=[]

    @property
    def busy(self):
        with self.lock:return bool(self.future and not self.future.done()) or any(thread.is_alive() for thread in self.cleanup_threads)

    def _start(self):
        with self.lock:
            if self.closing:raise RuntimeError("Spraakverbinding afgesloten.")
            if self.loop:return
            loop=self.loop=asyncio.new_event_loop();ready=threading.Event()
            def run():
                asyncio.set_event_loop(loop);ready.set()
                loop.run_forever();loop.close()
            self.thread=threading.Thread(target=run,name="jarvis-voice-http",daemon=True);self.thread.start();ready.wait(2)

    async def _ensure_client(self):
        if self.client is None:
            self.client=self.client_factory(base_url=self.api.origin,verify=True,trust_env=False,follow_redirects=False,
                timeout=httpx.Timeout(110,connect=4),limits=httpx.Limits(max_connections=2,max_keepalive_connections=2,keepalive_expiry=3))

    async def _request(self,path,*,body=None,audio=None,method='POST'):
        if path=='/api/v1/mobile/speech/transcribe' and self.pcm_stream:
            try:return await self.realtime.transcribe(audio)
            except asyncio.CancelledError:raise
            except Exception:
                # Recognition is read-only. Fall back once to the existing HTTP
                # route; never replay a chat action after an ambiguous failure.
                pass
        headers=await asyncio.to_thread(self.api.headers)
        await self._ensure_client()
        limit=8_000_000 if audio is None else 64000
        kwargs={"json":body} if body is not None else {"content":audio}
        if audio is not None:headers={**headers,"Content-Type":"audio/wav"}
        active_client:Any=self.client
        if active_client is None:raise RuntimeError('Spraakverbinding is afgesloten.')
        try:
            async with active_client.stream(method,path,headers=headers,**kwargs) as response:
                data=bytearray()
                async for part in response.aiter_bytes():
                    if len(data)+len(part)>limit:raise ClientError("invalid_response","Het spraakantwoord is te groot.")
                    data.extend(part)
                if not response.is_success:
                    decoded=httpx.Response(response.status_code,headers=response.headers,content=bytes(data))
                    if response.status_code==401:await asyncio.to_thread(self.api.forget)
                    self.api._decode(decoded)
                return bytes(data)
        except asyncio.CancelledError:
            # Some transports retain a connection awaiting response headers after
            # cancellation. Close this voice-only pool, never the chat connection.
            if self.client is active_client:self.client=None
            await active_client.aclose()
            raise
        except httpx.TransportError:
            raise ClientError("speech_unavailable","De spraakverbinding met de server is onderbroken.") from None

    def request(self,path,*,body=None,audio=None,valid=lambda:True,method='POST'):
        if not valid():raise RuntimeError("Spraakopdracht geannuleerd.")
        self._start()
        loop=self.loop
        if loop is None:raise RuntimeError("Spraakverbinding niet gestart.")
        with self.serial:
            if not valid():raise RuntimeError("Spraakopdracht geannuleerd.")
            with self.lock:
                if self.closing:raise RuntimeError("Spraakverbinding afgesloten.")
                async def bounded():
                    async with asyncio.timeout(120):return await self._request(path,body=body,audio=audio,method=method)
                future=self.future=asyncio.run_coroutine_threadsafe(bounded(),loop)
            try:
                while True:
                    if not valid():future.cancel();raise RuntimeError("Spraakopdracht geannuleerd.")
                    try:
                        value=future.result(timeout=.05)
                        if not valid():raise RuntimeError("Spraakopdracht geannuleerd.")
                        return value
                    except concurrent.futures.TimeoutError:
                        if future.done():raise ClientError("speech_timeout","Spraakverwerking duurde te lang.") from None
                        continue
                    except concurrent.futures.CancelledError:raise RuntimeError("Spraakopdracht geannuleerd.") from None
            finally:
                if not future.done():future.cancel()
                with self.lock:
                    if self.future is future:self.future=None

    def transcribe(self,audio,settings,valid):
        if not 0<len(audio)<=2_000_000:raise ValueError("Ongeldige of te grote opname.")
        if self.prefer_local_stt and time.monotonic()>=self.local_retry:
            from jarvis_client.voice.settings import installed_stt_models
            if self.local_factory or settings.model in installed_stt_models(settings):
                try:
                    if self.local_stt is None:
                        from jarvis_client.voice.worker import InferenceWorker
                        self.local_stt=(self.local_factory or InferenceWorker)()
                    return {**self.local_stt.transcribe(audio,settings,valid),'location':'windows_local'}
                except Exception:
                    if not valid():raise RuntimeError('Spraakopdracht geannuleerd.') from None
                    self.local_retry=time.monotonic()+60
        if self.local_only:raise RuntimeError('De gekozen lokale spraakruntime is niet beschikbaar. Er is geen microfoonaudio geüpload.')
        raw=self.request("/api/v1/mobile/speech/transcribe",audio=audio,valid=valid)
        try:
            result=json.loads(raw)
            if not isinstance(result.get("text"),str) or len(result["text"])>8000:raise ValueError()
            return {**result,"device":"server"}
        except (ValueError,TypeError,AttributeError):raise ClientError("invalid_response","Ongeldige spraakherkenning ontvangen.") from None

    def begin_utterance(self,identifier,conversation):
        self.utterance_id=identifier;self.conversation_id=conversation

    def progress_audio(self,clip,valid):
        from jarvis_client.voice.progress import cached
        return cached(clip,self.api.origin,lambda:self.request('/api/v1/natural/progress-audio/'+clip.identifier,method='GET',valid=valid))

    def warm_progress(self,valid):
        with self.lock:
            if self.warming or self.closing:return
            self.warming=True
        def warm():
            try:
                from jarvis_client.voice.progress import ProgressClip
                manifest=json.loads(self.request('/api/v1/natural/progress-audio',method='GET',valid=valid))
                for item in manifest.get('items',[])[:100]:
                    if not valid() or self.closing:return
                    clip=ProgressClip.parse({'audio_id':item['id'],'voice_key':manifest['version'],'sha256':item['sha256'],'text':item['text']})
                    self.progress_audio(clip,valid)
            except Exception:pass  # Optional generic audio never blocks real speech.
            finally:
                with self.lock:self.warming=False
        threading.Thread(target=warm,name='jarvis-progress-cache',daemon=True).start()

    def synthesize(self,text,settings,valid):
        if not 1<=len(text)<=700:raise ValueError("Ongeldige lengte voor spraak.")
        if self.pcm_stream:
            from jarvis_client.voice.streaming import StreamedAudio
            return StreamedAudio(self,text,settings),{'device':'server','streaming':True}
        start=time.perf_counter()
        data=self.request("/api/v1/mobile/speech/synthesize",body={"text":text,**({"speed":settings.speed} if not self.utterance_id else {}),**({"utterance_id":self.utterance_id} if self.utterance_id else {}),**({"conversation_id":self.conversation_id} if self.conversation_id else {})},valid=valid)
        return data,{"seconds":time.perf_counter()-start,"device":"server"}

    def cancel(self):
        self.cancel_pending()
        if self.local_stt:self.local_stt.cancel()

    def cancel_pending(self):
        with self.lock:
            if self.future:self.future.cancel()
            for future in tuple(self.stream_futures):future.cancel()
        if self.local_stt:self.local_stt.cancel_pending()

    def close(self):
        with self.lock:
            if self.closing:return
            self.closing=True;self.cancel();loop=self.loop
        if loop and not loop.is_closed():
            async def finish():
                await self.realtime.close()
                if self.client:await self.client.aclose()
                pending=[task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
                for task in pending:task.cancel()
                if pending:await asyncio.gather(*pending,return_exceptions=True)
            def cleanup():
                try:asyncio.run_coroutine_threadsafe(finish(),loop).result(timeout=5)
                finally:loop.call_soon_threadsafe(loop.stop)
                if self.thread:self.thread.join(2)
            thread=threading.Thread(target=cleanup,daemon=True);self.cleanup_threads.append(thread);thread.start()
