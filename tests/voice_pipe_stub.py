"""Synthetic private protocol process; no audio, network, keys or model imports."""
import json
import os
import sys
import time

count=0
for line in sys.stdin:
    request=json.loads(line);count+=1
    if request.get("wait"):time.sleep(60)
    if request.get("malformed"):
        print("not-json",flush=True);continue
    print(json.dumps({"ok":True,"result":{"pid":os.getpid(),"count":count,"operation":request.get("operation")}}),flush=True)
