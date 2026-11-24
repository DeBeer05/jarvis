"""Voice adapter to the existing server helper, with cancellable pooled HTTP."""
import asyncio
import concurrent.futures
import json
import threading
import time

import httpx

from jarvis_client.api import ClientError


class ServerInferenceWorker:
    def __init__(self,api,*,client_factory=httpx.AsyncClient):
        self.api=api;self.client_factory=client_factory;self.loop=None;self.thread=None;self.client=None
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

    async def _request(self,path,*,body=None,audio=None):
        headers=await asyncio.to_thread(self.api.headers)
        if self.client is None:
            self.client=self.client_factory(base_url=self.api.origin,verify=True,trust_env=False,follow_redirects=False,
                timeout=httpx.Timeout(110,connect=4),limits=httpx.Limits(max_connections=2,max_keepalive_connections=2,keepalive_expiry=3))
        limit=8_000_000 if audio is None else 64000
        kwargs={"json":body} if body is not None else {"content":audio}
        if audio is not None:headers={**headers,"Content-Type":"audio/wav"}
        active_client=self.client
        try:
            async with active_client.stream("POST",path,headers=headers,**kwargs) as response:
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

    def request(self,path,*,body=None,audio=None,valid=lambda:True):
        if not valid():raise RuntimeError("Spraakopdracht geannuleerd.")
        self._start()
        loop=self.loop
        if loop is None:raise RuntimeError("Spraakverbinding niet gestart.")
        with self.serial:
            if not valid():raise RuntimeError("Spraakopdracht geannuleerd.")
            with self.lock:
                if self.closing:raise RuntimeError("Spraakverbinding afgesloten.")
                async def bounded():
                    async with asyncio.timeout(120):return await self._request(path,body=body,audio=audio)
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
        raw=self.request("/api/v1/mobile/speech/transcribe",audio=audio,valid=valid)
        try:
            result=json.loads(raw)
            if not isinstance(result.get("text"),str) or len(result["text"])>8000:raise ValueError()
            return {**result,"device":"server"}
        except (ValueError,TypeError,AttributeError):raise ClientError("invalid_response","Ongeldige spraakherkenning ontvangen.") from None

    def synthesize(self,text,settings,valid):
        if not 1<=len(text)<=700:raise ValueError("Ongeldige lengte voor spraak.")
        start=time.perf_counter()
        data=self.request("/api/v1/mobile/speech/synthesize",body={"text":text,"speed":settings.speed},valid=valid)
        return data,{"seconds":time.perf_counter()-start,"device":"server"}

    def cancel(self):
        with self.lock:
            if self.future:self.future.cancel()

    cancel_pending=cancel

    def close(self):
        with self.lock:
            if self.closing:return
            self.closing=True;self.cancel();loop=self.loop
        if loop and not loop.is_closed():
            async def finish():
                if self.client:await self.client.aclose()
                pending=[task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
                for task in pending:task.cancel()
                if pending:await asyncio.gather(*pending,return_exceptions=True)
            def cleanup():
                try:asyncio.run_coroutine_threadsafe(finish(),loop).result(timeout=5)
                finally:loop.call_soon_threadsafe(loop.stop)
                if self.thread:self.thread.join(2)
            thread=threading.Thread(target=cleanup,daemon=True);self.cleanup_threads.append(thread);thread.start()
