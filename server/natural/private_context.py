"""Bounded RAM-only turns when ordinary history is disabled."""
import threading
import time
from collections import OrderedDict


class PrivateContext:
    def __init__(self,clock=time.monotonic):
        self.clock=clock;self.lock=threading.Lock();self.items:OrderedDict[tuple,list]=OrderedDict();self.expiries={}

    def prune(self):
        now=self.clock()
        for key in list(self.items):
            if now>self.expiries[key]:self.items.pop(key);self.expiries.pop(key)

    def get(self,user,conversation,forgotten,ttl):
        with self.lock:
            self.prune();key=(user,conversation)
            if key not in self.items:return []
            self.items[key]=[row for row in self.items[key] if row["id"] not in forgotten]
            self.items.move_to_end(key)
            return [dict(row) for row in self.items[key]]

    def add(self,user,run,ttl):
        with self.lock:
            self.prune();key=(user,run.conversation_id)
            rows=self.items.get(key,[])
            rows.append({"id":run.request_id,"sequence":len(rows)+1,"user_text":run.message,"assistant_text":run.text,"status":run.status})
            rows=rows[-20:]
            while sum(len(row["user_text"])+len(row["assistant_text"]) for row in rows)>32000:rows.pop(0)
            self.items[key]=rows;self.expiries[key]=self.clock()+ttl;self.items.move_to_end(key)
            while len(self.items)>50:
                old,_=self.items.popitem(last=False);self.expiries.pop(old)

    def clear(self):
        with self.lock:self.items.clear();self.expiries.clear()
