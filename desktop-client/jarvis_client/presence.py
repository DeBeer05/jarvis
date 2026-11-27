"""Opt-in Windows signals and a quiet durable event inbox; no model polling."""
import os
from pathlib import PureWindowsPath

from PySide6.QtCore import QObject,QTimer,Signal
from PySide6.QtWidgets import QWidget,QVBoxLayout,QCheckBox,QPushButton,QLabel

BASE='/api/v1/natural'


def classify_application(name,config):
    value=PureWindowsPath(name or '').name.casefold()
    if value and value in {item.casefold() for item in config.get('gaming_apps',[])}:return 'gaming'
    if value and value in {item.casefold() for item in config.get('work_apps',[])}:return 'work'
    return 'normal'


class WindowsSignals:
    def __init__(self):self.hwnd=None;self.locked=False

    @staticmethod
    def session_locked(library):
        import ctypes
        from ctypes import wintypes
        class Level1(ctypes.Structure):
            _fields_=[('session',wintypes.ULONG),('state',ctypes.c_int),('flags',wintypes.LONG),
                      ('names',wintypes.WCHAR*72),('times',ctypes.c_longlong*5),('counts',wintypes.DWORD*6)]
        class Data(ctypes.Union):
            _fields_=[('level1',Level1)]
        class Info(ctypes.Structure):
            _fields_=[('level',wintypes.DWORD),('data',Data)]
        buffer=ctypes.c_void_p();size=wintypes.DWORD()
        library.WTSQuerySessionInformationW.argtypes=[wintypes.HANDLE,wintypes.DWORD,ctypes.c_int,ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(wintypes.DWORD)]
        library.WTSFreeMemory.argtypes=[ctypes.c_void_p]
        try:
            if not library.WTSQuerySessionInformationW(None,0xffffffff,25,ctypes.byref(buffer),ctypes.byref(size)):
                raise ctypes.WinError(ctypes.get_last_error())
            if not buffer.value or size.value<ctypes.sizeof(Info):raise OSError('Onvolledige WTS-sessiestatus')
            value=Info.from_buffer_copy(ctypes.string_at(buffer,ctypes.sizeof(Info)))
            if value.level!=1 or value.data.level1.flags not in (0,1):raise OSError('WTS-vergrendeling onbekend')
            return value.data.level1.flags==0
        finally:
            if buffer.value:library.WTSFreeMemory(buffer)

    def start(self,hwnd):
        if os.name!='nt':raise OSError('Windows-aanwezigheid is op dit platform niet beschikbaar')
        import ctypes
        from ctypes import wintypes
        library=ctypes.WinDLL('wtsapi32',use_last_error=True)
        library.WTSRegisterSessionNotification.argtypes=[wintypes.HWND,wintypes.DWORD]
        if not library.WTSRegisterSessionNotification(hwnd,0):raise ctypes.WinError(ctypes.get_last_error())
        self.hwnd=hwnd
        try:self.locked=self.session_locked(library)
        except OSError:self.stop();raise

    def stop(self):
        if self.hwnd and os.name=='nt':
            import ctypes
            from ctypes import wintypes
            library=ctypes.WinDLL('wtsapi32',use_last_error=True)
            library.WTSUnRegisterSessionNotification.argtypes=[wintypes.HWND]
            library.WTSUnRegisterSessionNotification(self.hwnd)
        self.hwnd=None

    def event(self,message):
        if not self.hwnd or os.name!='nt':return False
        from ctypes import wintypes
        value=wintypes.MSG.from_address(int(message))
        if value.message!=0x02B1:return False  # WM_WTSSESSION_CHANGE
        if value.wParam in (2,4,7):self.locked=True;return True
        if value.wParam in (1,3,8):self.locked=False;return True
        return False

    def sample(self,config,applications=False):
        if not self.hwnd:raise OSError('Aanwezigheidsmeting is niet ingeschakeld')
        import ctypes
        from ctypes import wintypes
        class LastInput(ctypes.Structure):
            _fields_=[('cbSize',wintypes.UINT),('dwTime',wintypes.DWORD)]
        user=ctypes.WinDLL('user32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        value=LastInput();value.cbSize=ctypes.sizeof(value)
        if not user.GetLastInputInfo(ctypes.byref(value)):raise ctypes.WinError(ctypes.get_last_error())
        idle=min(86400,((kernel.GetTickCount()-value.dwTime)&0xffffffff)//1000)
        hint='normal'
        if applications and not self.locked:
            user.GetForegroundWindow.restype=wintypes.HWND
            hwnd=user.GetForegroundWindow();pid=wintypes.DWORD()
            user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
            user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
            kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
            kernel.OpenProcess.restype=wintypes.HANDLE
            handle=kernel.OpenProcess(0x1000,False,pid.value)
            if handle:
                try:
                    name=ctypes.create_unicode_buffer(32768);size=wintypes.DWORD(len(name))
                    kernel.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
                    if kernel.QueryFullProcessImageNameW(handle,0,name,ctypes.byref(size)):
                        hint=classify_application(name.value,config)
                finally:
                    kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle(handle)
        return {'locked':self.locked,'idle_seconds':idle,'hint':hint}


class PresenceController(QObject):
    changed=Signal(str)
    device_loaded=Signal(dict)

    def __init__(self,window,sampler=None):
        super().__init__(window);self.window=window;self.sampler=sampler or WindowsSignals()
        self.document=None;self.config=None;self.sequence=0;self.busy=False;self.paused=False
        self.timer=QTimer(self);self.timer.setInterval(15000);self.timer.timeout.connect(self.poll)

    def clear(self):
        self.timer.stop();self.sampler.stop();self.document=None;self.config=None;self.busy=False

    def configure(self,settings):
        self.config=settings.get('presence')
        if self.config is None:self.clear();return
        if self.config.get('mode')=='private':self.sampler.stop()
        if not self.timer.isActive():self.timer.start()
        if self.document is None:self.refresh()

    def failed(self,error):
        self.busy=False;self.sampler.stop();self.document=None
        self.changed.emit('Aanwezigheid niet bijgewerkt; controleer verbinding en toestemming.')

    def request(self,method,path,body,done):
        self.window.call(method,BASE+path,body,done,self.failed)

    def refresh(self):
        if not self.window.principal or self.window.closing or self.busy:return
        self.busy=True;self.request('GET','/device-settings',None,self.loaded)

    def loaded(self,document):
        self.document=document;self.paused=False;self.device_loaded.emit(document)
        enabled=document['settings'].get('presence_allowed',False) and (self.config or {}).get('mode')!='private'
        if not enabled:self.sampler.stop()
        elif not self.sampler.hwnd:
            try:self.sampler.start(int(self.window.winId()))
            except OSError as error:self.failed(error);return
        self.request('GET','/presence',None,self.ready)

    def ready(self,state):
        self.sequence=state.get('sequence',0);self.busy=False
        self.changed.emit('Modus: '+state.get('label','Onbekend'))
        self.poll()

    def native_event(self,message):
        if self.sampler.event(message):self.poll()

    def poll(self):
        if self.busy or not self.config or not self.window.principal or self.window.closing or self.window.manager.state!='online':return
        self.busy=True
        if self.document and self.document['settings'].get('presence_allowed') and not self.paused and self.config.get('mode')!='private':
            if not self.sampler.hwnd:
                try:self.sampler.start(int(self.window.winId()))
                except OSError as error:self.failed(error);return
            try:
                sample=self.sampler.sample(self.config,self.document['settings'].get('application_allowed',False))
            except OSError as error:self.failed(error);return
            self.sequence+=1
            self.request('POST','/presence/signals',{'sequence':self.sequence,**sample},self.reported)
        else:self.reported({})

    def reported(self,state):
        if state:self.changed.emit('Modus: '+state.get('label','Onbekend'))
        if self.window.isActiveWindow() and not self.sampler.locked:
            self.request('GET','/events',None,self.events)
        else:self.busy=False

    def events(self,result):
        self.busy=False
        for item in result.get('items',[]):
            identifier=item['id'];seen=self.window.preferences.presence_seen
            if identifier not in seen:
                self.window.preferences.presence_seen=(seen+[identifier])[-200:]
                try:self.window.store.save(self.window.preferences)
                except (OSError,ValueError):
                    self.window.preferences.presence_seen=seen
                    self.changed.emit('Melding nog niet getoond: ontvangstbewijs kon niet worden opgeslagen.');return
                text=item.get('payload',{}).get('text','')
                if text:self.window.show_notice(text)  # quiet, visible app only; no TTS or OS toast
            self.request('POST','/events/'+identifier+'/ack',None,lambda _:None)


class PresencePanel(QWidget):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.document=None;self.loading=False
        layout=QVBoxLayout(self)
        self.status=QLabel('Log in om apparaatstatus te beheren.');self.status.setWordWrap(True);layout.addWidget(self.status)
        explanation=QLabel('Delen staat standaard uit. Alleen vergrendeling, inactiviteit en eventueel werk-/gameclassificatie worden gedeeld. Geen toetsen, venstertitels, procesnamen of schermbeelden. Globale modi staan onder Gespreksinstellingen → Aanwezigheid en modi.')
        explanation.setWordWrap(True);layout.addWidget(explanation)
        self.share=QCheckBox('Aanwezigheidsstatus van deze Windows-sessie delen')
        self.apps=QCheckBox('Actief programma lokaal met mijn werk-/gamelijst vergelijken')
        layout.addWidget(self.share);layout.addWidget(self.apps)
        save=QPushButton('Apparaattoestemming opslaan');save.clicked.connect(self.save);layout.addWidget(save)
        refresh=QPushButton('Vernieuwen');refresh.clicked.connect(window.presence.refresh);layout.addWidget(refresh)
        layout.addStretch()
        window.presence.changed.connect(self.status.setText);window.presence.device_loaded.connect(self.loaded)
        self.share.toggled.connect(self.toggled)

    def clear(self):
        self.document=None;self.loading=True
        self.share.setChecked(False);self.apps.setChecked(False);self.apps.setEnabled(False)
        self.status.setText('Log in om apparaatstatus te beheren.');self.loading=False

    def toggled(self,value):
        self.apps.setEnabled(value)
        if not self.loading and not value:
            self.window.presence.paused=True;self.window.presence.sampler.stop()

    def loaded(self,document):
        self.document=document;self.loading=True
        self.share.setChecked(document['settings'].get('presence_allowed',False))
        self.apps.setChecked(document['settings'].get('application_allowed',False))
        self.apps.setEnabled(self.share.isChecked());self.loading=False

    def save(self):
        if not self.document or not self.window.principal:return
        data={**self.document['settings'],'presence_allowed':self.share.isChecked(),'application_allowed':self.apps.isChecked() and self.share.isChecked()}
        self.window.presence.request('PUT','/device-settings',{'revision':self.document['revision'],'settings':data},self.window.presence.loaded)
