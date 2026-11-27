from types import SimpleNamespace
from uuid import uuid4
import sys
import pytest

from PySide6.QtCore import QObject
from jarvis_client.presence import PresenceController,classify_application
from jarvis_client.settings import Preferences


class Sampler:
    def __init__(self):self.hwnd=None;self.locked=False;self.samples=0
    def start(self,hwnd):self.hwnd=hwnd
    def stop(self):self.hwnd=None
    def sample(self,config,applications=False):
        self.samples+=1
        return {'locked':False,'idle_seconds':4,'hint':'gaming' if applications else 'normal'}


class Window(QObject):
    def __init__(self):
        super().__init__();self.principal={'device_id':'synthetic'};self.closing=False
        self.manager=SimpleNamespace(state='online');self.preferences=Preferences()
        self.saved=[];self.store=SimpleNamespace(save=lambda data:self.saved.append(list(data.presence_seen)))
        self.requests=[];self.notices=[];self.active=True
    def call(self,method,path,body,done,failure):self.requests.append((method,path,body,done))
    def winId(self):return 1
    def isActiveWindow(self):return self.active
    def show_notice(self,text):self.notices.append(text)


def test_application_names_are_classified_locally():
    config={'work_apps':['Code.exe'],'gaming_apps':['Game.exe']}
    assert classify_application(r'C:\Games\Game.exe',config)=='gaming'
    assert classify_application(r'C:\Editors\code.EXE',config)=='work'
    assert classify_application('other.exe',config)=='normal'


def test_no_os_sampling_without_consent_and_no_process_names_on_network(qt):
    window=Window();sampler=Sampler();controller=PresenceController(window,sampler)
    controller.config={'mode':'normal'}
    controller.document={'revision':1,'settings':{'presence_allowed':False}}
    controller.poll()
    assert sampler.samples==0 and window.requests[-1][1].endswith('/events')
    controller.busy=False;controller.document['settings'].update(presence_allowed=True,application_allowed=True)
    controller.poll()
    method,path,body,_=window.requests[-1]
    assert path.endswith('/presence/signals') and body=={'sequence':1,'locked':False,'idle_seconds':4,'hint':'gaming'}
    controller.config['mode']='private';controller.busy=False;controller.poll()
    assert sampler.samples==1
    controller.clear()


def test_return_event_receipt_is_persisted_before_display_and_ack(qt):
    window=Window();controller=PresenceController(window,Sampler())
    identifier=str(uuid4());event={'id':identifier,'payload':{'text':'Welkom terug.'}}
    controller.events({'items':[event]});controller.events({'items':[event]})
    assert window.saved==[[identifier]] and window.notices==['Welkom terug.']
    assert len(window.requests)==2 and all(row[1].endswith('/ack') for row in window.requests)
    window.store.save=lambda _:(_ for _ in ()).throw(OSError('Synthetic disk error'))
    failed={'id':str(uuid4()),'payload':{'text':'Niet tonen zonder ontvangstbewijs.'}}
    controller.events({'items':[failed]});controller.events({'items':[failed]})
    assert window.notices==['Welkom terug.'] and len(window.requests)==2
    controller.clear()


@pytest.mark.skipif(sys.platform!='win32',reason='Windows SDK WCHAR/DWORD layout')
@pytest.mark.parametrize('flag,expected',[(0,True),(1,False),(-1,None)])
def test_initial_windows_session_state_is_queried_and_freed(flag,expected):
    import ctypes
    from ctypes import wintypes
    from jarvis_client.presence import WindowsSignals
    # WTSINFOEXW: aligned union at 8, SessionFlags at 16, total 232 bytes.
    buffer=ctypes.create_string_buffer(232)
    wintypes.DWORD.from_buffer(buffer,0).value=1
    wintypes.LONG.from_buffer(buffer,16).value=flag
    freed=[]
    def query(server,session,kind,pointer,size):
        assert session==0xffffffff and kind==25
        ctypes.cast(pointer,ctypes.POINTER(ctypes.c_void_p))[0]=ctypes.addressof(buffer)
        ctypes.cast(size,ctypes.POINTER(wintypes.DWORD))[0]=232
        return 1
    def free(pointer):freed.append(pointer.value)
    library=SimpleNamespace(WTSQuerySessionInformationW=query,WTSFreeMemory=free)
    if expected is None:
        with pytest.raises(OSError):WindowsSignals.session_locked(library)
    else:assert WindowsSignals.session_locked(library) is expected
    assert freed==[ctypes.addressof(buffer)]
