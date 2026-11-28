"""Persistent remote commands with synthetic workers; never touch the real OS."""
from uuid import uuid4
import pytest
from server.automation.windows import HostPolicy
from server.automation.store import fingerprint
from tests.test_automation import automation as automation,submit
from tests.test_security import client_for
from tests.auth_helpers import TEST_PASSWORD
from tests.test_natural_presence import consent

N='/api/v1/natural';A='/api/v1/automation'

@pytest.fixture
def worker(automation):
    app,c,e=automation
    with client_for(app) as target:
        data=target.post('/api/v1/auth/desktop-login',json={'username':'owner','password':TEST_PASSWORD,'device_name':'Synthetic Worker','device_id':str(uuid4())}).json()
        target.headers['Authorization']='Bearer '+data['access_token']
        identifier=data['device_id']
        assert c.post(A+'/grants',json={'device_id':identifier,'scopes':['automation:read','automation:write']}).status_code==200
        policy=HostPolicy(enabled=True).model_dump(mode='json')
        consent(target,execution_allowed=True,execution_policy=policy)
        response=target.post(N+'/devices/heartbeat',json={'policy':policy});assert response.status_code==200,response.text
        yield app,c,e,target,identifier,policy


def queued(worker):
    app,c,e,target,identifier,policy=worker
    job=submit(c,'DeviceQuery',{'target_device':identifier,'operation':'DesktopRead','input':{'kind':'status'}}).json()
    c.portal.call(e.tick)
    assert e.store.get(job['id'])['status']=='waiting'
    return job


def test_claim_start_result_are_bound_and_idempotent(worker):
    app,c,e,target,identifier,policy=worker;job=queued(worker)
    item=target.post(N+'/devices/claim',json={}).json()['item'];assert item['tool']=='DesktopRead'
    path=N+'/devices/commands/'+item['id'];lease={'lease':item['lease']}
    assert c.post(path+'/start',json=lease).status_code==400
    assert target.post(path+'/start',json=lease).status_code==200
    assert target.post(path+'/start',json=lease).status_code==400
    outcome={**lease,'state':'completed','result':{'synthetic':True}}
    assert target.post(path+'/result',json=outcome).status_code==200
    assert target.post(path+'/result',json=outcome).json()['replayed']
    assert e.store.get(job['id'])['status']=='completed'
    assert target.post(N+'/devices/claim',json={}).json()['item'] is None


def test_started_lease_timeout_is_uncertain_and_never_replayed(worker):
    app,c,e,target,identifier,policy=worker;job=queued(worker)
    item=target.post(N+'/devices/claim',json={}).json()['item']
    assert target.post(N+'/devices/commands/'+item['id']+'/start',json={'lease':item['lease']}).status_code==200
    now=app.state.natural.store.clock();app.state.natural.store.clock=lambda:now+61
    assert target.post(N+'/devices/claim',json={}).json()['item'] is None
    assert e.store.get(job['id'])['status']=='uncertain'


def test_unstarted_lease_can_be_recovered_but_old_token_is_rejected(worker):
    app,c,e,target,identifier,policy=worker;queued(worker)
    first=target.post(N+'/devices/claim',json={}).json()['item']
    now=app.state.natural.store.clock();app.state.natural.store.clock=lambda:now+31
    second=target.post(N+'/devices/claim',json={}).json()['item'];assert second['id']==first['id'] and second['lease']!=first['lease']
    assert target.post(N+'/devices/commands/'+first['id']+'/start',json={'lease':first['lease']}).status_code==400


def test_target_consent_and_original_authority_are_rechecked(worker):
    app,c,e,target,identifier,policy=worker;queued(worker)
    consent(target,execution_allowed=False)
    assert target.post(N+'/devices/claim',json={}).status_code==400
    consent(target,execution_allowed=True)
    owner=c.get('/api/v1/auth/session').json()['device_id']
    with e.store.db(True) as db:db.execute("DELETE FROM auth_permissions WHERE device_id=? AND permission='automation:read'",(owner,))
    assert target.post(N+'/devices/claim',json={}).status_code==403


def test_write_requires_bound_approval_and_known_policy(worker):
    app,c,e,target,identifier,policy=worker
    payload={'target_device':identifier,'operation':'DesktopControl','input':{'action':'lock','policy_hash':fingerprint(policy)}}
    job=submit(c,'DeviceCommand',payload).json();assert job['status']=='approval'
    c.portal.call(e.tick);assert target.post(N+'/devices/claim',json={}).json()['item'] is None
    assert submit(c,'DeviceQuery',{**payload,'operation':'DesktopControl'}).status_code==400


def test_remote_status_query_does_not_require_write_permission(worker):
    app,c,e,target,identifier,policy=worker
    source=c.get('/api/v1/auth/session').json()['device_id']
    with e.store.db(True) as db:db.execute("DELETE FROM auth_permissions WHERE device_id=? AND permission='automation:write'",(source,))
    from dataclasses import replace
    app.state.chat.settings=replace(app.state.chat.settings,profile='mini-pc-production')
    response=c.post('/api/v1/chat',json={'message':'Toon de systeemstatus','provider':'ollama'})
    assert response.status_code==200,response.text
    job=e.store.items()[0]
    assert job['status']=='waiting',response.text
    assert target.post(N+'/devices/claim',json={}).json()['item']['tool']=='DesktopRead'
    assert e.store.get(job['id'])['approval_required']==0
