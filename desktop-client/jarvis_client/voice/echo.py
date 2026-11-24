"""Bounded far-end reference gate. This is not a hardware AEC or speaker verifier."""
import re
import threading
import time
from collections import deque
from difflib import SequenceMatcher

import numpy as np


class EchoReference:
    def __init__(self,clock=time.monotonic):
        self.clock=clock;self.lock=threading.Lock();self.blocks:deque[np.ndarray]=deque(maxlen=100)
        self.last=-10.;self.maximum_correlation=0.

    def clear(self):
        with self.lock:self.blocks.clear();self.last=-10.;self.maximum_correlation=0.

    def feed(self,pcm,rate):
        samples=np.frombuffer(pcm,dtype=np.int16).astype(np.float32)/32768
        if not len(samples):return
        # Keep at most two seconds at 16 kHz; alignment search runs at 2 kHz.
        size=max(1,round(len(samples)*16000/rate))
        reduced=np.interp(np.arange(size)*rate/16000,np.arange(len(samples)),samples)
        with self.lock:self.blocks.append(reduced);self.last=self.clock()

    def filter(self,samples):
        with self.lock:
            if self.clock()-self.last>1 or not self.blocks:return samples
            full_reference=np.concatenate(tuple(self.blocks))[-32000:]
        reference=full_reference[::8]
        target=samples[::8].astype(np.float64)/32768
        if len(target)<20 or len(reference)<len(target):return samples
        target=target-target.mean();energy=float(target@target)
        if energy<1e-9:return samples
        width=len(target)
        centered=reference-reference.mean()
        products=np.correlate(centered,target,mode="valid")
        sums=np.concatenate(([0.],np.cumsum(centered)))
        squares=np.concatenate(([0.],np.cumsum(centered*centered)))
        powers=np.maximum(0,squares[width:]-squares[:-width]-(sums[width:]-sums[:-width])**2/width)
        correlations=np.abs(products)/np.sqrt(np.maximum(1e-12,powers*energy))
        index=int(np.argmax(correlations))*8
        full_target=samples.astype(np.float64)/32768;full_target-=full_target.mean()
        full_energy=float(full_target@full_target)
        score=0.;matched=None
        for offset in range(max(0,index-7),min(index+8,len(full_reference)-len(samples)+1)):
            fragment=full_reference[offset:offset+len(samples)];fragment=fragment-fragment.mean()
            power=float(fragment@fragment)
            current=abs(float(fragment@full_target))/max(1e-12,float(np.sqrt(power*full_energy)))
            if current>score:score=current;matched=fragment
        with self.lock:self.maximum_correlation=max(self.maximum_correlation,score)
        if score<.78 or matched is None:return samples
        # Suppress only strong matches; keep the residual when a person talks
        # over the assistant. No persistent raw audio, model or extra process.
        gain=float(full_target@matched)/max(1e-12,float(matched@matched))
        echo=matched*gain*32768
        return np.clip(samples.astype(np.float64)-echo,-32768,32767).astype(np.int16)


def resembles_output(text,spoken):
    words=lambda value:re.findall(r"\w+",value.casefold())
    candidate=words(text);reference=words(spoken)
    if not candidate:return True
    # Never turn echoed approval words into authority during duplex capture.
    if len(candidate)<=2 and all(word in reference for word in candidate):return True
    if len(candidate)<3:return False
    for start in range(max(1,len(reference)-len(candidate)+1)):
        fragment=reference[start:start+len(candidate)]
        if SequenceMatcher(None,candidate,fragment,autojunk=False).ratio()>=.85:return True
    return False
