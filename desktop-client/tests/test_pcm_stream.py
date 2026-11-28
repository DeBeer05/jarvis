from types import SimpleNamespace

from jarvis_client.voice.audio import AudioOutputManager


def test_pcm_playback_starts_before_final_chunk_and_obeys_interrupt(monkeypatch):
    writes=[];started=[];valid=[True]
    class Stream:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def write(self,pcm):writes.append(pcm)
    monkeypatch.setattr('jarvis_client.voice.audio.sd.RawOutputStream',Stream)
    def chunks():
        yield b'\0'*960
        assert writes and started
        valid[0]=False
        yield b'\1'*960
    AudioOutputManager().play_pcm(chunks(),24000,SimpleNamespace(output_device=-1,output_gain=1.),lambda:valid[0],lambda:started.append(True))
    assert sum(map(len,writes))==960 and len(started)==1
