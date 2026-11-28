"""Stop/restart, priorities and compensating proposals, with no real OS/API effects."""
import json
from tests.test_automation import automation as automation,submit
from tests.test_chat_automation import tools_chat as tools_chat,call


def test_stop_survives_recovery_and_requires_explicit_resume(automation):
    app,c,e=automation
    job=submit(c,'ReminderList',{}).json()
    assert c.post('/api/v1/automation/safety',json={'active':True}).status_code==200
    assert e.store.get(job['id'])['status']=='paused'
    e.store.recover();c.portal.call(e.tick)
    assert e.store.get(job['id'])['status']=='paused'
    assert submit(c,'ReminderList',{}).status_code==409
    assert c.post('/api/v1/automation/jobs/'+job['id']+'/control',json={'status':'queued'}).status_code==409
    assert c.get('/api/v1/natural/events').json()['items'][0]['kind']=='control.stop'
    assert c.post('/api/v1/automation/safety',json={'active':False}).status_code==200
    assert e.store.get(job['id'])['status']=='paused'
    assert c.post('/api/v1/automation/jobs/'+job['id']+'/control',json={'status':'queued'}).status_code==200
    c.portal.call(e.tick)
    assert e.store.get(job['id'])['status']=='completed'


def test_stop_invalidates_approvals_and_all_devices_receive_event(automation):
    app,c,e=automation
    proposal=submit(c,'DesktopControl',{'action':'lock'}).json()
    with e.store.db(True) as db:
        other=app.state.security.store._device(db,'Synthetic Windows','windows',{'chat:read'})
    assert c.post('/api/v1/automation/safety',json={'active':True}).status_code==200
    with e.store.db() as db:
        devices={r[0] for r in db.execute("SELECT device_id FROM natural_events WHERE kind='control.stop'")}
    assert other in devices and len(devices)>=2
    assert e.store.get(proposal['id'])['approval_hash'] is None
    assert e.store.get(proposal['id'])['status']=='paused'


def test_priorities_deadlines_and_no_repeated_write(automation):
    app,c,e=automation;calls=[]
    now=e.store.clock()
    from datetime import datetime,UTC
    deadline=datetime.fromtimestamp(now+60,UTC).isoformat()
    low=submit(c,'ReminderList',{},priority=0).json()
    high=submit(c,'ReminderList',{},priority=3).json()
    expiring=submit(c,'ReminderList',{},deadline=deadline).json()
    with e.store.db(True) as db:db.execute('UPDATE automation_jobs SET deadline=? WHERE id=?',(now-1,expiring['id']))
    async def execute(row):calls.append(row['id']);return {'ok':True}
    e.executor.execute=execute;c.portal.call(e.tick)
    assert calls==[high['id'],low['id']]
    assert e.store.get(expiring['id'])['status']=='expired'
    assert submit(c,'ReminderList',{},deadline='2020-01-01T00:00:00+00:00').status_code==400


def test_advice_does_not_execute_and_ask_requires_approval(automation):
    app,c,e=automation
    doc=c.get('/api/v1/natural/settings').json()
    doc['settings']['autonomy']['actions']={'ReminderList':'advise','NotificationSend':'ask'}
    assert c.put('/api/v1/natural/settings',json={'revision':doc['revision'],'settings':doc['settings']}).status_code==200
    advice=submit(c,'ReminderList',{}).json()
    asked=submit(c,'NotificationSend',{'text':'Synthetic','category':'important'}).json()
    c.portal.call(e.tick)
    assert e.store.get(advice['id'])['status']=='advisory'
    assert e.store.get(asked['id'])['status']=='approval'
    assert asked['approval_required']==1


