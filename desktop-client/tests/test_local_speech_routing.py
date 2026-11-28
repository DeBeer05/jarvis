from types import SimpleNamespace
import pytest

from jarvis_client.voice.server_worker import ServerInferenceWorker


def test_available_local_speech_does_not_require_a_cloud_connection():
    calls=[]
    class Local:
        def transcribe(self,*args):calls.append('local');return {'text':'Morgen.','device':'cpu','seconds':.1}
        def cancel_pending(self):calls.append('cancel_pending')
        def cancel(self):calls.append('cancel')
    worker=ServerInferenceWorker(SimpleNamespace(),prefer_local_stt=True,local_factory=Local)
    worker.request=lambda *args,**kwargs:(_ for _ in ()).throw(AssertionError('No network for available local speech'))
    settings=SimpleNamespace(model='whisper-small')
    result=worker.transcribe(b'wav',settings,lambda:True)
    assert result['location']=='windows_local' and result['text']=='Morgen.'
    worker.cancel_pending();assert calls==['local','cancel_pending']
    worker.close()


def test_explicit_windows_only_never_uploads_audio_when_unavailable():
    class Local:
        def transcribe(self,*args):raise RuntimeError('missing runtime')
        def cancel_pending(self):pass
        def cancel(self):pass
    worker=ServerInferenceWorker(SimpleNamespace(),prefer_local_stt=True,local_only=True,local_factory=Local)
    worker.request=lambda *args,**kwargs:pytest.fail('No upload after explicit local-only selection')
    with pytest.raises(RuntimeError,match='geen microfoonaudio'):
        worker.transcribe(b'wav',SimpleNamespace(model='whisper-small'),lambda:True)
    worker.close()


def test_missing_local_runtime_falls_back_to_authenticated_server_once():
    class Local:
        def transcribe(self,*args):raise RuntimeError('missing runtime')
        def cancel_pending(self):pass
        def cancel(self):pass
    worker=ServerInferenceWorker(SimpleNamespace(),prefer_local_stt=True,local_factory=Local)
    calls=[]
    def request(*args,**kwargs):calls.append('server');return b'{"text":"Morgen.","seconds":0.2}'
    worker.request=request
    settings=SimpleNamespace(model='whisper-small')
    assert worker.transcribe(b'wav',settings,lambda:True)['device']=='server'
    assert worker.transcribe(b'wav',settings,lambda:True)['device']=='server'
    assert calls==['server','server']
    worker.close()
