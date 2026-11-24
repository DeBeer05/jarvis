"""Bounded, authenticated mobile adapters. No inference libraries in server venv."""
import asyncio
import base64
import io
import json
import logging
import os
from pathlib import Path
import threading
import wave

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from providers.voice_pipe import OwnedVoicePipe
from server.api.routes import require_loopback
from server.security.gate import require_permission
from server.security.types import AuthError, digest

router = APIRouter(prefix="/api/v1/mobile", dependencies=[Depends(require_loopback)])
logger = logging.getLogger("jarvis.server")
MAX_AUDIO = 2_000_000  # <60 s of 16 kHz PCM16 mono plus WAV header


class SpeechBridge:
    """One persistent private helper; loaded models survive between requests."""
    def __init__(self,command=None):
        self.slot=asyncio.Lock();self.worker=OwnedVoicePipe(command or self.command);self.idle=None

    @staticmethod
    def command():
        root=Path(__file__).resolve().parents[1]
        executable=root/".local/voice-venv/Scripts/python.exe"
        if not executable.is_file():executable=root/".local/voice-venv/bin/python"
        if not executable.is_file():
            raise AuthError("speech_unavailable","De spraakruntime is niet geinstalleerd op de server.",503)
        return [str(executable),str(root/"desktop-client/voice_worker.py")]

    def run(self,operation,payload,valid=lambda:True):
        models=Path(os.environ.get("LOCALAPPDATA",str(Path.home()/".local/share")))/"JARVIS/Desktop/models"
        request={"operation":operation,"models":str(models),"model":"whisper-small","device":"auto",
                 "provider":"piper","voice":"ronnie","profile":"desktop",**payload}
        response=self.worker.exchange(request,valid=valid,timeout=100)
        if response.get("ok") and isinstance(response.get("result"),dict):return response["result"]
        raise AuthError("speech_unavailable","Controleer de ingestelde Whisper- en Piper-modellen op de server.",503)

    async def request(self,operation,payload):
        if self.slot.locked():raise AuthError("speech_busy","De spraakengine is bezet. Probeer opnieuw.",429)
        if self.idle:self.idle.cancel()
        payload=dict(payload);unload=payload.pop("unload_after_seconds",300)
        async with self.slot:
            cancelled=threading.Event()
            task=asyncio.create_task(asyncio.to_thread(self.run,operation,payload,lambda:not cancelled.is_set()))
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                cancelled.set();self.worker.cancel()
                await asyncio.gather(task,return_exceptions=True)
                raise
            except TimeoutError:
                raise AuthError("speech_timeout","Spraakverwerking duurde te lang.",504) from None
            finally:
                self.idle=asyncio.get_running_loop().call_later(max(30,min(3600,unload)),self.worker.cancel)

    async def close(self):
        if self.idle:self.idle.cancel()
        self.worker.cancel()
        for thread in self.worker.cleanup_threads:
            await asyncio.to_thread(thread.join,8)


async def audio_preferences(request):
    document=await asyncio.to_thread(request.app.state.natural.settings.get,request.state.principal)
    voice=document["settings"]["voice"]
    return {"model":voice["whisper_model"],"device":voice["processing"],"provider":voice["tts_provider"],
            "voice":voice["voice"],"speaker":voice["speaker"],"speed":voice["speed"],"unload_after_seconds":voice["unload_after_seconds"],
            "profile":"light" if document["settings"]["ai"]["performance"]=="saving" else "desktop"}


