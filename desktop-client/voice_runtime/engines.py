# SPDX-License-Identifier: GPL-3.0-or-later
import base64
import ctypes
import gc
import io
import os
import sys
from pathlib import Path
import time
import wave

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"


class SpeechToTextProvider:
    def __init__(self):
        self.model = None
        self.key = None
        self.cuda_device = None
        self.fallback_reason = None

    def unload(self):
        if self.model is not None:
            self.model,self.key=None,None
            gc.collect()

    def select_device(self,requested):
        if requested=='cpu':return 'cpu',False,None
        if self.cuda_device is None:
            try:
                import ctranslate2
                if not ctranslate2.get_cuda_device_count():
                    self.cuda_device='cpu'
                else:
                    # Probe once per helper lifetime; missing native libraries
                    # can abort rather than raise inside CTranslate2 inference.
                    loader=ctypes.WinDLL if sys.platform=='win32' else ctypes.CDLL
                    loader('cublas64_12.dll' if sys.platform=='win32' else 'libcublas.so.12')
                    loader('cudnn64_9.dll' if sys.platform=='win32' else 'libcudnn.so.9')
                    self.cuda_device='cuda'
            except OSError:
                self.cuda_device='cpu';self.fallback_reason='cuda_libraries_missing'
            except RuntimeError:
                self.cuda_device='cpu';self.fallback_reason='cuda_probe_failed'
        reason=self.fallback_reason or ('cuda_device_missing' if requested=='cuda' and self.cuda_device=='cpu' else None)
        return self.cuda_device,bool(reason),reason

    def transcribe(self, request):
        from faster_whisper import WhisperModel
        import numpy as np
        directory = Path(request["models"]) / request.get("model", "whisper-small")
        if not all((directory / name).is_file() for name in ("model.bin", "config.json", "tokenizer.json", "vocabulary.txt")):
            raise ValueError("stt_model_missing")
        device = request.get("device", "auto")
        if device not in ("auto", "cpu", "cuda"):
            raise ValueError("invalid_settings")
        beam=request.get('beam_size',3)
        if type(beam) is not int or not 1<=beam<=5:raise ValueError('invalid_settings')
        text_only=request.get('without_timestamps',False)
        if type(text_only) is not bool:raise ValueError('invalid_settings')
        # Our private protocol is PCM WAV only. Decode without FFmpeg/PyAV API
        # version coupling, then resample Piper's 22.05 kHz test input as needed.
        with wave.open(io.BytesIO(base64.b64decode(request["audio"], validate=True)), "rb") as source:
            rate = source.getframerate()
            if source.getsampwidth() != 2 or source.getnchannels() != 1 or not 8000 <= rate <= 96000 or source.getnframes() > rate * 120:
                raise ValueError("audio_too_long")
            audio = np.frombuffer(source.readframes(source.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        if rate != 16000:
            audio = np.interp(np.arange(int(len(audio) * 16000 / rate)) * rate / 16000, np.arange(len(audio)), audio).astype(np.float32)
        # Short isolated utterances need leading/trailing context; do not cut the
        # first phoneme at Whisper's window boundary. No prompt or canned answer.
        audio = np.concatenate((np.zeros(8000, dtype=np.float32), audio, np.zeros(8000, dtype=np.float32)))
        started = time.perf_counter()
        device,fallback,reason=self.select_device(device)
        try:
            text = self._run(WhisperModel, directory, device, audio,beam,text_only)
        except (RuntimeError, OSError):
            if device != "cuda":
                raise
            self.unload()
            self.cuda_device='cpu';self.fallback_reason=reason='cuda_runtime_error'
            device, fallback = "cpu", True
            text = self._run(WhisperModel, directory, device, audio,beam,text_only)
        return {"text": text, "device": device, "cpu_fallback": fallback,"fallback_reason":reason, "seconds": time.perf_counter() - started}

    def _run(self, factory, directory, device, audio,beam=3,text_only=False):
        key = str(directory), device
        if self.key != key:
            # Release old weights before allocating another model. Python's
            # assignment would otherwise keep both alive while factory runs.
            self.unload()
            self.model = factory(str(directory), device=device, compute_type="int8" if device == "cpu" else "float16",
                                 cpu_threads=4, num_workers=1, local_files_only=True)
            self.key = key
        segments, _ = self.model.transcribe(audio, language="nl", beam_size=beam, vad_filter=True,
                                            without_timestamps=text_only,
                                            condition_on_previous_text=False,
                                            vad_parameters={"min_silence_duration_ms": 500})
        return " ".join(segment.text.strip() for segment in segments if segment.no_speech_prob < 0.75).strip()[:8000]


class PiperProvider:
    def __init__(self):
        self.voice, self.key = None, None

    def synthesize(self, request):
        from piper import PiperVoice, SynthesisConfig
        voice_name = request.get("voice", "ronnie")
        if voice_name not in ("ronnie", "mls"):
            raise ValueError("invalid_settings")
        model = Path(request["models"]) / ("piper-ronnie/nl_NL-ronnie-medium.onnx" if voice_name == "ronnie" else "piper/nl_NL-mls-medium.onnx")
        if not model.is_file() or not model.with_suffix(".onnx.json").is_file():
            raise ValueError("tts_model_missing")
        if request.get("provider", "piper") != "piper":
            raise ValueError("tts_provider_unavailable")
        started = time.perf_counter()
        if self.key != str(model):
            self.voice = PiperVoice.load(str(model), use_cuda=False)
            self.key = str(model)
        text = request["text"].strip()
        if not text or len(text) > 700:
            raise ValueError("invalid_text")
        speed = min(1.5, max(0.7, float(request.get("speed", 1.0))))
        speaker = min(51, max(0, int(request.get("speaker", 0)))) if voice_name == "mls" else 0
        data = io.BytesIO()
        with wave.open(data, "wb") as output:
            self.voice.synthesize_wav(text, output, syn_config=SynthesisConfig(speaker_id=speaker, length_scale=1 / speed))
        return {"audio": base64.b64encode(data.getvalue()).decode("ascii"), "provider": "piper",
                "voice":voice_name,"device":"cpu","seconds": time.perf_counter() - started}


class SupertonicProvider:
    def __init__(self):self.model=None;self.key=None;self.styles={}

    def synthesize(self,request):
        import numpy as np
        import onnxruntime as ort
        from voice_runtime.supertonic_helper import load_cfgs,load_onnx_all,load_text_processor,TextToSpeech,load_voice_style
        root=Path(request["models"])/"supertonic-3";voice=request.get("supertonic_voice","M1")
        if voice not in ("M1","M2","M3","M4","M5"):raise ValueError("invalid_settings")
        required=[root/"onnx"/name for name in ("duration_predictor.onnx","text_encoder.onnx","vector_estimator.onnx","vocoder.onnx","tts.json","unicode_indexer.json")]+[root/"voice_styles"/(voice+".json")]
        if not all(path.is_file() for path in required):raise ValueError("tts_model_missing")
        text=request["text"].strip()
        if not text or len(text)>700:raise ValueError("invalid_text")
        started=time.perf_counter()
        if self.key!=str(root):
            options=ort.SessionOptions();options.intra_op_num_threads=4;options.inter_op_num_threads=1
            providers=["CPUExecutionProvider"]
            sessions=load_onnx_all(str(root/"onnx"),options,providers)
            self.model=TextToSpeech(load_cfgs(str(root/"onnx")),load_text_processor(str(root/"onnx")),*sessions)
            self.key=str(root);self.styles={}
        if voice not in self.styles:self.styles[voice]=load_voice_style([str(root/"voice_styles"/(voice+".json"))])
        speed=min(1.5,max(.7,float(request.get("speed",.95))))
        steps=min(12,max(2,int(request.get("steps",8))))
        audio,duration=self.model(text,"nl",self.styles[voice],steps,speed=speed,silence_duration=min(1,max(0,float(request.get("pause_ms",180))/1000)))
        samples=np.asarray(audio).reshape(-1)[:int(float(duration[0])*self.model.sample_rate)]
        if len(samples)>self.model.sample_rate*90 or not np.isfinite(samples).all():raise ValueError("invalid_text")
        data=io.BytesIO()
        with wave.open(data,"wb") as output:
            output.setnchannels(1);output.setsampwidth(2);output.setframerate(self.model.sample_rate)
            output.writeframes((np.clip(samples,-1,1)*32767).astype('<i2').tobytes())
        return {"audio":base64.b64encode(data.getvalue()).decode("ascii"),"provider":"supertonic","voice":voice,"device":"cpu","seconds":time.perf_counter()-started}


class TextToSpeechProvider:
    """One loaded TTS provider at a time in the existing isolated helper."""
    def __init__(self):self.provider=None;self.engine=None

    def synthesize(self,request):
        provider=request.get("provider","piper")
        if provider not in ("piper","supertonic"):raise ValueError("tts_provider_unavailable")
        if self.provider!=provider:
            self.engine=None
            import gc
            gc.collect()
            self.engine=PiperProvider() if provider=="piper" else SupertonicProvider();self.provider=provider
        return self.engine.synthesize(request)


class Runtime:
    def __init__(self):
        self.stt, self.tts = SpeechToTextProvider(), TextToSpeechProvider()

    def dispatch(self, request):
        if request.get('operation') not in ('stt','tts'):raise ValueError('invalid_operation')
        if request.get("profile") == "light":
            # One large inference engine at a time on a future constrained host.
            if request["operation"] == "stt":
                if self.tts.engine is not None:
                    self.tts = TextToSpeechProvider()
                    gc.collect()
            else:
                self.stt.unload()
        if request["operation"] == "stt":
            return self.stt.transcribe(request)
        if request["operation"] == "tts":
            return self.tts.synthesize(request)
        raise ValueError("invalid_operation")
