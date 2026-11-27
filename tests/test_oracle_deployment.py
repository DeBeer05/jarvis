"""Deployment coordinator with fake service control and real encrypted rollback."""
from contextlib import closing
import sqlite3
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet
from scripts import deploy_release as deploy
from server.voice_secrets import save_secret


@pytest.fixture
def environment(tmp_path,monkeypatch):
    source=tmp_path/'jarvis.sqlite3'
    with closing(sqlite3.connect(source)) as db,db:
        db.execute('CREATE TABLE test(value TEXT)');db.execute("INSERT INTO test VALUES ('original')")
    env=tmp_path/'server.env';env.write_text('JARVIS_ENABLE_AUTOMATIONS=false\nJARVIS_DATABASE_PATH='+str(source)+'\n')
    key=tmp_path/'backup.key';save_secret(key,Fernet.generate_key().decode())
    ticket=tmp_path/'approval.json';ticket.write_text('{}')
    old=tmp_path/'old';old.mkdir();candidate=tmp_path/'candidate';candidate.mkdir()
    current=SimpleNamespace(resolve=lambda **kwargs:state['release'])
    state={'release':old,'commands':[],'starts':0}
    class Base:
        def __truediv__(self,name):
            assert name=='current';return current
    for name,value in {'BASE':Base(),'ENV':env,'DATA':source,'BACKUPS':tmp_path/'backups','KEY':key,'TICKET':ticket}.items():monkeypatch.setattr(deploy,name,value)
    monkeypatch.setattr(deploy,'switch',lambda current,release:state.update(release=release))
    monkeypatch.setattr(deploy.shutil,'chown',lambda *args,**kwargs:None,raising=False)
    def run(*args):
        state['commands'].append(args)
        if args[:2]==('systemctl','start'):
            state['starts']+=1
            if state['release']==candidate:
                with closing(sqlite3.connect(source)) as db,db:db.execute("UPDATE test SET value='candidate-migration'")
        return ''
    monkeypatch.setattr(deploy,'run',run)
    return SimpleNamespace(state=state,source=source,env=env,ticket=ticket,old=old,candidate=candidate)


def test_success_stays_fenced_and_consumes_exact_ticket(environment,monkeypatch):
    monkeypatch.setattr(deploy,'healthy',lambda:True)
    deploy.promote(environment.candidate,'a'*40)
    assert environment.state['release']==environment.candidate
    assert not environment.ticket.exists()
    assert 'JARVIS_ENABLE_AUTOMATIONS=false' in environment.env.read_text()


def test_failed_health_restores_old_release_and_database(environment,monkeypatch):
    results=iter([False,True]);monkeypatch.setattr(deploy,'healthy',lambda:next(results))
    with pytest.raises(RuntimeError,match='old release and database restored'):
        deploy.promote(environment.candidate,'b'*40)
    assert environment.state['release']==environment.old
    with closing(sqlite3.connect(environment.source)) as db:
        assert db.execute('SELECT value FROM test').fetchone()[0]=='original'
    assert environment.ticket.exists() and environment.state['starts']==2


def test_unfenced_deployment_is_rejected_without_service_changes(environment):
    environment.env.write_text(environment.env.read_text().replace('=false','=true'))
    with pytest.raises(ValueError,match='Maintenance fence'):deploy.promote(environment.candidate,'c'*40)
    assert environment.state['commands']==[]


def test_maintenance_fence_uses_real_backend_setting(environment):
    from server.config import load_settings
    settings=load_settings(root=environment.env.parent,env_file=environment.env,environ={})
    assert settings.automations_enabled is False


def test_deployment_template_disables_real_scheduler(tmp_path):
    from pathlib import Path
    from server.config import load_settings
    template=Path(__file__).resolve().parents[1]/'deploy/oracle/server.env.example'
    settings=load_settings(root=tmp_path,env_file=template,environ={'ELEVENLABS_API_KEY_FILE':''})
    assert settings.automations_enabled is False
    assert settings.profile=='oracle-production' and settings.cookie_secure=='true'


def test_invalid_approval_never_starts_commands(tmp_path,monkeypatch):
    import os
    if os.name=='nt':pytest.skip('POSIX ownership/modes are checked in Linux CI')
    ticket=tmp_path/'approval.json';ticket.write_text('{}');ticket.chmod(0o666)
    monkeypatch.setattr(deploy,'run',lambda *args:pytest.fail('No command allowed'))
    with pytest.raises(ValueError,match='root-controlled'):deploy.approved_release(ticket,tmp_path)
