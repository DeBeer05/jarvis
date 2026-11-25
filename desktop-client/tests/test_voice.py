import io
import json
from pathlib import Path
import threading
import time
import wave

import numpy as np
import pytest

from jarvis_client.voice import audio
from jarvis_client.voice.manager import VoiceConversationManager
from jarvis_client.voice.processing import AudioCache, InterruptionController, SentenceBuffer, VoiceActivityDetector, WakeWordEngine
from jarvis_client.voice.settings import VoiceSettings, VoiceSettingsManager, installed_stt_models
from jarvis_client.voice.worker import InferenceWorker
from test_window import window


def until(qt, predicate, seconds=3):
    deadline = time.monotonic() + seconds
    while not predicate() and time.monotonic() < deadline:
        qt.processEvents()
        time.sleep(.005)
    qt.processEvents()
    assert predicate()


def wav_bytes(seconds=.2):
    data = io.BytesIO()
    with wave.open(data, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(16000)
        stream.writeframes(np.zeros(int(seconds * 16000), dtype=np.int16).tobytes())
    return data.getvalue()


@pytest.mark.parametrize("bad", [{"speed": 5}, {"device": "remote"}, {"provider": "xtts"}, {"followup_seconds": 90}, {"model": "http://untrusted"}, {"ptt_shortcut": "Ctrl+Shift+Space"}])
def test_settings_reject_unsupported_or_unbounded_values(bad):
    with pytest.raises(ValueError):
        VoiceSettings(**bad).validate()


def test_settings_roundtrip_no_audio_consent_or_secrets(tmp_path):
    store = VoiceSettingsManager(tmp_path)
    settings = VoiceSettings(speaker=7, speed=1.15, input_device=2, device="cpu")
    store.save(settings)
    assert store.load() == settings
    assert not any(word in store.path.read_text() for word in ("password", "token", "consent", "transcript"))
    store.path.write_text('{"speed":"invalid"}')
    assert store.load() == VoiceSettings()


def test_vad_silence_noise_and_end_of_utterance():
    detector = VoiceActivityDetector(silence=.5)
    assert all(detector.feed(.001, .03) == "continue" for _ in range(50))
    assert detector.speech == 0
    assert detector.feed(0, 6) == "empty"
    detector = VoiceActivityDetector(silence=.5)
    assert detector.feed(.1, .5) == "continue"
    assert detector.feed(.001, .6) == "finish"
    detector = VoiceActivityDetector(maximum=1)
    assert detector.feed(.1, 1) == "finish"


@pytest.mark.parametrize("text,command", [("Hé JARVIS, hoeveel is zeven plus vijf?", "hoeveel is zeven plus vijf?"), ("Hey Jarvis", ""), ("Hé, Jarvis. Vertel over België.", "Vertel over België.")])
def test_dutch_phrase_gate(text, command):
    assert WakeWordEngine().detect(text) == (True, command)


@pytest.mark.parametrize("text", ["Ik las over Jarvis", "Jarvis is mijn naam", "Helemaal niet Jarvis", ""])
def test_wake_does_not_trigger_on_mentions(text):
    assert WakeWordEngine().detect(text) == (False, "")


def test_sentence_stream_and_cache_are_bounded():
    buffer = SentenceBuffer()
    assert buffer.feed("Dit is een hal") == []
    assert buffer.feed("ve zin. Volgende") == ["Dit is een halve zin."]
    assert buffer.feed("", final=True) == ["Volgende"]
    assert buffer.feed("Het is 3.") == []
    assert buffer.feed("14 euro. Nog iets") == ["Het is 3.14 euro."]
    cache = AudioCache(maximum=5)
    cache.put("first", b"123")
    cache.put("second", b"456")
    assert cache.get("first") is None and cache.get("second") == b"456"
    cache.put("large", b"123456")
    assert cache.size <= 5
    cache.clear()
    assert cache.size == 0
    controller = InterruptionController()
    generation = controller.generation
    controller.cancel()
    assert not controller.valid(generation)


def test_no_microphone_without_explicit_consent(monkeypatch):
    monkeypatch.setattr(audio.sd, "RawInputStream", lambda **kwargs: pytest.fail("Microphone opened"))
    with pytest.raises(audio.AudioError, match="toestemming"):
        audio.AudioInputManager().capture(VoiceSettings(), consent=False)


@pytest.mark.parametrize("reason", ["device missing", "busy", "permission denied", "unplugged"])
def test_capture_driver_errors_are_safe(monkeypatch, reason):
    def unavailable(**kwargs):
        raise OSError(reason)
    monkeypatch.setattr(audio.sd, "RawInputStream", unavailable)
    with pytest.raises(audio.AudioError, match="Microfoon niet beschikbaar"):
        audio.AudioInputManager().capture(VoiceSettings(), consent=True)


def test_capture_pcm_silence_stop_and_memory_only(monkeypatch, tmp_path):
    class Stream:
        def __init__(self, **kwargs):
            self.callback = kwargs["callback"]
        def __enter__(self):
            def feed():
                for level in [2000] * 10 + [0] * 45:
                    self.callback(np.full(480, level, dtype=np.int16).tobytes(), 480, None, False)
                    time.sleep(.003)
            self.thread = threading.Thread(target=feed)
            self.thread.start()
            return self
        def __exit__(self, *args):
            self.thread.join()
    monkeypatch.setattr(audio.sd, "RawInputStream", Stream)
    result = audio.AudioInputManager().capture(VoiceSettings(), consent=True)
    assert result.startswith(b"RIFF") and len(result) < 4 * 1024 * 1024
    assert not list(tmp_path.iterdir())


def test_output_failure_and_immediate_stop(monkeypatch):
    output = audio.AudioOutputManager()
    writes = []
    class Stream:
        def __init__(self, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def write(self, data):
            writes.append(data)
            output.stop()
        def abort(self):
            pass
    monkeypatch.setattr(audio.sd, "RawOutputStream", Stream)
    output.play(wav_bytes(5), VoiceSettings())
    assert len(writes) == 1
    def missing(**kwargs):
        raise OSError("private driver details")
    monkeypatch.setattr(audio.sd, "RawOutputStream", missing)
    with pytest.raises(audio.AudioError, match="Luidspreker"):
        output.play(wav_bytes(), VoiceSettings())
    output.play(wav_bytes(), VoiceSettings(), valid=lambda: False)


def test_device_enumeration_failure_no_recording(monkeypatch):
    monkeypatch.setattr(audio.sd, "query_devices", lambda: [{"name": "Test", "max_input_channels": 1, "max_output_channels": 0}])
    assert audio.AudioDeviceManager().devices() == [(0, "Test", True, False)]
    def unavailable():
        raise OSError("error")
    monkeypatch.setattr(audio.sd, "query_devices", unavailable)
    with pytest.raises(audio.AudioError):
        audio.AudioDeviceManager().devices()


class FakeInput:
    def prepare(self):
        pass
    def stop(self, discard=False):
        pass
    def capture(self, settings, **kwargs):
        return b"synthetic"


class FakeOutput:
    def __init__(self):
        self.played = []
    def stop(self):
        pass
    def play(self, data, settings, valid, on_started):
        if valid():
            on_started()
            self.played.append(data)


class FakeWorker:
    def __init__(self):
        self.calls = []
    def cancel(self):
        pass
    def transcribe(self, audio, settings, valid):
        self.calls.append("stt")
        return {"text": "Hoe heet je?", "seconds": .1, "device": "cpu"}
    def synthesize(self, text, settings, valid):
        self.calls.append(text)
        return text.encode(), {"seconds": .1}


def manager(qt):
    return VoiceConversationManager(VoiceSettings(), worker=FakeWorker(), audio_input=FakeInput(), audio_output=FakeOutput())


def test_ptt_auth_consent_transcript_stream_playback_and_followup(qt):
    voice = manager(qt)
    errors, texts, metrics, states = [], [], [], []
    voice.problem.connect(errors.append)
    voice.ready_text.connect(texts.append)
    voice.metrics.connect(metrics.append)
    voice.changed.connect(states.append)
    voice.toggle_recording()
    assert errors and not voice.worker.calls
    voice.set_authorized(True)
    voice.set_consent(True)
    voice.toggle_recording()
    until(qt, lambda: bool(texts))
    assert texts == ["Hoe heet je?"] and voice.voice_next
    voice.begin_response()
    voice.delta("Ik ben JAR")
    assert voice.output.played == []
    voice.delta("VIS. Aangenaam!")
    voice.finish_response()
    until(qt, lambda: bool(metrics))
    assert voice.output.played == [b"Ik ben JARVIS.", b"Aangenaam!"]
    assert metrics[0]["first_token_seconds"] >= 0 and metrics[0]["first_audio_seconds"] >= 0
    assert any("Ik luister" in state for state in states)
    voice.set_authorized(False)
    assert not voice.consent and not voice.cache.items
    voice.close()


def test_cancel_discards_late_tts_and_shutdown_stops_capture(qt):
    voice = manager(qt)
    entered, release = threading.Event(), threading.Event()
    def slow(text, settings, valid):
        entered.set()
        release.wait(2)
        return b"stale", {}
    voice.worker.synthesize = slow
    voice.voice_next = True
    voice.begin_response()
    voice.delta("Oud antwoord. ")
    until(qt, entered.is_set)
    voice.stop()
    release.set()
    until(qt, lambda: not voice.busy)
    assert voice.output.played == []
    voice.close()
    assert voice.closed and not voice.consent


def test_ready_server_clause_does_not_wait_for_another_sentence(qt):
    voice=manager(qt);voice.voice_next=True;voice.begin_response()
    clause='Na een lange werkdag helpt een rustige wandeling om wat afstand te nemen, '
    voice.delta(clause,ready=True)
    until(qt,lambda:bool(voice.output.played))
    assert voice.output.played==[clause.strip().encode()]
    voice.finish_response();until(qt,lambda:not voice.responding);voice.close()


@pytest.mark.parametrize('barge',[False,True])
def test_speech_prefetch_is_one_block_ahead_and_stop_discards_it(qt,barge):
    voice=manager(qt)
    voice.options={'conversations':{'enabled':False},'listening':{'barge_in':barge}}
    started,release=threading.Event(),threading.Event()
    class Output(FakeOutput):
        def play(self,data,settings,valid,on_started):
            if valid():
                self.played.append(data);on_started()
                if len(self.played)==1:started.set();release.wait(3)
    voice.output=Output();voice.voice_next=True;voice.begin_response()
    try:
        for text in ('Eerste zin.','Tweede zin.','Derde zin.'):voice.delta(text,ready=True)
        voice.finish_response();until(qt,started.is_set)
        if barge:
            time.sleep(.05);assert len(voice.worker.calls)==1
        else:
            until(qt,lambda:len(voice.worker.calls)==2)
            time.sleep(.05);assert len(voice.worker.calls)==2
        voice.stop();release.set();until(qt,lambda:not voice.busy)
        assert voice.output.played==[b'Eerste zin.']
    finally:release.set();voice.close()


def test_missing_models_and_offline_error_never_leaks_raw_error(qt):
    voice = manager(qt)
    errors = []
    voice.problem.connect(errors.append)
    def unavailable(*args):
        raise RuntimeError("Spraakmodel ontbreekt.")
    voice.worker.transcribe = unavailable
    voice.set_authorized(True)
    voice.set_consent(True)
    voice.start_recording()
    until(qt, lambda: bool(errors))
    assert "ontbreekt" in errors[0] and not voice.recording
    voice.close()


def test_voice_page_stays_in_existing_window_and_auth_boundary(qt, tmp_path, vault):
    app = window(tmp_path, vault)
    app.navigate(6)
    assert app.pages.currentWidget() is app.voice_panel
    assert not app.voice_panel.consent.isChecked() and not app.voice_panel.global_keys.isChecked()
    app.voice_message("Niet versturen zonder sessie")
    assert not app.running and "Log opnieuw in" in app.notice.text()
    app.voice_panel.fields["speaker"].setValue(7)
    app.voice_panel.save()
    assert VoiceSettingsManager(tmp_path).load().speaker == 7
    assert not app.voice.busy
    app.voice_panel.close_voice()
    app.closing = True
    app.tray.hide()
    app.close()


def test_microphone_permission_and_device_survive_restart(qt, tmp_path, vault):
    app = window(tmp_path, vault)
    panel = app.voice_panel
    panel.consent.setChecked(True)
    panel.inputs.addItem("Synthetic USB microphone", 4)
    panel.inputs.setCurrentIndex(1)
    panel.inputs.activated.emit(1)
    saved = VoiceSettingsManager(tmp_path).load()
    assert saved.microphone_allowed and saved.input_device == 4
    assert not app.voice.authorized and not app.voice.recording
    panel.close_voice()
    app.closing = True
    app.tray.hide()
    app.close()
    reopened = window(tmp_path, vault)
    assert reopened.voice_panel.consent.isChecked()
    assert reopened.voice_panel.inputs.currentData() == 4
    assert not reopened.voice.recording and not reopened.voice.consent
    reopened.manager.state = "online"
    reopened.principal = {"permissions": ["chat:write"]}
    reopened.update_controls()
    assert reopened.voice.consent and not reopened.voice.recording
    reopened.voice_panel.consent.setChecked(False)
    assert not VoiceSettingsManager(tmp_path).load().microphone_allowed and not reopened.voice.consent
    reopened.voice_panel.close_voice()
    reopened.closing = True
    reopened.tray.hide()
    reopened.close()


def test_live_microphone_feedback_and_stop_clear_meter(qt, tmp_path, vault):
    app = window(tmp_path, vault)
    voice, panel = app.voice, app.voice_panel
    voice.authorized, voice.consent, voice.recording = True, True, True
    voice._delivered((voice.interruptions.generation, "activity", (.1, True, False)))
    assert panel.status.text() == "Ik hoor je…" and panel.level.value() == 80
    assert "Microfoon actief" in panel.microphone_status.text()
    assert panel.ptt.text() == "■  Opname afronden"
    voice.stop()
    assert panel.level.value() == 0 and "Microfoon uit" in panel.microphone_status.text()
    panel.close_voice()
    app.closing = True
    app.tray.hide()
    app.close()


def test_missing_tiny_disabled_and_repaired_to_installed_small(qt, tmp_path, vault):
    models = tmp_path / "models"
    model = models / "whisper-small"
    model.mkdir(parents=True)
    for name in ("model.bin", "config.json", "tokenizer.json", "vocabulary.txt"):
        (model / name).write_bytes(b"synthetic")
    store = VoiceSettingsManager(tmp_path)
    store.save(VoiceSettings(models=str(models), model="whisper-tiny"))
    app = window(tmp_path, vault)
    assert app.voice.settings.model == "whisper-small"
    assert store.load().model == "whisper-small"
    choice = app.voice_panel.choices["model"]
    assert not choice.model().item(choice.findData("whisper-tiny")).isEnabled()
    assert installed_stt_models(app.voice.settings) == {"whisper-small"}
    app.voice_panel.show_problem("Spraakmodel ontbreekt.")
    assert app.voice_panel.error.text() == "Spraakmodel ontbreekt." and not app.voice_panel.error.isHidden()
    app.voice_panel.close_voice()
    app.closing = True
    app.tray.hide()
    app.close()


def test_inference_helper_missing_runtime_fails_without_download(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "is_file", lambda self: False)
    with pytest.raises(RuntimeError, match="runtime ontbreekt"):
        InferenceWorker().resolve_command()


def test_voice_uses_same_authenticated_stream_and_conversation(qt, tmp_path, vault):
    app = window(tmp_path, vault)
    calls = []
    class Api:
        origin = "http://127.0.0.1:8765"
        def stream(self, message, conversation, provider, emit, request_id, **options):
            calls.append((message, conversation, provider))
            emit({"type": "meta", "conversation_id": "same-conversation"})
            emit({"type": "delta", "text": "Ik onthoud de context."})
            emit({"type": "done", "message": "Ik onthoud de context.", "status": "completed"})
    app.manager.api, app.manager.state = Api(), "online"
    app.principal = {"permissions": ["chat:read", "chat:write", "chat:delete"]}
    app.load_history = lambda *args: None
    app.voice.worker, app.voice.output = FakeWorker(), FakeOutput()
    app.update_controls()
    for text in ("Mijn naam is Eva", "Hoe heet ik?", "Wat vroeg ik eerst?"):
        app.voice.voice_next = True
        app.voice_message(text)
        until(qt, lambda: not app.running and not app.voice.responding)
    assert [item[1] for item in calls] == [None, "same-conversation", "same-conversation"]
    assert [row[1] for row in app.rows if row[0] == "JIJ"] == [item[0] for item in calls]
    assert len(app.voice.output.played) == 3
    app.voice_panel.close_voice()
    app.closing = True
    app.tray.hide()
    app.close()


def test_voice_network_failure_restores_ui_without_resend(qt, tmp_path, vault):
    from jarvis_client.api import ClientError
    app = window(tmp_path, vault)
    calls = []
    class Api:
        def stream(self, *args, **options):
            calls.append(1)
            raise ClientError("network", "Server niet bereikbaar.")
    app.manager.api, app.manager.state = Api(), "online"
    app.principal = {"permissions": ["chat:write"]}
    app.voice.worker, app.voice.output = FakeWorker(), FakeOutput()
    app.update_controls()
    app.voice.voice_next = True
    app.voice_message("Een vraag")
    until(qt, lambda: not app.running)
    assert calls == [1] and not app.voice.responding and app.send_button.isEnabled()
    app.voice_panel.close_voice()
    app.closing = True
    app.tray.hide()
    app.close()


@pytest.mark.parametrize("failure", ["dll", "inference"])
def test_whisper_gpu_falls_back_to_local_cpu_without_download(tmp_path, monkeypatch, failure):
    import sys
    from types import SimpleNamespace
    from voice_runtime.engines import SpeechToTextProvider
    from voice_runtime import engines
    directory = tmp_path / "whisper-small"
    directory.mkdir()
    for name in ("model.bin", "config.json", "tokenizer.json", "vocabulary.txt"):
        (directory / name).write_bytes(b"synthetic")
    attempts = []
    def factory(path, **kwargs):
        assert kwargs["local_files_only"]
        attempts.append(kwargs["device"])
        if kwargs["device"] == "cuda":
            raise RuntimeError("CUDA failure")
        return SimpleNamespace(transcribe=lambda *args, **kwargs: ([SimpleNamespace(text="Hallo", no_speech_prob=.1)], None))
    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=factory))
    monkeypatch.setitem(sys.modules, "ctranslate2", SimpleNamespace(get_cuda_device_count=lambda: 1))
    def load(*args):
        if failure == "dll":
            raise OSError("missing CUDA")
        return True
    monkeypatch.setattr(engines.ctypes, "WinDLL" if sys.platform == "win32" else "CDLL", load)
    import base64
    result = SpeechToTextProvider().transcribe({"models": str(tmp_path), "audio": base64.b64encode(wav_bytes()).decode(), "device": "auto"})
    assert result["text"] == "Hallo" and result["device"] == "cpu" and result["cpu_fallback"]
    assert attempts == (["cpu"] if failure == "dll" else ["cuda", "cpu"])
