"""Private streaming PCM. Revocation/cancel closes the upstream generator."""
import asyncio
from contextlib import aclosing,suppress
from copy import deepcopy
import time

from fastapi import APIRouter,Depends,Request
from fastapi.responses import StreamingResponse

from providers.speech_format import format_speech
from server.api.routes import require_client_access
from server.mobile import Speak
from server.security.gate import require_permission
from server.security.types import AuthError

router=APIRouter(prefix='/api/v1/mobile',dependencies=[Depends(require_client_access)])


async def guarded(request,source):
    n=request.app.state.natural;principal=request.state.principal
    epoch=await asyncio.to_thread(lambda:n.automation.safety.state(principal.device_id)['epoch'])
    async def watch():
        while True:
            if await request.is_disconnected() or not await asyncio.to_thread(n.security.store.live,principal):return
            try:await asyncio.to_thread(n.automation.permissions.check,principal.device_id,'chat:read')
            except AuthError:return
            if await asyncio.to_thread(lambda:n.automation.safety.state(principal.device_id)['epoch'])!=epoch:return
            await asyncio.sleep(.15)
    monitor=asyncio.create_task(watch());pending=None
    try:
        while True:
            pending=asyncio.create_task(anext(source))
            done,_=await asyncio.wait((pending,monitor),return_when=asyncio.FIRST_COMPLETED)
            if monitor in done:raise AuthError('speech_cancelled','De audio is gestopt.',499)
            try:yield pending.result()
            except StopAsyncIteration:return
    finally:
        monitor.cancel()
        if pending and not pending.done():pending.cancel()
        await asyncio.gather(*(task for task in (monitor,pending) if task),return_exceptions=True)
        await source.aclose()


@router.post('/speech/stream',dependencies=[Depends(require_permission('chat:read'))])
async def stream(request:Request,body:Speak):
    started=time.perf_counter();n=request.app.state.natural;principal=request.state.principal
    await asyncio.to_thread(n.security.store.rate,'mobile-tts:'+principal.device_id,60)
    config=deepcopy((await asyncio.to_thread(n.settings.runtime,principal))['settings'])
    if body.conversation_id:
        await asyncio.to_thread(n.authorize_conversation,principal,body.conversation_id)
        config=n.responses.apply(principal,body.conversation_id,config)
    if config.get('presence',{}).get('mode')=='private':config['voice']['mode']='offline'
    if body.speed is not None:config['voice']['speed']=body.speed
    text=format_speech(body.text,config['general']['timezone'])
    source=guarded(request,n.tts.stream_pcm(request,text,config,body.utterance_id))
    try:rate,first=await asyncio.wait_for(anext(source),30)
    except BaseException:
        await source.aclose();raise
    await asyncio.to_thread(n.diagnostics.record,principal,'tts_first_chunk_ms',(time.perf_counter()-started)*1000)
    async def chunks():
        size=len(first)
        try:
            yield first
            async with aclosing(source):
                async for current,pcm in source:
                    size+=len(pcm)
                    if current!=rate or size>5_760_000:raise AuthError('speech_unavailable','De audiolimiet is bereikt.',503)
                    yield pcm
        finally:
            await source.aclose()
            with suppress(AuthError):await asyncio.to_thread(n.diagnostics.record,principal,'tts_ms',(time.perf_counter()-started)*1000)
    return StreamingResponse(chunks(),media_type='audio/pcm',headers={'X-JARVIS-Audio-Rate':str(rate),'Cache-Control':'no-store','X-Accel-Buffering':'no'})
