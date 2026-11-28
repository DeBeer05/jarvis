"""Bounded authenticated realtime channel; partial transcripts never run actions."""
import asyncio
from contextlib import suppress
import ipaddress
import json
from types import SimpleNamespace

from fastapi import APIRouter,WebSocket,WebSocketDisconnect
from pydantic import ValidationError

from server.api.chat import ChatInput
from server.mobile import MAX_AUDIO,Speak,transcribe
from server.security.types import AuthError,digest
from server.speech_stream import stream as speech_stream

router=APIRouter()


@router.websocket('/api/v1/realtime')
async def realtime(socket:WebSocket):
    app=socket.app;n=app.state.natural;security=app.state.security
    slots=getattr(app.state,'realtime_slots',None)
    if slots is None:slots=app.state.realtime_slots=set()
    principal=None;worker=None;monitor=None;disconnected=False;raw=bytearray();lock=asyncio.Lock();slot=None;claimed=False
    async def send(value):
        async with lock:await socket.send_json(value)
    async def is_disconnected():return disconnected
    async def body():return bytes(raw)
    request=SimpleNamespace(app=app,state=SimpleNamespace(),is_disconnected=is_disconnected,body=body)
    async def authorize(permission):
        if not await asyncio.to_thread(security.store.live,principal):raise AuthError()
        await asyncio.to_thread(n.automation.permissions.check,principal.device_id,permission)
    async def stop_worker():
        nonlocal worker
        if worker and not worker.done():
            worker.cancel();await asyncio.gather(worker,return_exceptions=True)
        worker=None
    async def operate(message):
        try:
            kind=message['type']
            if kind in ('audio.partial','audio.commit'):
                await authorize('chat:write')
                # WAV is supplied by existing capture clients, bounded on append.
                response=await transcribe(request)
                await send({'type':'transcript','final':kind=='audio.commit',**response})
                if kind=='audio.commit':raw.clear()
            elif kind=='chat':
                await authorize('chat:write')
                value=ChatInput.model_validate(message['input'])
                run=await app.state.chat.prepare(value.message,value.provider,str(value.conversation_id) if value.conversation_id else None,str(value.request_id) if value.request_id else None,principal=principal,channel=value.channel,session_epoch=value.session_epoch)
                async for event in app.state.chat.events(run):await send(event)
            elif kind=='speak':
                await authorize('chat:read')
                response=await speech_stream(request,Speak.model_validate(message['input']))
                await send({'type':'audio','sample_rate':int(response.headers['X-JARVIS-Audio-Rate']),'format':'pcm_s16le'})
                async for chunk in response.body_iterator:
                    async with lock:await socket.send_bytes(chunk)
                await send({'type':'audio.done'})
        except (AuthError,ValidationError,ValueError) as error:
            await send({'type':'error','code':error.code if isinstance(error,AuthError) else 'invalid_parameters','message':error.message if isinstance(error,AuthError) else 'Controleer uw spraakverzoek.'})
        except asyncio.CancelledError:raise
        except Exception:await send({'type':'error','code':'unavailable','message':'Deze verwerking is tijdelijk niet beschikbaar.'})
    try:
        address=socket.client.host if socket.client else ''
        if not socket.scope.get('jarvis.trusted_https') and not ipaddress.ip_address(address).is_loopback:raise AuthError(status=403)
        origin=socket.headers.get('origin')
        if origin and origin not in app.state.settings.allowed_origins:raise AuthError(status=403)
        if socket.scope.get('query_string') or len(slots)>=16:raise AuthError(status=403)
        await asyncio.to_thread(security.store.rate,'websocket-open:'+digest(address),30)
        token=socket.headers.get('authorization','').removeprefix('Bearer ')
        await socket.accept()
        if not token:
            authentication=await asyncio.wait_for(socket.receive_text(),5)
            if len(authentication)>2048:raise AuthError()
            first=json.loads(authentication)
            if set(first)!={'type','access_token'} or first['type']!='authenticate':raise AuthError()
            token=first['access_token']
        if not isinstance(token,str) or not 32<=len(token)<=128:raise AuthError()
        principal=await asyncio.to_thread(security.store.authenticate,token)
        slot=(principal.session_id,principal.device_id)
        if slot in slots:raise AuthError('busy','Er is al een realtimeverbinding voor dit apparaat.',409)
        slots.add(slot);claimed=True;request.state.principal=principal
        await authorize('chat:read')
        async def watch():
            while True:
                await asyncio.sleep(2)
                if not await asyncio.to_thread(security.store.live,principal):
                    await stop_worker();await socket.close(4401);return
        monitor=asyncio.create_task(watch())
        await send({'type':'ready','version':1,'audio_format':'wav_pcm16_16khz','maximum_audio_bytes':MAX_AUDIO,'partial_transcripts_execute_actions':False})
        while True:
            event=await asyncio.wait_for(socket.receive(),120)
            if event['type']=='websocket.disconnect':break
            if event.get('bytes') is not None:
                await authorize('chat:write')
                fragment=event['bytes']
                if len(fragment)>65536 or len(raw)+len(fragment)>MAX_AUDIO:raise AuthError('audio_too_large','De opname is te groot.',413)
                if worker and not worker.done():raise AuthError('busy','Wacht op de lopende spraakverwerking.',409)
                raw.extend(fragment);continue
            text=event.get('text','')
            if len(text)>20000:raise ValueError()
            message=json.loads(text)
            if not isinstance(message,dict):raise ValueError()
            kind=message.get('type')
            await authorize('chat:read')
            if kind=='ping':await send({'type':'pong'})
            elif kind=='cancel':
                await stop_worker();raw.clear();await send({'type':'cancelled'})
            elif kind=='audio.start':
                await authorize('chat:write');await stop_worker();raw.clear();await send({'type':'audio.ready'})
            elif kind in ('audio.partial','audio.commit','chat','speak'):
                if worker and not worker.done():
                    await send({'type':'error','code':'busy','message':'Er wordt nog een opdracht verwerkt.'});continue
                await asyncio.to_thread(security.store.rate,'websocket-operation:'+principal.device_id,90)
                worker=asyncio.create_task(operate(message))
            else:await send({'type':'error','code':'invalid_parameters','message':'Onbekend realtimeverzoek.'})
    except (AuthError,ValueError,TypeError,KeyError,TimeoutError,WebSocketDisconnect,RuntimeError):
        with suppress(RuntimeError,WebSocketDisconnect):await socket.close(4401)
    finally:
        disconnected=True;raw.clear()
        if claimed:slots.discard(slot)
        if monitor:monitor.cancel()
        await stop_worker()
        if monitor:await asyncio.gather(monitor,return_exceptions=True)
