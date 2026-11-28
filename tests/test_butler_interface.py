"""Actual authenticated endpoints backing both clients; no external calls."""
from tests.test_automation import automation as automation


def test_history_keeps_receipts_but_never_crosses_owner_device(automation):
    app,c,e=automation;principal=app.state.security.store.authenticate(c.cookies.get('jarvis_access'))
    with e.store.db(True) as db:
        user=db.execute('SELECT user_id FROM auth_devices WHERE id=?',(principal.device_id,)).fetchone()[0]
        other=app.state.security.store._device(db,'Synthetic second client','windows',{'chat:read'})
        identifier=app.state.natural.events.publish(db,user,principal.device_id,'task.changed',{'text':'Synthetic own notice'},'synthetic-own')
        app.state.natural.events.publish(db,user,other,'task.changed',{'text':'Synthetic other-device notice'},'synthetic-other')
    assert c.post('/api/v1/natural/events/'+identifier+'/ack').status_code==200
    assert not c.get('/api/v1/natural/events').json()['items']
    assert [item['payload']['text'] for item in c.get('/api/v1/natural/events?history=true').json()['items']]==['Synthetic own notice']


def test_host_policy_requires_actual_owner_permission(automation):
    app,c,e=automation;principal=app.state.security.store.authenticate(c.cookies.get('jarvis_access'))
    assert c.get('/api/v1/automation/windows/policy').json()['media_allowed'] is False
    with e.store.db(True) as db:db.execute("DELETE FROM auth_permissions WHERE device_id=? AND permission='admin:account'",(principal.device_id,))
    assert c.get('/api/v1/automation/windows/policy').status_code==403
    assert c.post('/api/v1/automation/safety',json={'active':True}).status_code==200
    assert c.post('/api/v1/automation/safety',json={'active':False}).status_code==403


def test_owner_forms_never_grant_on_load_and_do_not_fake_rejected_resume():
    import shutil
    import subprocess
    from pathlib import Path
    import pytest
    node=shutil.which('node')
    if not node:pytest.skip('Node required for browser DOM contract')
    root=Path(__file__).resolve().parents[1]
    result=subprocess.run([node,str(root/'tests/js/butler_controls.cjs'),str(root/'server/static/automations.js')],capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stderr
