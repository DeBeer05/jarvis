"""Cloud opt-in boundaries; no real accounts, network, models or remote writes."""
import pytest
from fastapi.testclient import TestClient

from server.config import ConfigurationError, load_settings
from server.voice_secrets import save_secret
from server.automation.vault import SecretVault
from tests.test_security import make_app
from tests.auth_helpers import login, owner_hash

ORIGIN='https://jarvis.example.org'
FORWARDED={'X-Forwarded-Proto':'https','X-Forwarded-For':'198.51.100.12'}


def cloud(tmp_path):
    return load_settings(root=tmp_path,environ={'JARVIS_PROFILE':'oracle-production','JARVIS_PUBLIC_ORIGIN':ORIGIN})


@pytest.mark.parametrize('origin',['','http://jarvis.example.org','https://localhost','https://user:secret@jarvis.example.org','https://jarvis.example.org/path'])
def test_cloud_requires_https_origin(tmp_path,origin):
    with pytest.raises(ConfigurationError):
        load_settings(root=tmp_path,environ={'JARVIS_PROFILE':'oracle-production','JARVIS_PUBLIC_ORIGIN':origin})


def test_proxy_keeps_auth_csrf_and_internal_boundaries(tmp_path):
    settings=cloud(tmp_path)
    assert settings.cookie_secure=='true' and settings.host=='127.0.0.1'
    app=make_app(settings)
    with TestClient(app,base_url=ORIGIN,client=('127.0.0.1',3456),headers=FORWARDED) as client:
        app.state.security.store.create_owner('owner',owner_hash())
        assert client.get('/api/v1/natural/settings').status_code==401
        assert login(client).status_code==200
        assert client.get('/api/v1/natural/settings').status_code==200
        assert client.get('/api/v1/status').status_code==200
        assert client.get('/internal/status').status_code==403
        assert all(cookie.secure for cookie in client.cookies.jar)
        assert client.post('/api/v1/auth/logout',headers={'X-Jarvis-CSRF':'wrong'}).status_code==403
        assert client.get('/health',headers={'X-Forwarded-For':'1.1.1.1, 2.2.2.2'}).status_code==403
        assert client.get('/health',headers={'X-Forwarded-Proto':'http'}).status_code==403
        assert client.get('/health',headers={'Host':'attacker.example.org'}).status_code==403
        assert client.get('/health',headers=[('X-Forwarded-For','1.1.1.1'),('X-Forwarded-For','2.2.2.2')]).status_code==403
    with TestClient(app,base_url=ORIGIN,client=('198.51.100.20',3456),headers=FORWARDED) as client:
        assert client.get('/health').status_code==403


def test_local_profile_does_not_trust_forwarded_headers(settings):
    app=make_app(settings)
    with TestClient(app,base_url='http://127.0.0.1:8765',client=('198.51.100.20',3456),headers=FORWARDED) as client:
        assert client.get('/api/v1/natural/settings').status_code==403


def test_portable_vault_roundtrip_wrong_key_and_legacy_rejection(tmp_path):
    from cryptography.fernet import Fernet
    path=tmp_path/'vault.key';save_secret(path,Fernet.generate_key().decode())
    vault=SecretVault(None,str(path))
    encrypted=vault.crypt(b'synthetic-refresh-secret')
    assert b'synthetic-refresh-secret' not in encrypted
    assert vault.crypt(encrypted,True)==b'synthetic-refresh-secret'
    save_secret(path,Fernet.generate_key().decode())
    with pytest.raises(ValueError):vault.crypt(encrypted,True)
    with pytest.raises(ValueError):vault.crypt(b'old-DPAPI-ciphertext',True)


def test_cloud_oauth_requires_exact_web_callback(tmp_path):
    from types import SimpleNamespace
    from server.automation.google import IntegrationManager
    settings=cloud(tmp_path)
    # begin must reject before accessing storage or starting network I/O.
    manager=object.__new__(IntegrationManager)
    manager.security=SimpleNamespace(settings=settings);manager.port=8765
    manager.config=lambda:{'kind':'installed','redirect_uris':[]}
    with pytest.raises(ValueError,match='Web OAuth'):manager.begin(None,['calendar'])
    assert manager.redirect==ORIGIN+'/oauth/google/callback'


