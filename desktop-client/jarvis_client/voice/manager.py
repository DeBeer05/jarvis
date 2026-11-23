import queue
import threading
import time
from dataclasses import replace

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from jarvis_client.voice.audio import AudioInputManager, AudioOutputManager
from jarvis_client.voice.processing import AudioCache, InterruptionController, SentenceBuffer, WakeWordEngine
from jarvis_client.voice.worker import InferenceWorker


class VoiceConversationManager(QObject):
    changed = Signal(str)
    transcript = Signal(str)
    answer = Signal(str)
    ready_text = Signal(str)
    problem = Signal(str)
    metrics = Signal(object)
    delivered = Signal(object)

    def __init__(self, settings, parent=None, *, worker=None, audio_input=None, audio_output=None):
        super().__init__(parent)
        self.settings = settings
        self.worker = worker or InferenceWorker()
        self.input_factory = (lambda: audio_input) if audio_input is not None else AudioInputManager
        self.input = self.input_factory()
        self.output = audio_output or AudioOutputManager()
        self.interruptions = InterruptionController()
        self.cache = AudioCache()
        self.cache_lock = threading.Lock()
        self.wake = WakeWordEngine()
        self.consent = self.wake_enabled = self.authorized = False
        self.recording = self.closed = self.responding = self.voice_next = False
        self.armed = False
        self.state = "Microfoon uit"
        self.pending = queue.Queue(maxsize=32)
        self.threads = []
        self.sentence = SentenceBuffer()
        self.answer_text = ""
        self.response_started = self.first_token = self.first_audio = 0
        self.measurements = {}
        self.scheduled = QTimer(self)
        self.scheduled.setSingleShot(True)
        self.scheduled.timeout.connect(self._auto_listen)
        self.delivered.connect(self._delivered)

    @property
    def busy(self):
        return any(thread.is_alive() for thread in self.threads) or getattr(self.worker, "busy", False)

    def _thread(self, function):
        self.threads = [thread for thread in self.threads if thread.is_alive()]
        thread = threading.Thread(target=function, daemon=True)
        self.threads.append(thread)
        thread.start()

    def set_state(self, state):
        self.state = state
        self.changed.emit(state)

    def set_consent(self, value):
        self.consent = bool(value)
        if not self.consent:
            self.wake_enabled = False
            self.stop()
        else:
            self.set_state("Klaar · microfoon uit")

    def set_authorized(self, value):
        self.authorized = bool(value)
        if not self.authorized:
            self.set_consent(False)
            self.transcript.emit("")
            self.answer.emit("")
            with self.cache_lock:
                self.cache.clear()

    def toggle_wake(self, enabled):
        if enabled and not (self.consent and self.authorized):
            self.problem.emit("Log in en geef eerst microfoontoestemming voor deze appsessie.")
            return False
        self.stop()
        self.wake_enabled = bool(enabled)
        self.armed = False
        if enabled:
            self.scheduled.start(0)
        return True

    def toggle_recording(self):
        if self.recording:
            self.input.stop()
        else:
            self.start_recording()

    def start_recording(self, automatic=False):
        if self.closed:
            return
        if not self.consent or not self.authorized:
            self.problem.emit("Log in en vink microfoontoestemming aan in Spraak. Er is geen opname gestart.")
            return
        if self.recording:
            return
        self.stop(keep_wake=True)
        generation = self.interruptions.generation
        settings = replace(self.settings)
        wake_gate = automatic and self.wake_enabled and not self.armed
        self.recording = True
        capture_input = self.input = self.input_factory()
        capture_input.prepare()
        self.set_state("Standby · microfoon actief · zeg Hé JARVIS" if wake_gate else "Luisteren · microfoon actief · klik nogmaals om te verwerken")
        timeout = settings.followup_seconds if automatic and self.armed and settings.followup_seconds else 6

        def capture():
            try:
                audio = capture_input.capture(settings, consent=True, timeout=timeout)
                if not self.interruptions.valid(generation):
                    return
                self.delivered.emit((generation, "transcribing", None))
                result = self.worker.transcribe(audio, settings, lambda: self.interruptions.valid(generation)) if audio else {"text": "", "seconds": 0}
                self.delivered.emit((generation, "captured", (result, wake_gate)))
            except Exception as error:
                self.delivered.emit((generation, "error", str(error)))

        self._thread(capture)

    @Slot(object)
    def _delivered(self, item):
        generation, kind, payload = item
        if self.closed or not self.interruptions.valid(generation):
            return
        if kind == "transcribing":
            self.recording = False
            self.set_state("Spraak herkennen · microfoon uit")
        elif kind == "captured":
            self.recording = False
            result, wake_gate = payload
            self.measurements = {"stt_seconds": round(result["seconds"], 3), "device": result.get("device", "cpu"), "cpu_fallback": result.get("cpu_fallback", False)}
            text = result["text"].strip()
            if wake_gate:
                detected, text = self.wake.detect(text)
                self.measurements["wake_after_utterance_seconds"] = round(result["seconds"], 3)
                if not detected:
                    self.scheduled.start(150)
                    self.set_state("Standby hervatten · microfoon uit")
                    return
                if not text:
                    self.armed = True
                    self.scheduled.start(0)
                    return
            if text:
                self.transcript.emit(text)
                self.voice_next = True
                self.armed = False
                self.ready_text.emit(text)
            else:
                self.set_state("Geen spraak herkend · microfoon uit")
                self.armed = False
                if self.wake_enabled:
                    self.scheduled.start(150)
        elif kind == "playing":
            if not self.first_audio:
                self.first_audio = time.perf_counter()
                self.measurements["first_audio_seconds"] = round(self.first_audio - self.response_started, 3)
            self.set_state("JARVIS spreekt · microfoon uit")
        elif kind == "drained":
            self.responding = False
            self.measurements["total_seconds"] = round(time.perf_counter() - self.response_started, 3)
            self.metrics.emit(dict(self.measurements))
            self.set_state("Klaar · microfoon uit")
            if self.consent and self.authorized and (self.wake_enabled or self.settings.followup_seconds):
                self.armed = bool(self.settings.followup_seconds)
                # Let the output driver's final buffer drain to prevent self-triggering.
                self.scheduled.start(450)
        elif kind == "error":
            self.stop()
            self.problem.emit(payload)
            self.set_state("Spraak gestopt · controleer de melding · microfoon uit")

    def _auto_listen(self):
        if self.consent and self.authorized and not self.responding:
            self.start_recording(automatic=True)

    def begin_response(self):
        speak = self.voice_next
        self.stop(keep_wake=True)
        self.voice_next = False
        if not speak:
            return
        self.responding = True
        self.sentence, self.answer_text = SentenceBuffer(), ""
        self.response_started = time.perf_counter()
        self.first_token = self.first_audio = 0
        self.set_state("Antwoord ophalen · microfoon uit")
        generation, settings, pending = self.interruptions.generation, replace(self.settings), self.pending

        def consume():
            while self.interruptions.valid(generation) and not self.closed:
                try:
                    text = pending.get(timeout=0.1)
                except queue.Empty:
                    continue
                if text is None:
                    self.delivered.emit((generation, "drained", None))
                    return
                try:
                    valid = lambda: self.interruptions.valid(generation) and not self.closed
                    key = text, settings.provider, settings.voice, settings.speaker, settings.speed, settings.models
                    with self.cache_lock:
                        audio = self.cache.get(key) if settings.cache else None
                    if audio is None:
                        audio, _ = self.worker.synthesize(text, settings, valid)
                        if settings.cache and valid():
                            with self.cache_lock:
                                self.cache.put(key, audio)
                    if valid():
                        self.output.play(audio, settings, valid, lambda: self.delivered.emit((generation, "playing", None)))
                except Exception as error:
                    self.delivered.emit((generation, "error", str(error)))
                    return

        self._thread(consume)

    def delta(self, text):
        if not self.responding:
            return
        if text and not self.first_token:
            self.first_token = time.perf_counter()
            self.measurements["first_token_seconds"] = round(self.first_token - self.response_started, 3)
        self.answer_text += text
        self.answer.emit(self.answer_text)
        try:
            for sentence in self.sentence.feed(text):
                self.pending.put_nowait(sentence)
        except (queue.Full, ValueError):
            self.stop()
            self.problem.emit("Spraakbuffer vol; audio gestopt. Het tekstantwoord blijft beschikbaar.")

    def finish_response(self, successful=True):
        if not self.responding:
            return
        if not successful:
            self.stop()
            return
        try:
            for sentence in self.sentence.feed("", final=True):
                self.pending.put_nowait(sentence)
            self.pending.put_nowait(None)
        except queue.Full:
            self.stop()
            self.problem.emit("Spraakbuffer vol; audio gestopt.")

    def sample(self):
        if self.recording or self.responding:
            self.stop()
        self.voice_next = True
        self.begin_response()
        self.delta("Hallo, ik ben JARVIS. Dit is mijn Nederlandse stem. Je kunt mij met de stopknop onderbreken.")
        self.finish_response()

    def stop(self, keep_wake=False):
        self.scheduled.stop()
        self.interruptions.cancel()
        self.input.stop(discard=True)
        self.output.stop()
        self.worker.cancel()
        self.recording = self.responding = self.voice_next = False
        self.pending = queue.Queue(maxsize=32)
        if not keep_wake:
            self.wake_enabled = self.armed = False
        self.set_state("Gestopt · microfoon uit")

    def close(self):
        self.closed = True
        self.set_authorized(False)
