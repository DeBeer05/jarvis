"""CPU fallback and model lifetime contracts; no installed models or CUDA required."""
import base64
import io
import sys
from types import SimpleNamespace
import wave

import pytest

from voice_runtime import engines


@pytest.fixture
def inference(tmp_path,monkeypatch):
    directory=tmp_path/'whisper-small';directory.mkdir()
    for name in ('model.bin','config.json','tokenizer.json','vocabulary.txt'):(directory/name).write_bytes(b'synthetic')
    audio=io.BytesIO()
    with wave.open(audio,'wb') as output:
        output.setnchannels(1);output.setsampwidth(2);output.setframerate(16000);output.writeframes(b'\0\0'*1600)
    request={'models':str(tmp_path),'audio':base64.b64encode(audio.getvalue()).decode(),'device':'auto'}
    attempts=[];probes=[];loads=[];options=[]
    def transcribe(*args,**kwargs):
        options.append(kwargs)
        return [SimpleNamespace(text='Nee, annuleer dat voorstel.',no_speech_prob=.1)],None
    def factory(*args,**kwargs):
        attempts.append(kwargs['device'])
        return SimpleNamespace(transcribe=transcribe)
    def probe():probes.append(True);return 1
    def dll(*args):loads.append(True);raise OSError('private native path')
    monkeypatch.setitem(sys.modules,'faster_whisper',SimpleNamespace(WhisperModel=factory))
    monkeypatch.setitem(sys.modules,'ctranslate2',SimpleNamespace(get_cuda_device_count=probe))
    monkeypatch.setattr(engines.ctypes,'WinDLL' if sys.platform=='win32' else 'CDLL',dll)
    return request,attempts,probes,loads,options


def test_missing_cuda_is_probed_once_and_cpu_model_stays_warm(inference):
    request,attempts,probes,loads,options=inference;provider=engines.SpeechToTextProvider()
    results=[provider.transcribe(request) for _ in range(3)]
    assert attempts==['cpu'] and len(probes)==len(loads)==1
    assert all(r['device']=='cpu' and r['cpu_fallback'] and r['fallback_reason']=='cuda_libraries_missing' for r in results)
    assert all(option['beam_size']==5 for option in options)


def test_explicit_cpu_does_not_touch_cuda(inference):
    request,attempts,probes,loads,_=inference
    result=engines.SpeechToTextProvider().transcribe({**request,'device':'cpu'})
    assert result['device']=='cpu' and not result['cpu_fallback'] and not probes and not loads
    assert attempts==['cpu']


def test_dutch_transcription_preserves_boundary_speech_without_translation(inference):
    request,attempts,probes,loads,options=inference
    engines.SpeechToTextProvider().transcribe({**request,'device':'cpu'})
    decoding=options[0]
    assert decoding['language']=='nl' and decoding['task']=='transcribe'
    assert decoding['temperature']==0 and not decoding['condition_on_previous_text']
    assert 'morgen, vanmorgen, overmorgen' in decoding['initial_prompt']
    assert decoding['vad_parameters']['speech_pad_ms']>=400
    assert decoding['vad_parameters']['threshold']<=.5


def test_light_profile_keeps_small_beam_for_constrained_hosts(inference):
    request,attempts,probes,loads,options=inference
    engines.SpeechToTextProvider().transcribe({**request,'device':'cpu','profile':'light'})
    assert options[0]['beam_size']==3


def test_gpu_inference_failure_is_not_retried_every_utterance(inference,monkeypatch):
    request,attempts,_,_,_=inference
    monkeypatch.setattr(engines.ctypes,'WinDLL' if sys.platform=='win32' else 'CDLL',lambda *_:True)
    def factory(*args,**kwargs):
        attempts.append(kwargs['device'])
        if kwargs['device']=='cuda':raise RuntimeError('private CUDA error')
        return SimpleNamespace(transcribe=lambda *a,**k:([SimpleNamespace(text='Hallo',no_speech_prob=.1)],None))
    monkeypatch.setitem(sys.modules,'faster_whisper',SimpleNamespace(WhisperModel=factory))
    provider=engines.SpeechToTextProvider()
    for _ in range(3):assert provider.transcribe(request)['device']=='cpu'
    assert attempts==['cuda','cpu']


def test_light_unloads_weights_but_keeps_device_fallback_cache(inference):
    request,attempts,probes,loads,_=inference;runtime=engines.Runtime()
    first=runtime.dispatch({**request,'operation':'stt','profile':'light'})
    assert first['text']
    runtime.tts.synthesize=lambda _: {'audio':'synthetic'}
    runtime.dispatch({'operation':'tts','profile':'light'})
    assert runtime.stt.model is None
    runtime.dispatch({**request,'operation':'stt','profile':'light'})
    assert attempts==['cpu','cpu'] and len(probes)==len(loads)==1


def test_model_switch_releases_old_weights_before_allocating_new(inference,monkeypatch):
    request,_,_,_,_=inference;provider=engines.SpeechToTextProvider()
    provider.transcribe({**request,'device':'cpu'})
    def factory(*args,**kwargs):
        assert provider.model is None
        return SimpleNamespace(transcribe=lambda *a,**k:([SimpleNamespace(text='Hallo',no_speech_prob=.1)],None))
    monkeypatch.setitem(sys.modules,'faster_whisper',SimpleNamespace(WhisperModel=factory))
    provider.key=('previous-model','cpu')
    provider.transcribe({**request,'device':'cpu'})
