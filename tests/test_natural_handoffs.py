"""No real calls/messages. A handoff is explicitly different from sending."""
import pytest

from tests.test_automation import automation as automation,submit
from tests.test_windows_host import approve
from tests.test_natural_presence import consent
from server.automation.models import validate
from tests.test_chat_automation import tools_chat as tools_chat,call


def test_phone_handoff_requires_target_consent_and_is_one_use(automation):
    app,c,e=automation
    principal=c.get('/api/v1/auth/session').json()
    device=principal['device_id']
    # Synthetic browser fixture becomes a paired Android for this protocol test.
    with e.store.db(True) as db:db.execute("UPDATE auth_devices SET type='android' WHERE id=?",(device,))
    request={'target_device':device,'action':'dial','target':'+31612345678'}
    assert c.get('/api/v1/natural/mobile-handoffs').status_code==400
    consent(c,handoff_allowed=True)
    job=submit(c,'MobileHandoff',request).json();assert job['status']=='approval'
    approve(c,job);c.portal.call(e.tick)
    assert e.store.get(job['id'])['status']=='waiting'
    items=c.get('/api/v1/natural/mobile-handoffs').json()['items']
    assert len(items)==1 and items[0]['request']['target']==request['target']
    assert not c.get('/api/v1/natural/events').json()['items']
    route='/api/v1/natural/mobile-handoffs/'+items[0]['id']+'/result'
    first=c.post(route,json={'state':'handed_off'})
    assert first.status_code==200 and first.json()['called'] is False
    assert c.post(route,json={'state':'handed_off'}).json()['replayed']
    assert e.store.get(job['id'])['status']=='completed'
    assert not c.get('/api/v1/natural/mobile-handoffs').json()['items']


def test_source_revocation_hides_waiting_handoff_and_payload_is_closed(automation):
    app,c,e=automation;device=c.get('/api/v1/auth/session').json()['device_id']
    with e.store.db(True) as db:db.execute("UPDATE auth_devices SET type='android' WHERE id=?",(device,))
    consent(c,handoff_allowed=True)
    job=submit(c,'MobileHandoff',{'target_device':device,'action':'navigate','target':'Utrecht'}).json()
    approve(c,job);c.portal.call(e.tick)
    e.store.set_preference('disabled_tools',['MobileHandoff'])
    assert not c.get('/api/v1/natural/mobile-handoffs').json()['items']
    e.store.set_preference('disabled_tools',[])
    response=submit(c,'WorkflowCreate',{'title':'Synthetic parent','steps':[{'tool':'ReminderList','input':{}}]})
    assert response.status_code==200,response.text
    parent=response.json()
    with e.store.db(True) as db:
        db.execute("UPDATE automation_jobs SET status='cancelled' WHERE id=?",(parent['id'],))
        db.execute('UPDATE automation_jobs SET parent_id=? WHERE id=?',(parent['id'],job['id']))
    assert not c.get('/api/v1/natural/mobile-handoffs').json()['items']
    app.state.natural.store.clock=lambda:e.store.clock()+200
    app.state.natural.retention.sweep()
    assert e.store.get(job['id'])['status']=='uncertain'
    for request in ({'action':'call','target':'123'},{'action':'dial','target':'123;cmd'},{'action':'signal','target':'unknown'}):
        with pytest.raises(ValueError):validate('MobileHandoff',{'target_device':device,**request})


def test_desktop_chat_prepares_exact_job_without_model_or_execution(tools_chat,tmp_path,monkeypatch):
    app,c,router=tools_chat;e=app.state.automation
    from server.automation.windows import HostPolicy
    e.store.set_preference('windows_host',HostPolicy(enabled=True,programs={'kladblok':str(tmp_path/'notepad.exe')}).model_dump(mode='json'))
    monkeypatch.setattr(e.windows,'check',e.windows.policy)
    response=call(c,'Open kladblok.').json()
    assert response['status']=='completed' and 'voorstel' in response['message']
    jobs=e.store.items();assert len(jobs)==1 and jobs[0]['status']=='approval' and jobs[0]['tool']=='DesktopControl'
    assert not router.planning_calls and not any(provider.calls for provider in router.providers.values())


def test_download_changes_are_events_not_model_calls(automation,tmp_path,monkeypatch):
    app,c,e=automation;root=tmp_path/'Downloads';root.mkdir()
    from server.automation.windows import HostPolicy
    e.store.set_preference('windows_host',HostPolicy(enabled=True,roots=[str(root)],watch_downloads=True).model_dump(mode='json'))
    e.store.set_preference('windows_watch_owner',c.get('/api/v1/auth/session').json()['device_id'])
    monkeypatch.setattr(e.windows,'check',e.windows.policy)
    now=[e.store.clock()];e.store.clock=lambda:now[0]
    e.desktop_monitor();assert not c.get('/api/v1/natural/events').json()['items']
    (root/'synthetic.txt').write_text('example');now[0]+=31
    e.desktop_monitor();e.desktop_monitor()
    items=c.get('/api/v1/natural/events').json()['items']
    assert len(items)==1 and 'synthetic.txt' in items[0]['payload']['text']
