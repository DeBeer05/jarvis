"""Synthetic grants/approvals and files; no programs, keys or power actions executed."""
import ctypes
import os
from pathlib import Path

import pytest

from server.automation.models import validate
from server.automation.windows import HostPolicy,MemoryStatus,WindowsHost,gpu_status
from tests.test_automation import automation as automation,submit


def approve(c,job):
    challenge=c.post(f"/api/v1/automation/jobs/{job['id']}/challenge").json()
    response=c.post(f"/api/v1/automation/jobs/{job['id']}/decision",json={'token':challenge['token'],'approve':True})
    assert response.status_code==200,response.text


def test_default_disabled_closed_inputs_and_admin_policy(automation,tmp_path):
    app,c,e=automation
    assert not c.get('/api/v1/automation/windows').json()['enabled']
    with pytest.raises(ValueError):e.windows.check()
    for payload in ({'action':'shell','path':'secret'},{'action':'lock','path':'secret'},{'action':'open_program'}):
        with pytest.raises(ValueError):validate('DesktopControl',payload)
    with pytest.raises(ValueError):HostPolicy(programs={'shell':str(tmp_path/'cmd.exe')})
    with pytest.raises(ValueError):HostPolicy(roots=[str(Path(tmp_path.anchor))])
    response=c.put('/api/v1/automation/windows',json={'enabled':False,'roots':[str(tmp_path)]})
    assert response.status_code==200 and response.json()['target']=='backend_host'


def test_document_boundary_and_bounded_read(automation,tmp_path,monkeypatch):
    _,_,e=automation
    root=tmp_path/'docs';root.mkdir();(root/'rapport.txt').write_text('synthetic')
    outside=tmp_path/'outside.txt';outside.write_text('private')
    (root/'run.exe').write_text('never executable')
    policy=HostPolicy(enabled=True,roots=[str(root)])
    monkeypatch.setattr(e.windows,'check',lambda:policy)
    result=e.windows.read({'kind':'files','query':'rapport'})
    assert [item['name'] for item in result['items']]==['rapport.txt']
    with pytest.raises(ValueError):e.windows.document(str(outside),policy)
    with pytest.raises(ValueError):e.windows.document(str(root/'run.exe'),policy)
    with pytest.raises(ValueError):e.windows.read({'kind':'files','query':''})
    def revoked():raise ValueError('revoked')
    with pytest.raises(ValueError):e.windows.read({'kind':'files','query':'rapport'},revoked)


def test_control_one_use_approval_uncertain_outcome_is_not_replayed(automation,monkeypatch):
    _,c,e=automation;calls=[]
    def control(payload,guard):guard();calls.append(payload);raise OSError('unknown OS outcome')
    monkeypatch.setattr(e.windows,'control',control)
    job=submit(c,'DesktopControl',{'action':'lock'}).json()
    assert job['status']=='approval' and len(job['payload']['policy_hash'])==64
    c.portal.call(e.tick);assert not calls
    approve(c,job);c.portal.call(e.tick);e.store.recover();c.portal.call(e.tick)
    assert len(calls)==1 and e.store.get(job['id'])['status']=='uncertain'
    with e.store.db(True) as db:db.execute("UPDATE automation_jobs SET status='running' WHERE id=?",(job['id'],))
    e.store.recover();assert e.store.get(job['id'])['status']=='uncertain'


def test_policy_change_invalidates_previous_control(automation,monkeypatch,tmp_path):
    _,c,e=automation
    policy=HostPolicy(enabled=True,roots=[str(tmp_path)])
    monkeypatch.setattr(e.windows,'check',lambda:policy)
    with pytest.raises(ValueError,match='configuratie'):
        e.windows.control({'action':'lock','policy_hash':'0'*64})


@pytest.mark.skipif(os.name!='nt',reason='Native Windows ABI only')
def test_native_read_only_status_has_correct_windows_memory_layout():
    assert ctypes.sizeof(MemoryStatus)==64
    data=WindowsHost.status()
    assert data['ram_total']>data['ram_available']>=0
    assert data['cpu_percent'] is None or 0<=data['cpu_percent']<=100
    if data['gpu']:
        assert all(item['source']=='nvml' for item in data['gpu'])
    assert data['cpu_temperature'] is None


def test_gpu_native_abi_with_mocked_driver_handles_unsupported_temperature():
    from types import SimpleNamespace
    calls=[]
    def initialize():return 0
    def count(pointer):pointer._obj.value=1;return 0
    def handle(index,pointer):pointer._obj.value=123;return 0
    def utilization(handle,pointer):pointer._obj.gpu=32;return 0
    def temperature(*_):return 3  # NVML_ERROR_NOT_SUPPORTED
    def shutdown():calls.append('shutdown');return 0
    library=SimpleNamespace(nvmlInit_v2=initialize,nvmlDeviceGetCount_v2=count,nvmlDeviceGetHandleByIndex_v2=handle,nvmlDeviceGetUtilizationRates=utilization,nvmlDeviceGetTemperature=temperature,nvmlShutdown=shutdown)
    assert gpu_status(library)==[{'index':0,'utilization':32,'temperature':None,'source':'nvml'}]
    assert calls==['shutdown']


def test_media_sdk_checks_delivery_and_uses_absolute_pause(automation,monkeypatch):
    from types import SimpleNamespace
    _,_,e=automation;calls=[]
    monkeypatch.setattr(e.windows,'check',e.windows.policy)
    def send(count,events,size):
        calls.append((events[0].value.key.vk,events[1].value.key.flags,size))
        return count
    def target():return 123
    def command(window,message,wparam,lparam,flags,timeout,result):
        calls.append(lparam);result._obj.value=1;return 1
    library=SimpleNamespace(SendInput=send,GetForegroundWindow=target,GetShellWindow=target,SendMessageTimeoutW=command)
    monkeypatch.setattr(ctypes,'WinDLL',lambda *args,**kwargs:library,raising=False)
    signature=e.windows.signature()
    assert e.windows.control({'action':'volume_up','policy_hash':signature})['state']=='media_key_delivered'
    assert calls[0][:2]==(0xAF,2)
    if os.name=='nt':assert calls[0][2]==(40 if ctypes.sizeof(ctypes.c_void_p)==8 else 28)
    assert e.windows.control({'action':'pause','policy_hash':signature})['handled']
    assert calls[-1]==47<<16
