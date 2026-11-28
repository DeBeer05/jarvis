"""Real package manifest and restore safety on disposable local snapshots."""
import hashlib,json
import pytest
from scripts.build_minipc import build
from scripts.minipc_admin import prepare_restore
from server.database import Database


def test_package_contains_runtime_prompts_and_no_user_state(tmp_path):
    target=tmp_path/'JARVIS-MiniPC';archive=build(target)
    assert archive.is_file()
    manifest=json.loads((target/'manifest.json').read_text())
    for name,expected in manifest['files'].items():assert hashlib.sha256((target/'payload'/name).read_bytes()).hexdigest()==expected
    assert all((target/(name+'.ps1')).is_file() for name in ('INSTALL','START','STOP','RESTART','STATUS','UPDATE','BACKUP','RESTORE','REPAIR','UNINSTALL'))
    assert (target/'payload/config/jarvis-voice-system-prompt.txt').is_file()
    assert (target/'payload/desktop-client/voice_worker.py').is_file()
    assert not any(path.name=='.env' or path.suffix in ('.key','.db','.sqlite3') for path in target.rglob('*') if path.is_file())
    with pytest.raises(ValueError):build(target)


def test_restore_keeps_user_content_but_pauses_jobs_and_revokes_sessions(tmp_path):
    (tmp_path/'.jarvis-installation').write_text('synthetic')
    folder=tmp_path/'restore-synthetic';folder.mkdir();path=folder/'jarvis.sqlite3'
    database=Database(path);database.initialize()
    with database.connection() as db:
        db.execute("INSERT INTO auth_users VALUES (1,'owner','synthetic-hash',0)")
        db.execute("INSERT INTO auth_devices VALUES ('device',1,'Test','windows',0,0,1,NULL)")
        db.execute("INSERT INTO auth_sessions VALUES ('session',1,'device',0,0,99999999999,'digest',99999999999,'csrf',NULL)")
        db.execute("INSERT INTO automation_jobs(id,key,device_id,tool,payload,status,due,repeat,timezone,created,updated) VALUES ('job','once','device','EmailSend','{}','queued',0,'once','Europe/Amsterdam',0,0)")
    prepare_restore(path)
    with database.connection() as db:
        assert db.execute('SELECT username FROM auth_users').fetchone()[0]=='owner'
        assert db.execute('SELECT status FROM automation_jobs').fetchone()[0]=='paused'
        assert db.execute('SELECT revoked_at FROM auth_sessions').fetchone()[0] is not None
    assert database.check()


def test_restore_helper_refuses_live_database(tmp_path):
    live=tmp_path/'data';live.mkdir();path=live/'jarvis.sqlite3';Database(path).initialize()
    with pytest.raises(ValueError):prepare_restore(path)


def test_restored_vault_key_is_protected_and_temporary_plaintext_is_removed(tmp_path):
    from cryptography.fernet import Fernet
    from scripts.minipc_admin import restore_vault
    from server.voice_secrets import read_secret
    (tmp_path/'.jarvis-installation').write_text('synthetic')
    folder=tmp_path/'restore-synthetic';folder.mkdir()
    (tmp_path/'secrets').mkdir();source=folder/'vault.key';target=tmp_path/'secrets/vault.bin'
    value=Fernet.generate_key().decode();source.write_text(value)
    restore_vault(source,target)
    assert not source.exists() and read_secret(target)==value


def test_link_key_is_noninteractive_and_existing_keys_are_preserved(tmp_path):
    import shutil,subprocess
    from scripts.minipc_admin import generate_link_key
    if not shutil.which('ssh-keygen'):pytest.skip('OpenSSH key tool unavailable')
    folder=tmp_path/'space in key path';folder.mkdir();key=folder/'link'
    generate_link_key(key)
    response=subprocess.run(['ssh-keygen','-y','-P','','-f',str(key)],capture_output=True,check=True)
    assert response.stdout.startswith(b'ssh-ed25519 ')
    before=key.read_bytes()
    with pytest.raises(ValueError):generate_link_key(key)
    assert key.read_bytes()==before
