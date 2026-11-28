"""Explicit Windows -> existing Oracle cutover with encrypted export and fencing.

Never copies SSH keys, logs credentials, buys resources, or runs two schedulers.
The remote scheduler stays fenced until final deployment verification.
"""
import argparse
from datetime import datetime,UTC
import json
import os
from pathlib import Path,PurePosixPath
import re
import shlex
import shutil
import subprocess
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from cryptography.fernet import Fernet
import httpx
from scripts.cloud_backup import backup,restore
from server.config import load_settings
from server.voice_secrets import read_secret,save_secret


def environment(settings,origin,*,google=False):
    if not re.fullmatch(r'https://[a-z0-9][a-z0-9.-]+',origin):raise ValueError('An exact HTTPS origin is required')
    data={
      'JARVIS_PROFILE':'oracle-production','JARVIS_ENV':'production','JARVIS_HOST':'127.0.0.1','JARVIS_PORT':'8765',
      'JARVIS_PUBLIC_ORIGIN':origin,'JARVIS_COOKIE_SECURE':'true','JARVIS_ENABLE_EXTERNAL_ACCESS':'false',
      'JARVIS_DATABASE_PATH':'/var/lib/jarvis/jarvis.sqlite3','JARVIS_RUNTIME_DIR':'/run/jarvis','JARVIS_LOG_PATH':'/var/log/jarvis/server.log',
      'JARVIS_ENABLE_AUTOMATIONS':'false','JARVIS_VAULT_KEY_FILE':'/var/lib/jarvis/secrets/vault.key',
      'ELEVENLABS_API_KEY_FILE':'/var/lib/jarvis/secrets/elevenlabs.key' if settings.elevenlabs_api_key else '',
      'ELEVENLABS_VOICE_ID':settings.elevenlabs_voice_id,'GEMINI_API_KEY':settings.gemini_api_key,'GROQ_API_KEY':settings.groq_api_key,
      'JARVIS_AI_PROVIDER':settings.ai_provider,'JARVIS_AI_PREFERRED_PROVIDER':settings.preferred_provider,
      'GROQ_MODEL':settings.groq_model,'GEMINI_MODEL':settings.gemini_model,'OLLAMA_MODEL':settings.ollama_model,
      'OLLAMA_BASE_URL':'http://127.0.0.1:11434','JARVIS_ORACLE_BASE_URL':'http://127.0.0.1:11434','JARVIS_ORACLE_MODEL':settings.oracle_model,
      'JARVIS_AI_TIMEOUT_SECONDS':str(settings.ai_timeout_seconds),'JARVIS_PROVIDER_TIMEOUT_SECONDS':str(settings.provider_timeout_seconds),
      'JARVIS_AI_MAX_OUTPUT_TOKENS':str(settings.max_output_tokens),'JARVIS_MAX_CONTEXT_CHARS':str(settings.max_context_chars),
      'JARVIS_MAX_CONCURRENT_AI':'2','JARVIS_VOICE_PYTHON':'/opt/jarvis/voice-venv/bin/python','JARVIS_MODELS_DIR':'/opt/jarvis/models',
      'JARVIS_FORCE_CPU':'true','OMP_NUM_THREADS':'2','HF_HUB_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','XDG_CACHE_HOME':'/var/lib/jarvis/cache',
    }
    if google:data['JARVIS_GOOGLE_CLIENT_FILE']='/var/lib/jarvis/secrets/google-client.json'
    if any('\n' in value or '\r' in value for value in data.values()):raise ValueError('Multiline configuration is not permitted')
    return ''.join(key+'='+json.dumps(value)+'\n' for key,value in data.items())


def protected_stage():
    if os.name!='nt':raise ValueError('Run export on the original Windows host')
    directory=Path(os.environ['LOCALAPPDATA'])/'JARVIS/Deployment'/str(uuid.uuid4());directory.mkdir(parents=True)
    account=subprocess.check_output(['whoami'],text=True).strip()
    subprocess.run(['icacls.exe',str(directory),'/inheritance:r','/grant:r',account+':(OI)(CI)F','SYSTEM:(OI)(CI)F'],check=True,capture_output=True)
    return directory


