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


def merge_transcript(previous,current):
    """Remove only a matching suffix/prefix from the overlapping audio window."""
    left=list(re.finditer(r"\w+",previous,re.UNICODE));right=list(re.finditer(r"\w+",current,re.UNICODE))
    for size in range(min(12,len(left),len(right)),0,-1):
        if [x.group().casefold() for x in left[-size:]]==[x.group().casefold() for x in right[:size]]:
            return (previous[:left[-size].start()]+current).strip()
    return (previous+" "+current).strip()


class IncrementalTranscript:
    """One bounded, sequential stream per capture; nothing is written to disk."""
    def __init__(self,recognize):
        self.recognize=recognize;self.end=0;self.text='';self.seconds=0.;self.result=None

    def request(self,pcm,valid):
        if not valid():return None
        if len(pcm)<=self.end:return self.result
        start=max(0,self.end-16000)  # 500 ms PCM16 overlap, not the entire history.
        result=self.recognize(pcm_wav(pcm[start:]),valid)
        if not valid() or result is None:return None
        self.text=merge_transcript(self.text,result.get('text',''))
        self.seconds+=result.get('seconds',0)
        self.end=len(pcm);self.result={**result,'text':self.text,'seconds':self.seconds}
        return self.result


class AdaptiveTurn:
    def __init__(self,recognize,valid,*,normal,thinking,partial=lambda *_:None,clock=time.monotonic,incremental=False):
        self.recognize,self.valid,self.partial,self.clock=recognize,valid,partial,clock
        self.normal,self.thinking=normal,thinking;self.revision=0;self.pending=None;self.pending_revision=-1;self.tried_revision=-1
        self.stream=IncrementalTranscript(recognize) if incremental else None
        self.pending_deadline=0.

    def voiced(self):self.revision+=1

    def probe(self,pcm,quiet):
        interval=bool(self.stream and len(pcm)-self.stream.end>=256000)
        if not interval and quiet<self.normal or self.tried_revision==self.revision:return
        if self.pending and not self.pending.done():return
        revision=self.revision;self.pending_revision=self.tried_revision=revision
        future:Future=Future();self.pending=future;deadline=self.clock()+8;self.pending_deadline=deadline
        audio=bytes(pcm) if self.stream else pcm_wav(pcm)
        def recognize():
            try:
                valid=lambda:self.valid() and self.clock()<deadline
                result=self.stream.request(audio,valid) if self.stream else self.recognize(audio,valid)
                if not valid():result=None
                future.set_result(result)
                if result is not None and self.valid() and revision==self.revision:self.partial(result,revision,self)
            except Exception:
                if not future.done():future.set_result(None)
        threading.Thread(target=recognize,name="jarvis-turn-stt",daemon=True).start()

    def ready(self):
        if self.pending is None or self.pending_revision!=self.revision or not self.pending.done():return None
        return self.pending.result()

    def finished(self,quiet):
        result=self.ready()
        return quiet>=self.thinking or quiet>=self.normal and result is not None and completed_utterance(result.get("text",""))

    def finish(self,pcm=None):
        # Reuse a transcript only when no new voiced audio followed its snapshot.
        pending=self.pending
        if not self.stream and (pending is None or self.pending_revision!=self.revision):return None
        while pending is not None and not pending.done():
            if not self.valid() or self.clock()>=self.pending_deadline:return None
            time.sleep(.02)
        if self.stream and pcm is not None:
            if not self.valid():return None
            deadline=self.clock()+8
            return self.stream.request(pcm,lambda:self.valid() and self.clock()<deadline)
        if self.pending_revision!=self.revision:return None
        return self.ready()
