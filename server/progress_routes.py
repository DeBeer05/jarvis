"""Authenticated progress audio preparation and downloads; no public cache."""
import asyncio
import json

from fastapi import APIRouter,Depends,Request
from fastapi.responses import Response,StreamingResponse
from pydantic import Field

from server.natural.models import StrictModel
from server.security.gate import require_permission
from server.security.types import AuthError

router=APIRouter(prefix='/api/v1/natural/progress-audio')


@router.get('')
async def manifest(request:Request):
    n=request.app.state.natural;principal=request.state.principal
    config=(await asyncio.to_thread(n.settings.runtime,principal))['settings']
    return await asyncio.to_thread(n.progress_audio.manifest,principal,config)


@router.get('/{identifier}')
async def audio(request:Request,identifier:str):
    n=request.app.state.natural;principal=request.state.principal
    config=(await asyncio.to_thread(n.settings.runtime,principal))['settings']
    raw=await asyncio.to_thread(n.progress_audio.read,principal,config,identifier)
    return Response(raw,media_type='audio/wav',headers={'Cache-Control':'private, no-store'})


class Prepare(StrictModel):
    one_time_credits:int=Field(default=0,ge=0,le=3000)


@router.post('/prepare',dependencies=[Depends(require_permission('chat:write'))])
async def prepare(request:Request,body:Prepare):
    await asyncio.to_thread(request.app.state.security.store.rate,'progress-prepare:'+request.state.principal.device_id,2)
    async def stream():
        try:
            async for item in request.app.state.natural.progress_audio.prepare(request,one_time_credits=body.one_time_credits):
                yield json.dumps(item)+'\n'
            yield json.dumps({'status':'completed'})+'\n'
        except AuthError as error:yield json.dumps({'status':'blocked','code':error.code,'message':error.message})+'\n'
    return StreamingResponse(stream(),media_type='application/x-ndjson',headers={'Cache-Control':'no-store','X-Accel-Buffering':'no'})
