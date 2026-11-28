"""Device worker integration with real receipts and a mocked host/network."""
from types import SimpleNamespace
import time
from PySide6.QtCore import QObject
from jarvis_client.device_worker import DeviceWorker

class API:
    def __init__(self,enabled=True):self.enabled=enabled;self.calls=[]
    def request(self,method,path,body=None):
        self.calls.append((path,body))
        if path.endswith('/device-settings'):return {'settings':{'execution_allowed':self.enabled,'execution_policy':{'enabled':True}}}
        if path.endswith('/claim'):return {'item':{'id':'synthetic-command','lease':'synthetic-lease','tool':'DesktopRead','input':{'kind':'status'},'expires':time.time()+120}}
        return {'acknowledged':True}

class Jobs:
    def submit(self,work,done,failed):
        try:done(work(None))
        except Exception as error:failed(error)

class Window(QObject):
    def __init__(self,path,api):
        super().__init__();self.store=SimpleNamespace(directory=path);self.jobs=Jobs();self.principal={'device_id':'synthetic'};self.manager=SimpleNamespace(state='online',api=api);self.closing=False;self.notices=[]
    def show_notice(self,text):self.notices.append(text)


def test_receipt_prevents_a_second_os_execution_after_repeated_delivery(qt,tmp_path,monkeypatch):
    from server.automation.windows import WindowsHost
    calls=[]
    def read(self,args,guard):guard();calls.append(args);return {'synthetic':True}
    monkeypatch.setattr(WindowsHost,'read',read)
    api=API();window=Window(tmp_path,api);worker=DeviceWorker(window);worker.timer.stop()
    worker.poll();worker.poll()
    assert len(calls)==1 and worker.receipts.get('synthetic-command')==('completed',{'synthetic':True})
    assert sum(path.endswith('/start') for path,_ in api.calls)==1


def test_disabled_receiving_performs_no_claim_or_execution(qt,tmp_path):
    api=API(False);window=Window(tmp_path,api);worker=DeviceWorker(window);worker.timer.stop();worker.poll()
    assert len(api.calls)==1 and not (tmp_path/'device-receipts.sqlite3').exists()


def test_unknown_operation_is_rejected_before_start(qt,tmp_path):
    api=API();request=api.request
    def corrupted(method,path,body=None):
        result=request(method,path,body)
        if path.endswith('/claim'):result['item']['tool']='shell'
        return result
    api.request=corrupted
    window=Window(tmp_path,api);worker=DeviceWorker(window);worker.timer.stop();worker.poll()
    assert not any(path.endswith('/start') for path,_ in api.calls) and window.notices
