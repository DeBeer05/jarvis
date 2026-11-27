"""Apply a root-approved exact release, with fenced SQLite rollback.

Linux only. No fetching, dependency installs, model downloads or approvals here.
A timer may consume an explicit approval ticket; absence of a ticket is a no-op.
"""
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dotenv import dotenv_values
from scripts.cloud_backup import backup,restore

BASE=Path('/opt/jarvis')
TICKET=Path('/etc/jarvis/approved-release.json')
ENV=Path('/etc/jarvis/server.env')
DATA=Path('/var/lib/jarvis/jarvis.sqlite3')
BACKUPS=Path('/var/lib/jarvis/backups')
KEY=Path('/etc/jarvis/backup.key')


def run(*args):
    result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=120,check=False)
    if result.returncode:raise RuntimeError('Deployment command failed; service kept fenced')
    return result.stdout.strip()


def approved_release(ticket,base=BASE):
    if ticket.is_symlink() or ticket.stat().st_uid!=0 or stat.S_IMODE(ticket.stat().st_mode)&0o022:raise ValueError('Approval ticket must be root-controlled')
    value=json.loads(ticket.read_text())
    commit=value.get('commit','');release=Path(value.get('release','')).resolve(strict=True)
    if not re.fullmatch('[0-9a-f]{40}',commit) or release.parent!=(base/'releases').resolve():raise ValueError('Invalid exact release approval')
    for path in (release,*release.parents):
        if path.stat().st_uid!=0 or path.stat().st_mode&0o022:raise ValueError('Release path must be root-controlled')
    # A root-owned top directory is insufficient if files/venvs are user-writable.
    for path in release.rglob('*'):
        target=path.resolve(strict=True) if path.is_symlink() else path
        if path.is_symlink() and not (target.is_relative_to(release) or target.is_relative_to('/usr') or target.is_relative_to('/lib')):
            raise ValueError('Unexpected external release symlink')
        if target.stat().st_uid!=0 or target.stat().st_mode&0o022:
            raise ValueError('Release contents must be root-controlled')
    if run('git','-C',str(release),'rev-parse','HEAD')!=commit:raise ValueError('Commit differs from approval')
    if run('git','-C',str(release),'status','--porcelain','--untracked-files=normal'):raise ValueError('Candidate contains changes')
    return release,commit


def switch(current,release):
    pending=current.with_name('next')
    if pending.exists() or pending.is_symlink():raise ValueError('A pending release already exists')
    pending.symlink_to(release,target_is_directory=True);os.replace(pending,current)


def healthy():
    # No environment HTTP proxies and no external connection.
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for attempt in range(30):
        try:
            with opener.open('http://127.0.0.1:8765/ready',timeout=2) as response:
                if response.status==200 and json.load(response).get('status')=='ready':return True
        except (OSError,ValueError):pass
        time.sleep(1)
    return False


def promote(release,commit):
    settings=dotenv_values(ENV,interpolate=False)
    if settings.get('JARVIS_AUTOMATIONS_ENABLED')!='false' or settings.get('JARVIS_DATABASE_PATH')!=str(DATA):raise ValueError('Maintenance fence and standard data path required')
    current=BASE/'current';old=current.resolve(strict=True)
    if old==release:raise ValueError('Release is already active')
    run('runuser','-u','jarvis','--',str(release/'.venv/bin/python'),'-m','pip','check')
    BACKUPS.mkdir(mode=0o700,exist_ok=True)
    archive=BACKUPS/(time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+commit[:12]+'.enc')
    run('systemctl','stop','jarvis.service')
    # A stopped service is required before backup/restore or changing the link.
    backup(DATA,archive,KEY)
    try:
        switch(current,release)
        run('systemctl','start','jarvis.service')
        if not healthy():raise RuntimeError('Candidate readiness failed')
    except Exception:
        run('systemctl','stop','jarvis.service')
        with tempfile.TemporaryDirectory(prefix='restore-',dir=BACKUPS) as temporary:
            target=Path(temporary)/'snapshot';restore(archive,target,KEY)
            # Stop completed; stale journals must not override the restored snapshot.
            for suffix in ('-wal','-shm'):
                DATA.with_name(DATA.name+suffix).unlink(missing_ok=True)
            shutil.copyfile(target/'jarvis.sqlite3',DATA)
            os.chmod(DATA,0o600);shutil.chown(DATA,user='jarvis',group='jarvis')
        if current.resolve()!=old:switch(current,old)
        run('systemctl','start','jarvis.service')
        if not healthy():raise RuntimeError('Rollback needs operator intervention') from None
        raise RuntimeError('Candidate rejected; old release and database restored') from None
    TICKET.unlink()


def main():
    if sys.platform!='linux' or os.geteuid()!=0:
        print('Only a local root-controlled Linux deployment is supported.');return 2
    if not TICKET.exists():return 0
    try:
        release,commit=approved_release(TICKET)
        promote(release,commit)
        print('Approved release healthy; automations remain disabled.');return 0
    except Exception:
        # Leave the approval ticket for inspection; no repeated automatic attempts.
        failed=TICKET.with_suffix('.failed')
        if TICKET.exists() and not failed.exists():TICKET.rename(failed)
        print('Deployment stopped or rolled back; inspect locally before reapproval.',file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
