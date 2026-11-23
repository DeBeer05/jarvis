import base64
import json
import logging
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

from jarvis_client.voice.settings import model_directory


ERRORS = {
    "stt_model_missing": "Spraakmodel ontbreekt. Installeer het gekozen Whisper-model in de modelmap.",
    "tts_model_missing": "Nederlandse Piper-stem ontbreekt. Installeer de ONNX-stem en JSON-configuratie.",
    "tts_provider_unavailable": "Deze stemengine is niet beschikbaar. Kies Piper.",
    "voice_failed": "Spraakverwerking mislukt. Controleer de modellen of kies CPU in de spraakinstellingen.",
}


class InferenceWorker:
    """Supervised, private pipe; cancellation terminates only this owned helper."""
    def __init__(self, command=None):
        self.command = command
        self.process = None
        self.lock = threading.Lock()
        self.state_lock = threading.RLock()
        self.epoch = 0
        self.cleanup_threads = []

    @property
    def busy(self):
        return any(thread.is_alive() for thread in self.cleanup_threads)

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

    def cancel(self):
        with self.state_lock:
            self.epoch += 1
            process, self.process = self.process, None
        if process:
            # Windows venv launchers may have an interpreter child. Terminate
            # this owned process tree, not just the launcher, off the UI thread.
            thread = threading.Thread(target=self._reap, args=(process,), daemon=True)
            self.cleanup_threads = [item for item in self.cleanup_threads if item.is_alive()] + [thread]
            thread.start()

    @staticmethod
    def _reap(process):
        try:
            if sys.platform == "win32" and process.poll() is None:
                result = subprocess.run([str(Path(os.environ["SystemRoot"]) / "System32/taskkill.exe"),
                                         "/PID", str(process.pid), "/T", "/F"], capture_output=True,
                                        creationflags=subprocess.CREATE_NO_WINDOW, timeout=5, check=False)
                logging.getLogger("jarvis.voice").info("Owned speech helper stopped status=%d", result.returncode)
            elif process.poll() is None:
                process.terminate()
            process.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            if process.poll() is None:
                process.kill()
        finally:
            for stream in (process.stdin, process.stdout):
                try:
                    stream.close()
                except (OSError, ValueError):
                    pass

    @staticmethod
    def _stderr(stream):
        # Drain native diagnostics without retaining private content or losing errors silently.
        had_output = False
        try:
            while stream.read(4096):
                if not had_output:
                    logging.getLogger("jarvis.voice").warning("Voice helper emitted native diagnostics; private contents omitted")
                    had_output = True
        finally:
            stream.close()

    def request(self, operation, settings, *, valid=lambda: True, **payload):
        with self.lock:
            if not valid():
                raise RuntimeError("Spraakopdracht geannuleerd.")
            with self.state_lock:
                if self.process is None or self.process.poll() is not None:
                    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                    self.process = subprocess.Popen(self.resolve_command(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                                    stderr=subprocess.PIPE, creationflags=flags)
                    threading.Thread(target=self._stderr, args=(self.process.stderr,), daemon=True).start()
                process, epoch = self.process, self.epoch
            request = {"operation": operation, "models": model_directory(settings), "model": settings.model,
                       "device": settings.device, "profile": settings.profile, "provider": settings.provider,
                       "speaker": settings.speaker, "voice": settings.voice, "speed": settings.speed, **payload}
            result = queue.Queue(maxsize=1)

            def exchange():
                try:
                    process.stdin.write(json.dumps(request).encode("utf-8") + b"\n")
                    process.stdin.flush()
                    line = process.stdout.readline(24 * 1024 * 1024)
                    if not line.endswith(b"\n"):
                        raise ValueError("protocol")
                    result.put(json.loads(line))
                except Exception:
                    result.put({"ok": False, "code": "voice_failed"})

            threading.Thread(target=exchange, daemon=True).start()
            deadline = time.monotonic() + 120
            while True:
                if not valid() or epoch != self.epoch:
                    raise RuntimeError("Spraakopdracht geannuleerd.")
                try:
                    response = result.get(timeout=0.1)
                    break
                except queue.Empty:
                    if time.monotonic() > deadline:
                        self.cancel()
                        raise RuntimeError("Spraakverwerking duurde te lang; afgebroken.")
            if not response.get("ok"):
                raise RuntimeError(ERRORS.get(response.get("code"), ERRORS["voice_failed"]))
            return response["result"]

    def transcribe(self, audio, settings, valid):
        return self.request("stt", settings, valid=valid, audio=base64.b64encode(audio).decode("ascii"))

    def synthesize(self, text, settings, valid):
        result = self.request("tts", settings, valid=valid, text=text)
        return base64.b64decode(result["audio"], validate=True), result
