"""Bounded speculative STT: keep capturing while deciding whether a turn ended."""
import io
import re
import threading
import time
import wave
from concurrent.futures import Future


def completed_utterance(text):
    words=re.findall(r"\w+",text.casefold())
    if not words:return False
    if words[-1] in {"eh","ehm","uh","uhm","en","maar","of","om","voor","met","naar","een","de","het","mijn","jouw","dat","dus","want","als","dan"}:return False
    if text.count("(")!=text.count(")"):return False
    if re.search(r"\b(?:maak|plan|verzet|verplaats)\b.*\b(?:afspraak|vergadering)\b",text,re.I):
        # A missing time can be a thinking pause. Wait for the maximum before
        # slot filling asks for it; this classifier never invents a time.
        if not re.search(r"\b\d{1,2}:\d{2}\b|\b(?:om|van|tussen)\s+(?:\d+|een|twee|drie|vier|vijf|zes|zeven|acht|negen|tien|elf|twaalf|half|kwart)\b",text,re.I):return False
    return True


def pcm_wav(pcm):
    result=io.BytesIO()
    with wave.open(result,"wb") as output:
        output.setnchannels(1);output.setsampwidth(2);output.setframerate(16000);output.writeframes(pcm)
    return result.getvalue()


class AdaptiveTurn:
    def __init__(self,recognize,valid,*,normal,thinking,partial=lambda *_:None,clock=time.monotonic):
        self.recognize,self.valid,self.partial,self.clock=recognize,valid,partial,clock
        self.normal,self.thinking=normal,thinking;self.revision=0;self.pending=None;self.pending_revision=-1;self.tried_revision=-1

    def voiced(self):self.revision+=1

    def probe(self,pcm,quiet):
        if quiet<self.normal or self.tried_revision==self.revision:return
        if self.pending and not self.pending.done():return
        revision=self.revision;self.pending_revision=self.tried_revision=revision
        future:Future=Future();self.pending=future;deadline=self.clock()+8
        audio=pcm_wav(pcm)
        def recognize():
            try:
                result=self.recognize(audio,lambda:self.valid() and self.clock()<deadline)
                future.set_result(result)
                if self.valid() and revision==self.revision:self.partial(result,revision,self)
            except Exception:
                if not future.done():future.set_result(None)
        threading.Thread(target=recognize,name="jarvis-turn-stt",daemon=True).start()

    def ready(self):
        if self.pending is None or self.pending_revision!=self.revision or not self.pending.done():return None
        return self.pending.result()

    def finished(self,quiet):
        result=self.ready()
        return quiet>=self.thinking or quiet>=self.normal and result is not None and completed_utterance(result.get("text",""))

    def finish(self):
        # Reuse a transcript only when no new voiced audio followed its snapshot.
        pending=self.pending
        if pending is None or self.pending_revision!=self.revision:return None
        while not pending.done():
            if not self.valid():return None
            time.sleep(.02)
        return self.ready()