class Migration:
    def __init__(self,settings,ssh_key,origin,release,commit,manifest_sha256):
        self.settings=settings;self.origin=origin;self.release=release;self.stage=protected_stage();self.counter=0
        if not re.fullmatch(r'/opt/jarvis/releases/[a-z0-9-]{12,80}',release):raise ValueError('Invalid prepared release')
        if not re.fullmatch('[a-f0-9]{40}',commit) or not re.fullmatch('[a-f0-9]{64}',manifest_sha256):raise ValueError('Exact release approval is required')
        self.commit,self.manifest_sha256=commit,manifest_sha256
        self.ssh=['-i',str(Path(ssh_key).resolve(strict=True)),'-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','-o','HostKeyAlgorithms=ssh-ed25519','-o','ConnectTimeout=8']
        self.target='ubuntu@143.47.176.199';self.identifier=str(uuid.uuid4());self.remote_stage='/home/ubuntu/jarvis-master-staging/'+self.identifier
        self.stopped=False;self.remote_started=False;self.caddy_changed=False

    def run(self,arguments,*,data=None,timeout=120,sensitive=False):
        self.counter+=1
        result=subprocess.run(arguments,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,check=False)
        (self.stage/f'step-{self.counter:02}.log').write_bytes(b'Credential output suppressed.\n' if sensitive else result.stdout+b'\n'+result.stderr)
        if result.returncode:raise RuntimeError('Migration step failed; inspect the protected deployment log')
        return result.stdout

    def remote(self,command,*,data=None,timeout=120,sensitive=False):return self.run(['ssh',*self.ssh,self.target,command],data=data,timeout=timeout,sensitive=sensitive)

    def execute(self):
        # TLS identity is checked before any user credentials or data are moved.
        with httpx.Client(verify=True,trust_env=False,follow_redirects=False,timeout=10) as client:
            response=client.get(self.origin+'/health')
            if response.status_code not in (200,502,503):raise ValueError('Unexpected approved gateway response')
        source=self.settings;key=self.stage/'migration.dpapi';save_secret(key,Fernet.generate_key().decode())
        includes=[]
        google=bool(source.google_client_file and Path(source.google_client_file).is_file())
        if google:
            target=self.stage/'google-client.json';shutil.copyfile(source.google_client_file,target);includes.append(target)
        env=self.stage/'server.env';env.write_bytes(environment(source,self.origin,google=google).encode());includes.append(env)
        if source.elevenlabs_api_key:
            target=self.stage/'elevenlabs.key';target.write_text(source.elevenlabs_api_key,encoding='utf-8');includes.append(target)
        try:
            self.remote('test -x '+shlex.quote(self.release+'/.venv/bin/python')+' && sudo -n test ! -e /var/lib/jarvis/jarvis.sqlite3')
            verify="import sys;sys.path.insert(0,sys.argv[1]);from scripts.release_manifest import verify;verify(sys.argv[1],sys.argv[2],sys.argv[3])"
            self.remote('sudo -n '+shlex.quote(self.release+'/.venv/bin/python')+' -c '+shlex.quote(verify)+' '+shlex.quote(self.release)+' '+self.commit+' '+self.manifest_sha256)
            self.run([str(ROOT/'.venv/Scripts/python.exe'),'-m','server','stop','--wait','15']);self.stopped=True
            archive=self.stage/'migration.enc'
            backup(source.database_path,archive,key,portable=True,old_vault_key=source.vault_key_file,includes=includes)
            restore(archive,self.stage/'verified-restore',key)
            self.remote('install -d -m 0700 '+shlex.quote(self.remote_stage))
            self.run(['scp',*self.ssh,str(archive),self.target+':'+self.remote_stage+'/migration.enc'])
            remote_key='/etc/jarvis/migration/'+self.identifier+'/key'
            self.remote('sudo -n install -d -m 0700 '+shlex.quote(str(PurePosixPath(remote_key).parent))+' && sudo -n sh -c '+shlex.quote('umask 077; cat > '+remote_key),data=read_secret(key).encode())
            restored='/var/lib/jarvis/migration-'+self.identifier
            self.remote('sudo -n '+shlex.quote(self.release+'/.venv/bin/python')+' '+shlex.quote(self.release+'/scripts/cloud_backup.py')+' restore --archive '+shlex.quote(self.remote_stage+'/migration.enc')+' --directory '+shlex.quote(restored)+' --key-file '+shlex.quote(remote_key))
            provision='''import os,pwd,shutil,sqlite3,sys,time
from pathlib import Path
from cryptography.fernet import Fernet
root=Path(sys.argv[1]);account=pwd.getpwnam('jarvis');destination=Path('/var/lib/jarvis/jarvis.sqlite3')
if destination.exists():raise ValueError('Existing database preserved; use controlled update')
with destination.open('xb') as target:
    (root/'created-database').write_text('owned migration copy')
    with (root/'jarvis.sqlite3').open('rb') as source:shutil.copyfileobj(source,target)
destination.chmod(0o600);os.chown(destination,account.pw_uid,account.pw_gid)
with sqlite3.connect(destination) as db:
    if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Database integrity failed')
    db.execute("UPDATE automation_jobs SET status='uncertain',updated=? WHERE status='running'",(time.time(),))
    db.execute("UPDATE device_commands SET state='uncertain',lease_hash=NULL WHERE state IN ('leased','running','started')")
for name in ('vault.key','elevenlabs.key','google-client.json'):
    source=root/name
    if source.is_file():
        target=Path('/var/lib/jarvis/secrets')/name;shutil.copyfile(source,target);target.chmod(0o600);os.chown(target,account.pw_uid,account.pw_gid)
shutil.copyfile(root/'server.env','/etc/jarvis/server.env');os.chmod('/etc/jarvis/server.env',0o600)
key=Path('/etc/jarvis/backup.key')
if not key.exists():key.write_bytes(Fernet.generate_key());key.chmod(0o600)
print('Personal snapshot restored and checked; schedulers remain fenced.')
'''
            self.remote('sudo -n '+shlex.quote(self.release+'/.venv/bin/python')+' - '+shlex.quote(restored),data=provision.encode())
            self.remote('sudo -n ln -s '+shlex.quote(self.release)+' /opt/jarvis/migration-next-'+self.identifier+' && sudo -n mv -T /opt/jarvis/migration-next-'+self.identifier+' /opt/jarvis/current')
            self.remote('sudo -n systemctl enable jarvis.service && sudo -n systemctl start jarvis.service');self.remote_started=True
            self.remote('for attempt in $(seq 1 30); do curl -fsS http://127.0.0.1:8765/ready >/dev/null && exit 0; sleep 1; done; exit 1',timeout=40)
            backup_caddy='/etc/caddy/Caddyfile.before-master-'+self.identifier
            script='''from pathlib import Path
import shutil,sys
p=Path('/etc/caddy/Caddyfile');old=p.read_text();needle='127.0.0.1:18765'
if old.count(needle)!=1:raise ValueError('Unexpected gateway target; kept unchanged')
shutil.copy2(p,sys.argv[1]);p.write_text(old.replace(needle,'127.0.0.1:8765'))
'''
            self.remote('sudo -n python3 - '+shlex.quote(backup_caddy),data=script.encode());self.caddy_changed=True
            self.remote('sudo -n caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile && sudo -n systemctl reload caddy')
            with httpx.Client(verify=True,trust_env=False,follow_redirects=False,timeout=10) as client:
                ready=client.get(self.origin+'/ready');ready.raise_for_status()
                if ready.json().get('status')!='ready' or client.get(self.origin+'/api/v1/status').status_code!=401 or client.get(self.origin+'/internal/status').status_code!=404:raise ValueError('Public security acceptance failed')
            self.remote('sudo -n systemctl enable --now jarvis-backup.timer jarvis-health.timer && sudo -n systemctl start jarvis-backup.service')
            backup_key=self.remote('sudo -n cat /etc/jarvis/backup.key',sensitive=True).decode().strip()
            save_secret(self.stage/'oracle-backup.dpapi',backup_key)
            record={'status':'cloud_backend_ready','origin':self.origin,'release':self.release,'scheduler_fenced':True,'source_backend_stopped':True,'at':datetime.now(UTC).isoformat()}
            (self.stage/'result.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
            print(json.dumps({**record,'protected_local_backup':str(self.stage)}))
            return record
        except BaseException:
            # There is no automatic return to a stale local scheduler unless the
            # cloud instance has positively stopped; an ambiguous SSH loss fences both.
            if self.stopped:
                self.remote('sudo -n systemctl stop jarvis.service && ! sudo -n systemctl is-active --quiet jarvis.service')
                if self.caddy_changed:
                    self.remote('sudo -n cp -p '+shlex.quote('/etc/caddy/Caddyfile.before-master-'+self.identifier)+' /etc/caddy/Caddyfile && sudo -n systemctl reload caddy')
                preserve='''from pathlib import Path
import shutil,sys
root=Path('/var/lib/jarvis');migration=root/('migration-'+sys.argv[1]);target=root/('failed-migration-'+sys.argv[1])
if (migration/'created-database').is_file():
    target.mkdir(mode=0o700,exist_ok=False)
    for suffix in ('','-wal','-shm'):
        source=root/('jarvis.sqlite3'+suffix)
        if source.exists():shutil.move(str(source),str(target/source.name))
'''
                self.remote('sudo -n python3 - '+shlex.quote(self.identifier),data=preserve.encode())
                log=(self.stage/'local-rollback.log').open('ab')
                subprocess.Popen([str(ROOT/'.venv/Scripts/python.exe'),'-m','server','--no-console'],cwd=ROOT,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                log.close()
            raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');parser.add_argument('--ssh-key',required=True,type=Path)
    parser.add_argument('--origin',required=True);parser.add_argument('--release',required=True)
    parser.add_argument('--commit',required=True);parser.add_argument('--manifest-sha256',required=True);args=parser.parse_args()
    if not args.execute:parser.error('Explicit --execute is required; inspect the prepared release first')
    Migration(load_settings(),args.ssh_key,args.origin,args.release,args.commit,args.manifest_sha256).execute()
