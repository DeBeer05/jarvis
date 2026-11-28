import hashlib

import pytest

from jarvis_client.voice.progress import ProgressClip,cached


def test_cached_recording_never_downloads_twice_and_rejects_wrong_voice(tmp_path):
    audio=b'RIFF'+b'\0'*100;checksum=hashlib.sha256(audio).hexdigest();calls=[]
    clip=ProgressClip.parse({'audio_id':'general-00','voice_key':'f'*32,'sha256':checksum,'text':'Een ogenblik.'})
    def download():calls.append(True);return audio
    assert cached(clip,'https://example.test',download,root=tmp_path)==audio
    assert cached(clip,'https://example.test',download,root=tmp_path)==audio and len(calls)==1
    other=ProgressClip(clip.identifier,'b'*32,'a'*64,clip.text)
    with pytest.raises(ValueError):cached(other,'https://example.test',download,root=tmp_path)
    with pytest.raises(ValueError):ProgressClip.parse({'audio_id':'../escape'})
