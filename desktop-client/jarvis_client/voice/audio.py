import io
import queue
import threading
import time
import wave

import numpy as np
import sounddevice as sd

from jarvis_client.voice.processing import VoiceActivityDetector


class AudioError(Exception):
    pass


class AudioDeviceManager:
    def devices(self):
        try:
            return [(index, item["name"], item["max_input_channels"] > 0, item["max_output_channels"] > 0)
                    for index, item in enumerate(sd.query_devices())]
        except Exception:
            raise AudioError("Audioapparaten niet beschikbaar. Controleer Windows-geluid en de aangesloten apparaten.") from None


class AudioInputManager:
    def __init__(self):
        self.finish, self.cancelled = threading.Event(), threading.Event()

    def prepare(self):
        self.finish.clear()
        self.cancelled.clear()

    def stop(self, discard=False):
        self.cancelled.set() if discard else self.finish.set()

    def capture(self, settings, *, consent, timeout=6, activity=None, preprocess=None,turns=None):
        if not consent:
            raise AudioError("Geef eerst in het spraakpaneel toestemming voor de microfoon.")
        blocks:queue.Queue[bytes] = queue.Queue(maxsize=12)
        overflow = threading.Event()

        def callback(data, frames, timing, status):
            if status:
                overflow.set()
            try:
                blocks.put_nowait(bytes(data))
            except queue.Full:
                overflow.set()

        detector = VoiceActivityDetector(settings.sensitivity, settings.silence_seconds, settings.max_seconds, timeout)
        self.transcription=None
        audio = bytearray()
        try:
            device = None if settings.input_device == -1 else settings.input_device
            with sd.RawInputStream(device=device, samplerate=16000, channels=1, dtype="int16", blocksize=480, callback=callback):
                while not self.cancelled.is_set() and not self.finish.is_set():
                    try:
                        block = blocks.get(timeout=0.1)
                    except queue.Empty:
                        if overflow.is_set():
                            raise AudioError("Microfoonstream onderbroken. Kies het apparaat opnieuw.")
                        # A disconnected driver must not leave an endless capture.
                        detector.elapsed += 0.1
                        if detector.elapsed > settings.max_seconds:
                            raise AudioError("Geen audio ontvangen van de microfoon.")
                        continue
                    samples = np.frombuffer(block, dtype=np.int16).astype(np.float32) * settings.input_gain
                    samples = np.clip(samples, -32768, 32767).astype(np.int16)
                    if preprocess:samples=preprocess(samples)
                    audio.extend(samples.tobytes())
                    rms = float(np.sqrt(np.mean((samples.astype(np.float32) / 32768) ** 2)))
                    outcome = detector.feed(rms, len(samples) / 16000)
                    if turns:
                        if rms>=detector.threshold:turns.voiced()
                        if detector.speech>=.21:
                            turns.probe(audio,detector.quiet)
                            if turns.finished(detector.quiet):outcome="finish"
                    if activity:
                        activity(rms, rms >= detector.threshold)
                    if overflow.is_set():
                        raise AudioError("Microfoonstream overbelast of onderbroken; opname gestopt.")
                    if outcome in ("finish", "empty"):
                        break
            if self.cancelled.is_set() or detector.speech < 0.21:
                return b""
            result = io.BytesIO()
            with wave.open(result, "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(16000)
                output.writeframes(audio)
            if turns:self.transcription=turns.finish()
            return result.getvalue()
        except AudioError:
            raise
        except Exception:
            raise AudioError("Microfoon niet beschikbaar: controleer aansluiting, Windows-toestemming en of een andere app hem bezet houdt.") from None
        finally:
            audio.clear()


class AudioOutputManager:
    def __init__(self):
        self.cancelled = threading.Event()
        self.stream = None
        self.lock = threading.RLock()
        self.paused=threading.Event()
        self.reference=None
        self.playback_lock=threading.Lock()

    def pause(self):self.paused.set()

    def resume(self):self.paused.clear()

    def stop(self):
        self.cancelled.set()
        self.paused.clear()
        with self.lock:
            stream = self.stream
        if stream:
            try:
                stream.abort()
            except Exception:
                pass

    def play(self, data, settings, valid=lambda: True, on_started=lambda: None):
        with self.playback_lock:
            if valid():self._play(data,settings,valid,on_started)

    def _play(self,data,settings,valid,on_started):
        self.cancelled.clear()
        try:
            with wave.open(io.BytesIO(data), "rb") as source:
                if source.getsampwidth() != 2 or source.getnchannels() != 1 or source.getnframes() > source.getframerate() * 180:
                    raise AudioError("Ongeldig audioformaat.")
                if not valid():
                    return
                device = None if settings.output_device == -1 else settings.output_device
                with sd.RawOutputStream(device=device, samplerate=source.getframerate(), channels=1, dtype="int16") as stream:
                    with self.lock:
                        self.stream = stream
                    if self.cancelled.is_set() or not valid():
                        return
                    started=False
                    while not self.cancelled.is_set() and valid():
                        while self.paused.is_set() and not self.cancelled.is_set() and valid():time.sleep(.01)
                        if self.cancelled.is_set() or not valid():break
                        block = source.readframes(max(1, source.getframerate() // 50))
                        if not block:
                            break
                        samples = np.frombuffer(block, dtype=np.int16).astype(np.float32) * settings.output_gain
                        pcm=np.clip(samples, -32768, 32767).astype(np.int16).tobytes()
                        if self.reference:self.reference.feed(pcm,source.getframerate())
                        stream.write(pcm)
                        if not started:started=True;on_started()
        except Exception:
            if not self.cancelled.is_set() and valid():
                raise AudioError("Luidspreker niet beschikbaar of audio onderbroken. Kies de uitvoer opnieuw.") from None
        finally:
            with self.lock:
                self.stream = None
