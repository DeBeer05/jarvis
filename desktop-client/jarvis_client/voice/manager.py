import queue
import threading
import time
import re
from copy import deepcopy
from dataclasses import replace
from uuid import uuid4
from providers.speech_format import speech_chunks

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from jarvis_client.voice.audio import AudioInputManager, AudioOutputManager
from jarvis_client.voice.processing import AudioCache, InterruptionController, SentenceBuffer, WakeWordEngine
from jarvis_client.voice.worker import InferenceWorker
from jarvis_client.voice.echo import EchoReference, resembles_output
from jarvis_client.voice.turns import AdaptiveTurn


class VoiceConversationManager(QObject):
    preview_finished = Signal()
    changed = Signal(str)
    transcript = Signal(str)
    answer = Signal(str)
    ready_text = Signal(str)
    problem = Signal(str)
    metrics = Signal(object)
    level = Signal(float)
    delivered = Signal(object)
    session_ended = Signal(str)
    playback_finished = Signal()
    interrupted = Signal()

    def __init__(self, settings, parent=None, *, worker=None, audio_input=None, audio_output=None):
        super().__init__(parent)
        self.settings = settings
        self.worker = worker or InferenceWorker()
        self.next_worker=None
        self.input_factory = (lambda: audio_input) if audio_input is not None else AudioInputManager
        self.input = self.input_factory()
        self.output = audio_output or AudioOutputManager()
        self.echo=EchoReference()
        self.output.reference=self.echo
        self.barge_active=False
        self.barge_failed_generation=None
        self.interruptions = InterruptionController()
        self.cache = AudioCache()
        self.cache_lock = threading.Lock()
        self.wake = WakeWordEngine()
        self.consent = self.wake_enabled = self.authorized = False
        self.recording = self.closed = self.responding = self.voice_next = False
        self.armed = False
        self.options=None
        self.session_active=False
        self.session_started=self.last_activity=0.
        self.state = "Microfoon uit"
        self.pending:queue.Queue[str|None] = queue.Queue(maxsize=32)
        self.threads = []
        self.sentence = SentenceBuffer()
        self.answer_text = ""
        self.stream_audio=True
        self.prefetch_active=False
        self.response_started = self.first_token = self.first_audio = 0.
        self.measurements = {}
        self.scheduled = QTimer(self)
        self.scheduled.setSingleShot(True)
        self.scheduled.timeout.connect(self._auto_listen)
        self.delivered.connect(self._delivered)

    def configure_natural(self,settings):
        # Snapshot for the next turn; never open a microphone or alter local consent.
        self.options=deepcopy(settings)
        if self.session_active and not settings["conversations"]["enabled"]:
            self.end_session("uitgeschakeld")

    def select_worker(self,worker):
        if self.next_worker:getattr(self.next_worker,"close",self.next_worker.cancel)()
        self.next_worker=worker
        if not (self.recording or self.responding or self.busy):self.switch_worker()

    def switch_worker(self):
        if self.next_worker:
            getattr(self.worker,"close",self.worker.cancel)()
            self.worker,self.next_worker=self.next_worker,None

    def effective_settings(self):
        settings=replace(self.settings)
        if not self.options or not self.options["conversations"]["enabled"]:return settings
        voice=self.options["voice"];listening=self.options["listening"]
        provider=voice['tts_provider']
        if not getattr(self.worker,'centralized',False) and provider in ('auto','elevenlabs'):provider='piper'
        return replace(settings,model=voice["whisper_model"],device=voice["processing"],provider=provider,
                       voice=voice["voice"],speaker=voice.get("speaker",0),speed=voice["speed"],output_gain=voice["volume"],cache=voice["cache"],
                       max_seconds=listening["maximum_listen_seconds"],silence_seconds=(listening["thinking_pause_ms"] if listening["adaptive"] else listening["normal_silence_ms"])/1000,
                       sensitivity=max(0,min(1,(.028-listening["vad_threshold"])/.023)))

    def activate_session(self):
        if self.options and self.options["conversations"]["enabled"] and not self.session_active:
            self.session_active=True;self.session_started=self.last_activity=time.monotonic()

    def continuous(self):
        return bool(self.options and self.options["conversations"]["enabled"] and self.options["conversations"]["continuous"] and self.session_active)

    def end_session(self,reason="afgesloten"):
        wake=self.wake_enabled
        self.stop()
        self.wake_enabled=wake and self.consent and self.authorized
        self.set_state("Standby")
        self.session_ended.emit(reason)
        if self.wake_enabled:self.scheduled.start(150)

    def farewell(self,text):
        if not self.options:return False
        normalize=lambda value:re.sub(r"[^\w\s]","",value.casefold()).strip()
        return normalize(text) in {normalize(value) for value in self.options["conversations"]["ending_phrases"]}

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
            self.set_state("Microfoon niet toegestaan" if self.authorized else "Microfoon uit")
        else:
            self.set_state("Klaar om te luisteren")

    def set_authorized(self, value):
        was_authorized = self.authorized
        self.authorized = bool(value)
        if not self.authorized:
            self.set_consent(False)
            self.transcript.emit("")
            self.answer.emit("")
            with self.cache_lock:
                self.cache.clear()
        elif not was_authorized and self.settings.microphone_allowed:
            self.set_consent(True)
        elif not was_authorized:
            self.set_state("Microfoon niet toegestaan")

    def toggle_wake(self, enabled):
        if enabled and not (self.consent and self.authorized):
            self.problem.emit("Log in en geef microfoontoestemming bij Stem en microfoon instellen.")
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
            self.problem.emit("Log in en sta je microfoon toe bij Stem en microfoon instellen.")
            return
        if self.recording:
            return
        self.stop(keep_wake=True)
        self.switch_worker()
        generation = self.interruptions.generation
        settings = self.effective_settings()
        if not automatic:self.activate_session()
        wake_gate = automatic and self.wake_enabled and not self.armed
        if wake_gate and self.options:
            settings=replace(settings,sensitivity=max(0.,min(1.,settings.sensitivity+(self.options["conversations"].get("wake_sensitivity",.6)-.6)*.3)))
        self.recording = True
        capture_input = self.input = self.input_factory()
        capture_input.prepare()
        self.set_state("Ik wacht op Hé JARVIS" if wake_gate else "Ik luister…")
        timeout = settings.followup_seconds if automatic and self.armed and settings.followup_seconds else 6

        def capture():
            try:
                previous = 0.
                def activity(rms, voiced):
                    nonlocal previous
                    now = time.monotonic()
                    if now - previous >= .1:
                        previous = now
                        self.delivered.emit((generation, "activity", (rms, voiced, wake_gate)))
                turns=None
                if self.options and self.options["listening"]["adaptive"] and not wake_gate:
                    turns=AdaptiveTurn(lambda audio,valid:self.worker.transcribe(audio,settings,valid),lambda:self.interruptions.valid(generation) and not self.closed,
                        normal=self.options["listening"]["normal_silence_ms"]/1000,thinking=self.options["listening"]["thinking_pause_ms"]/1000,
                        partial=lambda result,revision,controller:self.delivered.emit((generation,"partial",(result,revision,controller))))
                audio = capture_input.capture(settings, consent=True, timeout=timeout, activity=activity,turns=turns)
                if not self.interruptions.valid(generation):
                    return
                self.delivered.emit((generation, "transcribing", None))
                result = (getattr(capture_input,"transcription",None) or self.worker.transcribe(audio, settings, lambda: self.interruptions.valid(generation))) if audio else {"text": "", "seconds": 0}
                self.delivered.emit((generation, "captured", (result, wake_gate)))
            except Exception as error:
                self.delivered.emit((generation, "error", str(error)))

        self._thread(capture)

    def start_barge_capture(self,generation):
        if self.prefetch_active:return
        if self.closed or not self.interruptions.valid(generation) or not self.responding or self.recording:return
        if self.barge_failed_generation==generation:return
        if not (self.session_active and self.consent and self.authorized and self.options and self.options["listening"].get("barge_in")):return
        if not all(hasattr(self.output,name) for name in ("pause","resume")):return
        self.barge_active=self.recording=True
        settings=replace(self.effective_settings(),sensitivity=self.options["listening"]["barge_in_sensitivity"])
        capture_input=self.input=self.input_factory();capture_input.prepare()
        filtered=self.echo.filter if self.options["listening"].get("echo_suppression",True) else None
        def capture():
            voiced_seconds=0.;paused=False
            def activity(rms,voiced):
                nonlocal voiced_seconds,paused
                voiced_seconds=voiced_seconds+.03 if voiced else 0.
                if voiced_seconds>=.12 and not paused:
                    paused=True;self.output.pause()
                    self.delivered.emit((generation,"barge_paused",None))
            try:
                audio=capture_input.capture(settings,consent=True,timeout=3,activity=activity,preprocess=filtered)
                valid=lambda:self.interruptions.valid(generation) and self.responding and not self.closed
                if not valid():return
                if audio:
                    self.output.pause()
                    result=self.worker.transcribe(audio,settings,valid)
                else:result={"text":""}
                self.delivered.emit((generation,"barge_captured",result))
            except Exception:
                # A duplex driver failure must leave the answer usable. Report
                # the disabled monitor once; ordinary PTT remains available.
                self.delivered.emit((generation,"barge_error",None))
        self._thread(capture)

    @Slot(object)
    def _delivered(self, item):
        generation, kind, payload = item
        if self.closed or not self.interruptions.valid(generation):
            return
        if kind == "activity":
            rms, voiced, wake_gate = payload
            self.level.emit(min(1.0, rms * 8))
            self.set_state("Ik hoor je…" if voiced else ("Ik wacht op Hé JARVIS" if wake_gate else "Ik luister…"))
        elif kind == "partial":
            result,revision,controller=payload
            if self.recording and controller.revision==revision and result.get("text"):
                self.transcript.emit(result["text"])
                self.set_state("Voorlopige herkenning · wacht op je vervolg" if not controller.finished(controller.normal) else "Uitspraak afronden…")
        elif kind == "transcribing":
            self.recording = False
            self.level.emit(0)
            self.set_state("Spraak verwerken…")
        elif kind == "captured":
            self.recording = False
            result, wake_gate = payload
            self.measurements = {"stt_seconds": round(result["seconds"], 3), "device": result.get("device", "cpu"), "cpu_fallback": result.get("cpu_fallback", False)}
            text = result["text"].strip()
            if wake_gate:
                detected, text = self.wake.detect(text,self.options["conversations"]["wake_word"] if self.options else None)
                self.measurements["wake_after_utterance_seconds"] = round(result["seconds"], 3)
                if not detected:
                    self.metrics.emit({"wake_miss":1})
                    self.scheduled.start(150)
                    self.set_state("Ik wacht op Hé JARVIS")
                    return
                self.activate_session()
                if not text:
                    self.armed = True
                    self.scheduled.start(0)
                    return
            if text:
                self.transcript.emit(text)
                if self.session_active and self.farewell(text):
                    self.end_session("afscheid")
                    return
                self.last_activity=time.monotonic()
                self.voice_next = True
                self.armed = self.continuous()
                self.ready_text.emit(text)
            else:
                self.set_state("Geen duidelijke spraak gehoord")
                self.armed = self.continuous()
                if self.wake_enabled or self.continuous():
                    self.scheduled.start(150)
        elif kind == "playing":
            if not self.first_audio:
                self.first_audio = time.perf_counter()
                self.measurements["first_audio_seconds"] = round(self.first_audio - self.response_started, 3)
            self.set_state("JARVIS spreekt")
            self.start_barge_capture(generation)
            if self.barge_active:self.set_state("JARVIS spreekt · luistert naar onderbreking")
        elif kind == "barge_paused":
            if self.responding:self.set_state("Ik hoor je · antwoord gepauzeerd")
        elif kind == "barge_captured":
            if not self.responding or not self.barge_active:return
            self.recording=self.barge_active=False
            text=payload.get("text","").strip()
            if not text or resembles_output(text,self.answer_text):
                self.measurements["rejected_interruptions"]=self.measurements.get("rejected_interruptions",0)+bool(text)
                if text:self.metrics.emit({"rejected_interruption":1})
                self.output.resume()
                QTimer.singleShot(150,lambda:self.start_barge_capture(generation))
                self.set_state("JARVIS spreekt · luistert naar onderbreking")
                return
            self.stop(keep_wake=True)
            self.measurements["interruptions"]=self.measurements.get("interruptions",0)+1
            self.metrics.emit({"interruption":1})
            self.interrupted.emit()
            self.transcript.emit(text)
            if self.farewell(text):self.end_session("afscheid");return
            self.last_activity=time.monotonic();self.voice_next=True;self.armed=self.continuous()
            self.ready_text.emit(text)
        elif kind == "barge_error":
            if not self.responding or not self.barge_active:return
            self.barge_failed_generation=generation
            self.recording=self.barge_active=False
            self.output.resume()
            self.problem.emit("Gelijktijdig luisteren lukt niet met dit audioapparaat. Gebruik de spreekknop om te onderbreken.")
        elif kind == "preview_done":
            self.responding=False;self.set_state("Stemvoorbeeld voltooid");self.preview_finished.emit()
        elif kind == "drained":
            if self.barge_active:self.input.stop(discard=True)
            self.recording=self.barge_active=False
            self.responding = False
            self.last_activity=time.monotonic()
            self.measurements["total_seconds"] = round(time.perf_counter() - self.response_started, 3)
            self.metrics.emit(dict(self.measurements))
            self.set_state("Klaar om te luisteren")
            self.playback_finished.emit()
            if self.consent and self.authorized and (self.wake_enabled or self.settings.followup_seconds or self.continuous()):
                self.armed = bool(self.settings.followup_seconds) or self.continuous()
                # Let the output driver's final buffer drain to prevent self-triggering.
                self.scheduled.start(450)
        elif kind == "error":
            self.stop()
            self.set_state("Spraak lukt nog niet")
            self.problem.emit(payload)

    def _auto_listen(self):
        if self.session_active and self.options:
            config=self.options["conversations"];now=time.monotonic()
            if now-self.session_started>=config["maximum_seconds"] or config["automatic_end"] and now-self.last_activity>=config["inactivity_seconds"]:
                self.end_session("time-out")
                return
            if self.continuous() and not config["auto_listen"]:return
        if self.consent and self.authorized and not self.responding:
            # Never open the microphone from a late timer after Stop/timeout.
            if not (self.wake_enabled or self.armed or self.continuous()):return
            self.start_recording(automatic=True)

    def begin_response(self):
        speak = self.voice_next
        self.stop(keep_wake=True)
        self.switch_worker()
        self.voice_next = False
        if hasattr(self.worker,"begin_utterance"):self.worker.begin_utterance(str(uuid4()),None)
        if not speak:
            return
        self.responding = True
        self.stream_audio=not self.options or not self.options["conversations"]["enabled"] or self.options["voice"].get("streaming",True)
        self.sentence, self.answer_text = SentenceBuffer(), ""
        self.response_started = time.perf_counter()
        self.first_token = self.first_audio = 0.
        self.set_state("JARVIS denkt…")
        generation, settings, pending = self.interruptions.generation, self.effective_settings(), self.pending
        worker=self.worker
        valid = lambda: self.interruptions.valid(generation) and not self.closed
        # One prepared WAV alongside the one playing; never an unbounded audio
        # queue or another inference engine. Keep STT priority when barge-in is on.
        prefetch=not (self.options and self.options.get('listening',{}).get('barge_in',False))
        self.prefetch_active=prefetch
        prepared:queue.Queue[tuple[str,bytes|str|None]]=queue.Queue(maxsize=1)
        capacity=threading.Semaphore(1)

        def synthesize(text):
            key = text, settings.provider, settings.voice, settings.speaker, settings.speed, settings.models
            with self.cache_lock:
                audio = self.cache.get(key) if settings.cache and not getattr(worker,"centralized",False) else None
            if audio is None:
                audio, _ = worker.synthesize(text, settings, valid)
                if settings.cache and valid() and not getattr(worker,"centralized",False):
                    with self.cache_lock:self.cache.put(key, audio)
            return audio

        def prepare():
            while valid():
                if not capacity.acquire(timeout=.1):continue
                try:text=pending.get(timeout=.1)
                except queue.Empty:capacity.release();continue
                try:packet=('audio',synthesize(text)) if text is not None else ('done',None)
                except Exception as error:packet=('error',str(error))
                if valid():prepared.put_nowait(packet)
                if packet[0]!='audio':return

        def consume():
            while valid():
                try:
                    if prefetch:
                        try:kind,audio=prepared.get(timeout=.1)
                        except queue.Empty:continue
                        capacity.release()
                        if kind=='error':raise RuntimeError(audio)
                        finished=kind=='done'
                    else:
                        try:text=pending.get(timeout=.1)
                        except queue.Empty:continue
                        finished=text is None
                        audio=None if finished else synthesize(text)
                    if finished:
                        self.delivered.emit((generation, "drained", None));return
                    if valid():
                        self.output.play(audio, settings, valid, lambda: self.delivered.emit((generation, "playing", None)))
                except Exception as error:
                    self.delivered.emit((generation, "error", str(error)))
                    return

        if prefetch:self._thread(prepare)
        self._thread(consume)

    def delta(self, text, *, ready=False):
        if not self.responding:
            return
        if text and not self.first_token:
            self.first_token = time.perf_counter()
            self.measurements["first_token_seconds"] = round(self.first_token - self.response_started, 3)
        self.answer_text += text
        self.answer.emit(self.answer_text)
        if not self.stream_audio:return
        try:
            for sentence in (speech_chunks(text) if ready else self.sentence.feed(text)):
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
            deferred=self.answer_text if not self.stream_audio else ""
            for sentence in self.sentence.feed(deferred, final=True):
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
        self.prefetch_active=False
        self.scheduled.stop()
        self.interruptions.cancel()
        self.input.stop(discard=True)
        self.output.stop()
        self.echo.clear()
        # Keep warmed models when only idle/output audio is being stopped.
        getattr(self.worker,"cancel_pending",self.worker.cancel)()
        self.recording = self.responding = self.voice_next = self.barge_active = False
        self.pending = queue.Queue(maxsize=32)
        if not keep_wake:
            self.wake_enabled = self.armed = False
            self.session_active=False
        self.level.emit(0)
        self.set_state("Gestopt")

    def close(self):
        self.closed = True
        self.set_authorized(False)
        getattr(self.worker,"close",self.worker.cancel)()
        if self.next_worker:getattr(self.next_worker,"close",self.next_worker.cancel)()


    def play_preview(self,audio,volume=None):
        self.stop();self.responding=True
        generation=self.interruptions.generation;settings=self.effective_settings()
        if volume is not None:settings=replace(settings,output_gain=max(0,min(1,volume)))
        self.set_state("Stemvoorbeeld afspelen")
        def play():
            valid=lambda:self.interruptions.valid(generation) and not self.closed
            try:
                self.output.play(audio,settings,valid)
                self.delivered.emit((generation,"preview_done",None))
            except Exception:self.delivered.emit((generation,"error","Stemvoorbeeld afspelen mislukt"))
        self._thread(play)
