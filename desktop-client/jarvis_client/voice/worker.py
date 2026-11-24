import base64
import logging
from pathlib import Path
import sys

from providers.voice_pipe import OwnedVoicePipe
from jarvis_client.voice.settings import model_directory


ERRORS = {
    "stt_model_missing": "Spraakmodel ontbreekt. Installeer het gekozen Whisper-model in de modelmap.",
    "tts_model_missing": "Nederlandse Piper-stem ontbreekt. Installeer de ONNX-stem en JSON-configuratie.",
    "tts_provider_unavailable": "Deze stemengine is niet beschikbaar. Kies Piper.",
    "voice_failed": "Spraakverwerking mislukt. Controleer de modellen of kies CPU in de spraakinstellingen.",
}


class InferenceWorker(OwnedVoicePipe):
    def resolve_command(self):
        if self.command:
            return self.command
        if getattr(sys, "frozen", False):
            executable = Path(sys.executable).parent / "voice-runtime/JARVIS-Voice.exe"
            if executable.is_file():
                return [str(executable)]
        else:
            root = Path(__file__).resolve().parents[3]
            executable = root / ".local/voice-venv/Scripts/python.exe"
            if executable.is_file():
                return [str(executable), str(root / "desktop-client/voice_worker.py")]
        raise RuntimeError("Spraakruntime ontbreekt. Voer scripts/Install-VoiceRuntime.ps1 uit of gebruik de volledige portable app.")


    def request(self, operation, settings, *, valid=lambda: True, **payload):
        request = {"operation": operation, "models": model_directory(settings), "model": settings.model,
                   "device": settings.device, "profile": settings.profile, "provider": settings.provider,
                   "speaker": settings.speaker, "voice": settings.voice, "speed": settings.speed, **payload}
        try:
            response = self.exchange(request, valid=valid, timeout=120)
        except TimeoutError:
            raise RuntimeError("Spraakverwerking duurde te lang; afgebroken.") from None
        if not response.get("ok") or not isinstance(response.get("result"), dict):
            code = response.get("code") if response.get("code") in ERRORS else "voice_failed"
            logging.getLogger("jarvis.voice").warning("Local speech request failed category=%s", code)
            raise RuntimeError(ERRORS[code])
        return response["result"]

    def transcribe(self, audio, settings, valid):
        return self.request("stt", settings, valid=valid, audio=base64.b64encode(audio).decode("ascii"))

    def synthesize(self, text, settings, valid):
        result = self.request("tts", settings, valid=valid, text=text)
        return base64.b64decode(result["audio"], validate=True), result
