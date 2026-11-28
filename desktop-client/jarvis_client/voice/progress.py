"""Bounded generic progress recordings; no synthesis on demand."""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re

from jarvis_client.settings import data_directory


@dataclass(frozen=True)
class ProgressClip:
    identifier:str
    voice_key:str
    checksum:str
    text:str

    @classmethod
    def parse(cls,event):
        if not re.fullmatch(r'[a-z]+-\d{2}',event.get('audio_id','')) or not re.fullmatch(r'[a-f0-9]{32}',event.get('voice_key','')) or not re.fullmatch(r'[a-f0-9]{64}',event.get('sha256','')):
            raise ValueError('Ongeldige audioreferentie')
        return cls(event['audio_id'],event['voice_key'],event['sha256'],str(event.get('text',''))[:200])


def cached(clip,origin,download,*,root=None):
    directory=(Path(root) if root else data_directory()/'progress-audio')/hashlib.sha256(origin.encode()).hexdigest()[:24]/clip.voice_key
    target=directory/(clip.identifier+'.wav')
    if target.is_file():
        raw=target.read_bytes()
        if 44<=len(raw)<=800000 and hashlib.sha256(raw).hexdigest()==clip.checksum:return raw
    raw=download()
    if not 44<=len(raw)<=800000 or hashlib.sha256(raw).hexdigest()!=clip.checksum:raise ValueError('Audio komt niet overeen met de stemcache')
    directory.mkdir(parents=True,exist_ok=True)
    temporary=target.with_suffix('.pending');temporary.write_bytes(raw);temporary.replace(target)
    files=sorted(directory.parent.rglob('*.wav'),key=lambda path:path.stat().st_mtime,reverse=True)
    for old in files[300:]:old.unlink()
    return raw