def test_inflight_stop_remains_uncertain_and_is_not_retried(automation):
    app,c,e=automation
    principal=app.state.security.store.authenticate(c.cookies.get('jarvis_access'))
    job=submit(c,'EmailDraft',{'to':'test@example.invalid','subject':'Synthetic','text':'Synthetic'}).json()
    async def execute(row):
        # Simulate stop arriving after provider dispatch, before its response.
        await e.safety.set(principal,True)
        return {'verified':True}
    e.executor.execute=execute;c.portal.call(e.tick);c.portal.call(e.tick)
    assert e.store.get(job['id'])['status']=='uncertain'


def test_undo_calendar_is_new_exact_approval_and_rejects_changed_event(automation):
    app,c,e=automation
    payload={'summary':'Synthetic','start':'2027-01-01T14:00:00+01:00','end':'2027-01-01T15:00:00+01:00'}
    job=submit(c,'CalendarCreate',payload).json()
    with e.store.db(True) as db:db.execute("UPDATE automation_jobs SET status='completed',result=? WHERE id=?",(json.dumps({'id':'synthetic','etag':'version1'}),job['id']))
    async def api(*args,**kwargs):return {'id':'synthetic','etag':'version1'}
    e.integrations.api=api
    path='/api/v1/automation/jobs/'+job['id']+'/undo'
    undo=c.post(path);assert undo.status_code==200,undo.text
    assert undo.json()['tool']=='CalendarDelete' and undo.json()['status']=='approval'
    assert c.post(path).json()['id']==undo.json()['id']
    async def changed(*args,**kwargs):return {'id':'synthetic','etag':'version2'}
    e.integrations.api=changed
    assert c.post(path).status_code==400


def test_restricting_autonomy_after_enqueue_stops_execution(automation):
    _,c,e=automation
    job=submit(c,'ReminderList',{}).json()
    doc=c.get('/api/v1/natural/settings').json()
    doc['settings']['autonomy']['actions']={'ReminderList':'advise'}
    assert c.put('/api/v1/natural/settings',json={'revision':doc['revision'],'settings':doc['settings']}).status_code==200
    c.portal.call(e.tick)
    assert e.store.get(job['id'])['status']=='advisory'


def test_stop_events_are_delivered_when_notifications_are_disabled(automation):
    _,c,e=automation
    doc=c.get('/api/v1/natural/settings').json();doc['settings']['notifications']['enabled']=False
    assert c.put('/api/v1/natural/settings',json={'revision':doc['revision'],'settings':doc['settings']}).status_code==200
    assert c.post('/api/v1/automation/safety',json={'active':True}).status_code==200
    assert [item['kind'] for item in c.get('/api/v1/natural/events').json()['items']]==['control.stop']


def test_low_risk_autonomy_still_requires_separate_host_grant(automation,monkeypatch):
    _,c,e=automation;calls=[]
    doc=c.get('/api/v1/natural/settings').json()
    doc['settings']['autonomy']['profile']='within_rules'
    assert c.put('/api/v1/natural/settings',json={'revision':doc['revision'],'settings':doc['settings']}).status_code==200
    def control(payload,guard):guard();calls.append(payload);return {'state':'media_key_delivered'}
    monkeypatch.setattr(e.windows,'control',control)
    rejected=submit(c,'DesktopMedia',{'action':'pause'}).json()
    c.portal.call(e.tick)
    assert not calls and e.store.get(rejected['id'])['status']=='uncertain'
    e.store.set_preference('windows_host',{'media_allowed':True})
    accepted=submit(c,'DesktopMedia',{'action':'pause'}).json()
    c.portal.call(e.tick);c.portal.call(e.tick)
    assert len(calls)==1 and e.store.get(accepted['id'])['status']=='completed'


def test_spoken_stop_uses_no_model_and_chat_remains_available(tools_chat):
    app,c,router=tools_chat
    result=call(c,'JARVIS, noodstop').json()
    assert 'noodstop is actief' in result['message'] and not router.planning_calls
    assert c.get('/api/v1/automation/safety').json()['stopped']
    answer=call(c,'Goedemiddag',result['conversation_id']).json()
    assert answer['status']=='completed'
