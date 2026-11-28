"""Local readiness watchdog. Never restarts a deliberately stopped service."""
import json
from pathlib import Path
import subprocess
import urllib.request


def check(state=Path('/run/jarvis-health/failures')):
    running=subprocess.run(['systemctl','is-active','--quiet','jarvis.service'],check=False).returncode==0
    if not running:return 'stopped_by_operator_or_systemd'
    healthy=False
    try:
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open('http://127.0.0.1:8765/ready',timeout=3) as response:
            healthy=response.status==200 and json.load(response).get('status')=='ready'
    except (OSError,ValueError):pass
    failures=0 if healthy else (int(state.read_text()) if state.exists() else 0)+1
    state.parent.mkdir(mode=0o700,parents=True,exist_ok=True);state.write_text(str(failures))
    if failures>=3:
        subprocess.run(['systemctl','try-restart','jarvis.service'],check=True,timeout=45)
        state.write_text('0');return 'restarted_after_three_failed_checks'
    return 'ready' if healthy else 'readiness_failed'


if __name__=='__main__':print(check())
