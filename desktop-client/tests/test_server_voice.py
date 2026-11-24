import asyncio
import json
import threading
import time

import httpx
import pytest

from jarvis_client.api import ApiClient,ClientError
from jarvis_client.voice.server_worker import ServerInferenceWorker
from jarvis_client.voice.settings import VoiceSettings
from test_voice import wav_bytes


class Api:
    origin="http://127.0.0.1:8765"
    _decode=staticmethod(ApiClient._decode)
    def __init__(self):self.forgotten=False
    def headers(self):return {"Authorization":"Bearer synthetic-not-a-real-credential"}
    def forget(self):self.forgotten=True


def cleanup(worker):
    worker.close()
    for thread in worker.cleanup_threads:thread.join(7)


def test_server_worker_reuses_authenticated_transport_without_local_models():
    calls=[];created=[];main=threading.get_ident()
    async def handler(request):
        calls.append((request,threading.get_ident()))
        assert request.headers["Authorization"]=="Bearer synthetic-not-a-real-credential"
        if request.url.path.endswith("transcribe"):
            assert request.content==wav_bytes()
            return httpx.Response(200,json={"text":"Een synthetische transcriptie","seconds":.01})
        assert json.loads(request.content)["speed"]==1.2
        return httpx.Response(200,content=wav_bytes(),headers={"Content-Type":"audio/wav"})
    def factory(**kwargs):created.append(kwargs);return httpx.AsyncClient(transport=httpx.MockTransport(handler),**kwargs)
    worker=ServerInferenceWorker(Api(),client_factory=factory)
    try:
        settings=VoiceSettings(speed=1.2)
        assert worker.transcribe(wav_bytes(),settings,lambda:True)["text"]=="Een synthetische transcriptie"
        assert worker.synthesize("Een synthetische zin.",settings,lambda:True)[0]==wav_bytes()
        assert len(created)==1 and created[0]["verify"] and not created[0]["trust_env"]
        assert all(thread!=main for _,thread in calls)
    finally:cleanup(worker)


def test_cancel_rejects_late_result_and_allows_next_voice_turn():
    entered=threading.Event();stopped=threading.Event();replies=[];count=[0]
    async def handler(request):
        count[0]+=1
        if count[0]==1:
            entered.set()
            try:await asyncio.Event().wait()
            except asyncio.CancelledError:stopped.set();raise
        return httpx.Response(200,json={"text":"Nieuw resultaat","seconds":.01})
    worker=ServerInferenceWorker(Api(),client_factory=lambda **kwargs:httpx.AsyncClient(transport=httpx.MockTransport(handler),**kwargs))
    def request():
        try:replies.append(worker.transcribe(wav_bytes(),VoiceSettings(),lambda:True))
        except RuntimeError:replies.append("cancelled")
    thread=threading.Thread(target=request);thread.start()
    try:
        assert entered.wait(2);worker.cancel();thread.join(2)
        assert not thread.is_alive() and stopped.wait(2) and replies==["cancelled"]
        assert worker.transcribe(wav_bytes(),VoiceSettings(),lambda:True)["text"]=="Nieuw resultaat"
    finally:cleanup(worker)


def test_voice_auth_failure_forgets_credential_and_never_returns_body():
    api=Api()
    async def handler(_):return httpx.Response(401,json={"private":"Never display this response body"})
    worker=ServerInferenceWorker(api,client_factory=lambda **kwargs:httpx.AsyncClient(transport=httpx.MockTransport(handler),**kwargs))
    try:
        with pytest.raises(ClientError) as error:worker.transcribe(wav_bytes(),VoiceSettings(),lambda:True)
        assert api.forgotten and error.value.status==401 and "private" not in str(error.value)
    finally:cleanup(worker)
