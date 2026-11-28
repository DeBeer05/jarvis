"""Small install-only operations. Never logs or returns credentials."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def prepare_restore(path):
    import sqlite3,time
    from contextlib import closing
    path=Path(path).resolve(strict=True)
    if path.name!='jarvis.sqlite3' or not path.parent.name.startswith('restore-') or not (path.parent.parent/'.jarvis-installation').is_file():raise ValueError('Only a fresh managed restore snapshot may be changed')
    with closing(sqlite3.connect(path)) as db,db:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Invalid restore database')
        tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        stamp=time.time()
        for name in ('auth_sessions','auth_refresh_tokens'):
            if name in tables:db.execute('UPDATE '+name+' SET revoked_at=? WHERE revoked_at IS NULL',(stamp,))
        if 'auth_pairing' in tables:db.execute("UPDATE auth_pairing SET status='denied' WHERE status IN ('pending','approved')")
        if 'automation_jobs' in tables:db.execute("UPDATE automation_jobs SET status='paused',approval_hash=NULL,approved_device=NULL,approval_expires=NULL WHERE status IN ('approval','queued','running','waiting','blocked','paused')")
        if 'device_commands' in tables:db.execute("UPDATE device_commands SET state='uncertain',lease_hash=NULL WHERE state IN ('queued','leased','running')")

def restore_vault(source,target):
    from cryptography.fernet import Fernet
    from server.voice_secrets import save_secret,read_secret
    source=Path(source).resolve(strict=True);target=Path(target).resolve()
    root=source.parent.parent
    if source.name!='vault.key' or not source.parent.name.startswith('restore-') or not (root/'.jarvis-installation').is_file() or target!=root/'secrets/vault.bin':raise ValueError('Invalid restore key location')
    value=source.read_text().strip();Fernet(value.encode())
    save_secret(target,value,machine=True)
    if read_secret(target)!=value:raise ValueError('Restored key not verified')
    source.unlink()  # Only the verified temporary key extracted by our restore.


def configure_voice(root):
    import getpass,re
    from server.voice_secrets import save_secret
    root=Path(root).resolve(strict=True)
    if not (root/'.jarvis-installation').is_file() or not sys.stdin.isatty():raise ValueError('Use the local interactive installer shell')
    voice=input('ElevenLabs Voice ID: ').strip()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',voice):raise ValueError('Invalid voice ID')
    value=getpass.getpass('ElevenLabs API-key (onzichtbaar): ')
    destination=root/'secrets/elevenlabs.bin';save_secret(destination,value,machine=True)
    env=root/'data/.env';lines=[line for line in env.read_text(encoding='utf-8-sig').splitlines() if not line.startswith(('ELEVENLABS_API_KEY=','ELEVENLABS_API_KEY_FILE=','ELEVENLABS_VOICE_ID='))]
    lines+=['ELEVENLABS_API_KEY_FILE='+str(destination),'ELEVENLABS_VOICE_ID='+voice]
    env.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Sleutel beveiligd opgeslagen. Herstart JARVIS en kies Premium bij Spraak. Kostenlimieten blijven gelden.')


def main():
    if len(sys.argv)==4 and sys.argv[1]=='restore-vault':
        restore_vault(sys.argv[2],sys.argv[3])
    elif len(sys.argv)==3 and sys.argv[1]=='configure-voice':configure_voice(sys.argv[2])
    elif len(sys.argv)==3 and sys.argv[1]=='prepare-restore':prepare_restore(sys.argv[2])
    elif len(sys.argv)==3 and sys.argv[1]=='keygen-machine':
        from cryptography.fernet import Fernet
        from server.voice_secrets import save_secret
        if Path(sys.argv[2]).exists():raise ValueError('Key already exists')
        save_secret(sys.argv[2],Fernet.generate_key().decode(),machine=True)
    else:raise ValueError('Unknown administration operation')

if __name__=='__main__':main()