def test_cpu_override_and_model_location(monkeypatch,tmp_path):
    from server.mobile import SpeechBridge
    monkeypatch.setenv('JARVIS_MODELS_DIR',str(tmp_path));monkeypatch.setenv('JARVIS_FORCE_CPU','true')
    captured={}
    bridge=SpeechBridge(['unused'])
    def exchange(request,**kwargs):
        captured.update(request);return {'ok':True,'result':{}}
    monkeypatch.setattr(bridge.worker,'exchange',exchange)
    bridge.run('transcribe',{'device':'cuda'})
    assert captured['device']=='cpu' and captured['models']==str(tmp_path)


def test_encrypted_backup_restores_wal_snapshot_without_overwrite(tmp_path):
    import sqlite3
    from cryptography.fernet import Fernet,InvalidToken
    from scripts.cloud_backup import backup,restore
    database=tmp_path/'source.sqlite3';key=tmp_path/'backup.key';archive=tmp_path/'backup.enc'
    save_secret(key,Fernet.generate_key().decode())
    with sqlite3.connect(database) as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('CREATE TABLE test(value TEXT)');db.execute("INSERT INTO test VALUES ('private-synthetic-text')");db.commit()
        backup(database,archive,key)
        assert b'private-synthetic-text' not in archive.read_bytes()
        restore(archive,tmp_path/'restored',key)
    with sqlite3.connect(tmp_path/'restored/jarvis.sqlite3') as db:
        assert db.execute('SELECT value FROM test').fetchone()[0]=='private-synthetic-text'
    with pytest.raises(FileExistsError):restore(archive,tmp_path/'restored',key)
    save_secret(key,Fernet.generate_key().decode())
    with pytest.raises(InvalidToken):restore(archive,tmp_path/'wrong-key',key)
    assert not (tmp_path/'wrong-key').exists()


def test_portable_snapshot_migrates_only_the_copy(tmp_path):
    import sqlite3
    from cryptography.fernet import Fernet
    from scripts.cloud_backup import snapshot,portable_snapshot
    path=tmp_path/'source.sqlite3';key=tmp_path/'vault.bin';save_secret(key,Fernet.generate_key().decode())
    vault=SecretVault(None,str(key));original=vault.crypt(b'synthetic-refresh')
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE integration_secrets(key TEXT PRIMARY KEY,ciphertext BLOB)')
        db.execute('CREATE TABLE integration_oauth(state_hash TEXT)')
        db.execute('INSERT INTO integration_secrets VALUES (?,?)',('synthetic',original))
        db.execute("INSERT INTO integration_oauth VALUES ('pending')")
    raw,new_key=portable_snapshot(snapshot(path),str(key))
    restored=tmp_path/'portable.sqlite3';restored.write_bytes(raw)
    with sqlite3.connect(restored) as db:
        ciphertext=db.execute('SELECT ciphertext FROM integration_secrets').fetchone()[0]
        assert Fernet(new_key).decrypt(ciphertext[len(b'JARVIS-FERNET-1\0'):])==b'synthetic-refresh'
        assert db.execute('SELECT COUNT(*) FROM integration_oauth').fetchone()[0]==0
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT ciphertext FROM integration_secrets').fetchone()[0]==original
        assert db.execute('SELECT COUNT(*) FROM integration_oauth').fetchone()[0]==1


@pytest.mark.skipif(__import__('os').name!='nt',reason='Original Windows-host migration')
def test_windows_dpapi_portable_export(tmp_path):
    import sqlite3
    from cryptography.fernet import Fernet
    from scripts.cloud_backup import portable_snapshot,snapshot
    path=tmp_path/'source.sqlite3';vault=SecretVault(None)
    original=vault.crypt(b'synthetic-windows-refresh')
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE integration_secrets(key TEXT PRIMARY KEY,ciphertext BLOB)')
        db.execute('INSERT INTO integration_secrets VALUES (?,?)',('synthetic',original))
    raw,key=portable_snapshot(snapshot(path));copy=tmp_path/'copy.sqlite3';copy.write_bytes(raw)
    with sqlite3.connect(copy) as db:
        value=db.execute('SELECT ciphertext FROM integration_secrets').fetchone()[0]
        assert Fernet(key).decrypt(value[len(b'JARVIS-FERNET-1\0'):])==b'synthetic-windows-refresh'
