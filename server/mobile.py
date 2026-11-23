"""Bounded, authenticated mobile adapters. No inference libraries in server venv."""
import asyncio
import base64
import io
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import wave

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from server.api.routes import require_loopback
from server.security.gate import require_permission
from server.security.types import AuthError, digest

router = APIRouter(prefix="/api/v1/mobile", dependencies=[Depends(require_loopback)])
logger = logging.getLogger("jarvis.server")
MAX_AUDIO = 2_000_000  # <60 s of 16 kHz PCM16 mono plus WAV header


class SpeechBridge:
    def __init__(self):
        self.slot = asyncio.Lock()

    def run(self, operation, payload):
        root = Path(__file__).resolve().parents[1]
        executable = root / ".local/voice-venv/Scripts/python.exe"
        if not executable.is_file():
            executable = root / ".local/voice-venv/bin/python"
        if not executable.is_file():
            raise AuthError("speech_unavailable", "De spraakruntime is niet geïnstalleerd op de server.", 503)
        models = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local/share"))) / "JARVIS/Desktop/models"
        request = {"operation": operation, "models": str(models), "model": "whisper-small", "device": "auto",
                   "provider": "piper", "voice": "ronnie", "profile": "light", **payload}
        # This owned process has no audio hardware, secrets or listening sockets.
        process = subprocess.Popen([str(executable), str(root / "desktop-client/voice_worker.py")],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            output, diagnostics = process.communicate((json.dumps(request) + "\n").encode(), timeout=100)
        except subprocess.TimeoutExpired:
            if sys.platform == "win32" and process.poll() is None:
                subprocess.run([str(Path(os.environ["SystemRoot"]) / "System32/taskkill.exe"), "/PID", str(process.pid), "/T", "/F"],
                               capture_output=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW, check=False)
            process.kill(); process.communicate()
            raise
        if diagnostics:
            logger.warning("mobile_speech_diagnostic")  # native text may contain private input
        if process.returncode or len(output) > 12_000_000:
            raise AuthError("speech_unavailable", "Spraakverwerking is tijdelijk niet beschikbaar.", 503)
        try:
            response = json.loads(output)
            if response["ok"]:
                return response["result"]
        except (ValueError, KeyError):
            pass
        raise AuthError("speech_unavailable", "Controleer Whisper Small en Piper Ronnie op de server.", 503)

    async def request(self, operation, payload):
        if self.slot.locked():
            raise AuthError("speech_busy", "De spraakengine is bezet. Probeer opnieuw.", 429)
        async with self.slot:
            try:
                return await asyncio.to_thread(self.run, operation, payload)
            except subprocess.TimeoutExpired:
                raise AuthError("speech_timeout", "Spraakverwerking duurde te lang.", 504) from None


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
    result = await request.app.state.speech.request("stt", {"audio": base64.b64encode(raw).decode()})
    # Reject results if authorization was revoked during inference.
    await asyncio.to_thread(request.app.state.security.store.own_device, principal)
    return {"text": result["text"], "seconds": result["seconds"]}


class Speak(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=700)
    speed: float = Field(default=1, ge=.7, le=1.5)


@router.post("/speech/synthesize", dependencies=[Depends(require_permission("chat:read"))])
async def synthesize(request: Request, body: Speak):
    principal = request.state.principal
    await asyncio.to_thread(request.app.state.security.store.rate, "mobile-tts:" + principal.device_id, 60)
    result = await request.app.state.speech.request("tts", {"text": body.text, "speed": body.speed})
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
