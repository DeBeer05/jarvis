"""Lazy bounded PCM stream; network and playback remain outside the Qt thread."""
import asyncio
import concurrent.futures
from dataclasses import dataclass
import queue
from typing import Any

from jarvis_client.api import ClientError


@dataclass
class StreamedAudio:
    worker:Any
    text:str
    settings:Any

    def play(self,output,settings,valid,on_started):
        worker=self.worker;worker._start();packets=queue.Queue(maxsize=3)
        async def put(value):
            while valid():
                try:packets.put_nowait(value);return
                except queue.Full:await asyncio.sleep(.01)
            raise asyncio.CancelledError
        async def produce():
            try:
                headers=await asyncio.to_thread(worker.api.headers)
                # Reuse the same bounded voice HTTP pool.
                if worker.client is None:
                    await worker._ensure_client()
                body={'text':self.text}
                if worker.utterance_id:body['utterance_id']=worker.utterance_id
                else:body['speed']=settings.speed
                if worker.conversation_id:body['conversation_id']=worker.conversation_id
                async with worker.client.stream('POST','/api/v1/mobile/speech/stream',headers=headers,json=body) as response:
                    if response.status_code!=200:
                        await response.aread();worker.api._decode(response)
                    rate=int(response.headers.get('X-JARVIS-Audio-Rate','0'))
                    if not 8000<=rate<=48000:raise ValueError('Ongeldige samplerate')
                    await put(('rate',rate));total=0
                    async for part in response.aiter_bytes(chunk_size=1920):
                        total+=len(part)
                        if total>5_760_000:raise ValueError('Audiolimiet bereikt')
                        if part:await put(('pcm',part))
                await put(('done',None))
            except asyncio.CancelledError:raise
            except Exception as error:await put(('error',error))
        future=asyncio.run_coroutine_threadsafe(produce(),worker.loop)
        with worker.lock:worker.stream_futures.add(future)
        def receive():
            while valid():
                try:return packets.get(timeout=.05)
                except queue.Empty:
                    if future.done():
                        try:future.result()
                        except concurrent.futures.CancelledError:return 'done',None
                        raise ClientError('speech_unavailable','De audiostream is onderbroken.')
            return 'done',None
        def chunks():
            while valid():
                kind,value=receive()
                if kind=='done':return
                if kind=='error':raise value
                if kind!='pcm':raise ValueError('Ongeldige audiostream')
                yield value
        try:
            kind,rate=receive()
            if kind=='error':raise rate
            if kind=='done':return
            if kind!='rate':raise ValueError('Audioheader ontbreekt')
            output.play_pcm(chunks(),rate,settings,valid,on_started)
        finally:
            future.cancel()
            with worker.lock:worker.stream_futures.discard(future)