async def inference_call(request,operation,payload):
    """Disconnect/revocation cancels only the inference owned by this request."""
    work=asyncio.create_task(request.app.state.speech.request(operation,payload))
    async def watch():
        while True:
            if await request.is_disconnected():return "disconnected"
            if not await asyncio.to_thread(request.app.state.security.store.live,request.state.principal):return "revoked"
            await asyncio.sleep(.2)
    monitor=asyncio.create_task(watch())
    try:
        done,_=await asyncio.wait((work,monitor),return_when=asyncio.FIRST_COMPLETED)
        if work in done:return await work
        work.cancel();await asyncio.gather(work,return_exceptions=True)
        raise AuthError("speech_cancelled","Spraakverwerking gestopt; sessie of verbinding is niet meer geldig.",401 if monitor.result()=="revoked" else 499)
    finally:
        monitor.cancel()
        if not work.done():work.cancel()
        await asyncio.gather(work,monitor,return_exceptions=True)


@router.post("/speech/transcribe", dependencies=[Depends(require_permission("chat:write"))])
async def transcribe(request: Request):
    raw = await request.body()
    if len(raw) > MAX_AUDIO:
        raise AuthError("audio_too_large", "Neem maximaal 60 seconden op.", 413)
    try:
        with wave.open(io.BytesIO(raw), "rb") as wav:
            if wav.getnchannels() != 1 or wav.getsampwidth() != 2 or wav.getframerate() != 16000 or not 0 < wav.getnframes() <= 960000:
                raise ValueError()
            if len(wav.readframes(wav.getnframes())) != wav.getnframes() * 2:
                raise ValueError()
    except (ValueError, EOFError, wave.Error):
        raise AuthError("invalid_audio", "Gebruik mono PCM16 WAV op 16 kHz, maximaal 60 seconden.", 422) from None
    principal = request.state.principal
    await asyncio.to_thread(request.app.state.security.store.rate, "mobile-stt:" + principal.device_id, 12)
    result = await inference_call(request,"stt", {**await audio_preferences(request), "audio": base64.b64encode(raw).decode()})
    # Reject results if authorization was revoked during inference.
    await asyncio.to_thread(request.app.state.security.store.own_device, principal)
    return {"text": result["text"], "seconds": result["seconds"]}


class Speak(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=700)
    speed: float | None = Field(default=None, ge=.7, le=1.5)


@router.post("/speech/synthesize", dependencies=[Depends(require_permission("chat:read"))])
async def synthesize(request: Request, body: Speak):
    principal = request.state.principal
    await asyncio.to_thread(request.app.state.security.store.rate, "mobile-tts:" + principal.device_id, 60)
    preferences=await audio_preferences(request)
    if body.speed is not None:preferences["speed"]=body.speed
    result = await inference_call(request,"tts", {**preferences,"text": body.text})
    await asyncio.to_thread(request.app.state.security.store.own_device, principal)
    return Response(base64.b64decode(result["audio"], validate=True), media_type="audio/wav")


class PushRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: SecretStr = Field(min_length=20, max_length=4096)
    categories: set[str] = Field(default_factory=lambda: {"urgent", "appointments", "important", "news"}, max_length=4)


@router.post("/push", dependencies=[Depends(require_permission("status:read"))])
async def register_push(request: Request, body: PushRegistration):
    if not body.categories <= {"urgent", "appointments", "important", "news"}:
        raise AuthError("invalid_category", "Onbekende meldingscategorie.", 422)
    # No Firebase service credentials in phase 6. A digest proves registration
    # without retaining a deliverable FCM address or claiming remote delivery.
    principal = request.state.principal
    await asyncio.to_thread(request.app.state.security.store.rate, "mobile-push:" + principal.device_id, 20)
    if principal.device_id not in request.app.state.mobile_push and len(request.app.state.mobile_push) >= 64:
        request.app.state.mobile_push.pop(next(iter(request.app.state.mobile_push)))
    request.app.state.mobile_push[principal.device_id] = {"digest": digest(body.token.get_secret_value()), "categories": sorted(body.categories)}
    return {"registered": True, "delivery": "local-test-only", "external_delivery_available": False}


@router.delete("/push", dependencies=[Depends(require_permission("status:read"))])
async def unregister_push(request: Request):
    request.app.state.mobile_push.pop(request.state.principal.device_id, None)
    return {"registered": False}
