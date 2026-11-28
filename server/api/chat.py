import asyncio
import json
from contextlib import suppress
from contextlib import aclosing
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from server.api.routes import require_client_access
from server.chat_store import ChatError
from server.ai.providers import MESSAGES
from server.security.types import AuthError

router = APIRouter(dependencies=[Depends(require_client_access)])
STATIC = Path(__file__).resolve().parents[1] / "static"


class ChatInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=8000)
    provider: Literal["auto", "gemini", "groq", "ollama", "oracle"] | None = None
    conversation_id: UUID | None = None
    request_id: UUID | None = None
    channel: Literal["text","voice"] = "text"
    session_epoch: int | None = Field(default=None,ge=1)


async def prepare(request: Request, body: ChatInput):
    if body.conversation_id and "chat:read" not in request.state.principal.permissions:
        raise AuthError("permission_denied", "Dit apparaat mag geen bestaande gesprekken gebruiken.", 403)
    return await request.app.state.chat.prepare(
        body.message, body.provider,
        str(body.conversation_id) if body.conversation_id else None,
        str(body.request_id) if body.request_id else None,
        principal=request.state.principal,
        channel=body.channel, session_epoch=body.session_epoch,
    )


async def watch_authentication(request, run):
    principal = request.state.principal
    while True:
        if not await asyncio.to_thread(request.app.state.security.store.live, principal):
            run.error = {"code": "authentication_expired", "message": "Je sessie is verlopen of ingetrokken. Log opnieuw in."}
            run.cancel.set()
            return
        await asyncio.sleep(0.5)


@router.post("/api/v1/chat")
async def chat(request: Request, body: ChatInput):
    service = request.app.state.chat
    run = await prepare(request, body)

    async def watch_disconnect():
        while not await request.is_disconnected():
            await asyncio.sleep(0.1)
        run.cancel.set()

    monitor = asyncio.create_task(watch_disconnect())
    auth_monitor = asyncio.create_task(watch_authentication(request, run))
    try:
        async for _ in service.events(run):
            pass
    finally:
        monitor.cancel()
        auth_monitor.cancel()
        with suppress(asyncio.CancelledError):
            await monitor
        with suppress(asyncio.CancelledError):
            await auth_monitor
    return JSONResponse(run.public(), status_code=200 if run.status == "completed" else 499 if run.status == "cancelled" else 502)


@router.post("/api/v1/chat/stream")
async def stream_chat(request: Request, body: ChatInput):
    service = request.app.state.chat
    run = await prepare(request, body)

    async def events():
        monitor = asyncio.create_task(watch_authentication(request, run))
        try:
            async with aclosing(service.events(run)) as source:
                async for event in source:
                    yield "event: " + event["type"] + "\ndata: " + json.dumps(event, ensure_ascii=True) + "\n\n"
        finally:
            monitor.cancel()
            with suppress(asyncio.CancelledError):
                await monitor

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@router.post("/api/v1/chat/requests/{request_id}/cancel")
async def cancel(request: Request, request_id: UUID):
    active = request.app.state.chat.cancel(str(request_id))
    return {"request_id": str(request_id), "status": "cancelling" if active else "not_active"}


@router.get("/api/v1/chat/conversations")
async def conversations(request: Request, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0, le=10000)):
    return await asyncio.to_thread(request.app.state.chat.store.list, limit, offset)


@router.get("/api/v1/chat/conversations/{conversation_id}")
async def conversation(request: Request, conversation_id: UUID):
    result = await asyncio.to_thread(request.app.state.chat.store.get, str(conversation_id))
    for turn in result["turns"]:
        turn["error"] = {"code": turn["error_code"], "message": MESSAGES.get(turn["error_code"], "Dit antwoord is niet voltooid. Probeer opnieuw.")} if turn["error_code"] else None
    return result


@router.delete("/api/v1/chat/conversations/{conversation_id}")
async def delete_conversation(request: Request, conversation_id: UUID):
    service = request.app.state.chat
    if service.busy(str(conversation_id)):
        raise ChatError("conversation_busy", "Stop eerst het lopende antwoord.", 409)
    await asyncio.to_thread(service.store.delete, str(conversation_id))
    return {"status": "deleted", "conversation_id": str(conversation_id)}


@router.get("/api/v1/ai/providers")
async def providers(request: Request):
    return await request.app.state.chat.router.availability()


@router.get("/chat", include_in_schema=False)
async def webchat():
    return FileResponse(STATIC / "chat.html", headers={"Cache-Control": "no-store"})


@router.get("/chat/assets/{name}", include_in_schema=False)
async def asset(name: str):
    if name not in ("chat.css", "chat.js", "auth.js", "login.js", "security.js", "automations.js"):
        raise HTTPException(status_code=404)
    return FileResponse(STATIC / name)
