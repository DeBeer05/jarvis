"""Opt-in Windows host adapter. Closed operations; no generated commands or Qt."""
import ctypes
from ctypes import wintypes
import logging
import hashlib
import os
from pathlib import Path
import subprocess
import threading
import time
from functools import lru_cache

from pydantic import Field,model_validator
from server.automation.models import Input
from server.automation.store import fingerprint

log=logging.getLogger('jarvis.server')
DOCUMENTS={'.txt','.md','.pdf','.docx','.xlsx','.csv','.png','.jpg','.jpeg'}
INTERPRETERS={'cmd.exe','powershell.exe','pwsh.exe','python.exe','pythonw.exe','node.exe','wscript.exe','cscript.exe','mshta.exe','rundll32.exe','regsvr32.exe','bash.exe'}


class HostPolicy(Input):
    enabled:bool=False
    programs:dict[str,str]=Field(default_factory=dict,max_length=20)
    roots:list[str]=Field(default_factory=list,max_length=10)
    watch_downloads:bool=False
    media_allowed:bool=False
    programs_allowed:bool=False
    notify_device:str=Field(default='',pattern=r'^(?:[0-9a-f-]{36})?$')
    @model_validator(mode='after')
    def paths(self):
        import re
        if any(not re.fullmatch(r'[\w -]{1,50}',name) for name in self.programs):raise ValueError('Gebruik korte programmanamen')
        if len({name.casefold() for name in self.programs})!=len(self.programs):raise ValueError('Programmanamen moeten ook zonder hoofdletters uniek zijn')
        for raw in [*self.programs.values(),*self.roots]:
            if len(raw)>400 or '\x00' in raw or raw.startswith(('\\\\','//')) or not Path(raw).is_absolute():raise ValueError('Alleen expliciete lokale absolute paden')
        if any(Path(path).suffix.casefold()!='.exe' or Path(path).name.casefold() in INTERPRETERS for path in self.programs.values()):raise ValueError('Geen interpreters of opdrachtverwerkers')
        if any(str(Path(root))==Path(root).anchor for root in self.roots):raise ValueError('Kies een specifieke documentenmap')
        if self.watch_downloads and not any(Path(root).name.casefold()=='downloads' for root in self.roots):raise ValueError('Kies expliciet uw Downloads-map om te monitoren')
        return self


class MemoryStatus(ctypes.Structure):
    _fields_=[('length',wintypes.DWORD),('load',wintypes.DWORD),
              *[(name,ctypes.c_ulonglong) for name in ('physical','available','page','page_available','virtual','virtual_available','extended')]]


class GPUUtilization(ctypes.Structure):
    _fields_=[('gpu',ctypes.c_uint),('memory',ctypes.c_uint)]


@lru_cache(maxsize=1)
def nvml_library():
    if os.name!='nt':return None
    path=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32/nvml.dll'
    if not path.is_file():return None
    try:return ctypes.CDLL(str(path))
    except OSError:return None


def gpu_status(library=None):
    library=library or nvml_library()
    if library is None:return None
    initialized=False
    try:
        library.nvmlInit_v2.restype=ctypes.c_int
        if library.nvmlInit_v2()!=0:return None
        initialized=True;count=ctypes.c_uint()
        library.nvmlDeviceGetCount_v2.argtypes=[ctypes.POINTER(ctypes.c_uint)]
        library.nvmlDeviceGetHandleByIndex_v2.argtypes=[ctypes.c_uint,ctypes.POINTER(ctypes.c_void_p)]
        library.nvmlDeviceGetUtilizationRates.argtypes=[ctypes.c_void_p,ctypes.POINTER(GPUUtilization)]
        if library.nvmlDeviceGetCount_v2(ctypes.byref(count))!=0:return None
        devices=[]
        for index in range(min(count.value,8)):
            handle=ctypes.c_void_p()
            if library.nvmlDeviceGetHandleByIndex_v2(index,ctypes.byref(handle))!=0:continue
            utilization=GPUUtilization();temperature=ctypes.c_uint();degrees=None
            busy=library.nvmlDeviceGetUtilizationRates(handle,ctypes.byref(utilization))==0
            # Older installed drivers expose this stable ABI; if removed or not
            # supported, temperature stays unavailable rather than being guessed.
            if hasattr(library,'nvmlDeviceGetTemperature'):
                library.nvmlDeviceGetTemperature.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.POINTER(ctypes.c_uint)]
                if library.nvmlDeviceGetTemperature(handle,0,ctypes.byref(temperature))==0 and temperature.value<=150:degrees=temperature.value
            devices.append({'index':index,'utilization':utilization.gpu if busy and utilization.gpu<=100 else None,'temperature':degrees,'source':'nvml'})
        return devices or None
    except (OSError,AttributeError):return None
    finally:
        if initialized:
            try:library.nvmlShutdown()
            except (OSError,AttributeError):pass


class WindowsHost:
    def __init__(self,store):self.store=store;self.last_scan=0.;self.scan_policy=None;self.downloads=None

    def changed_downloads(self):
        """Cheap bounded source sampling; changes become events, never LLM polls."""
        policy=self.check();now=self.store.clock();signature=self.signature()
        if not policy.watch_downloads:self.downloads=None;return []
        if now-self.last_scan<30 and self.scan_policy==signature:return []
        self.last_scan=now;snapshot={}
        for raw in policy.roots:
            root=Path(raw).resolve(strict=True)
            if root.name.casefold()!='downloads':continue
            with os.scandir(root) as entries:
                for index,entry in enumerate(entries):
                    if index>=2000:break
                    if not entry.is_file(follow_symlinks=False):continue
                    info=entry.stat(follow_symlinks=False)
                    key=hashlib.sha256(str(Path(entry.path).resolve()).encode()).hexdigest()
                    snapshot[key]=(info.st_mtime_ns,info.st_size,entry.name)
        baseline=self.downloads if self.scan_policy==signature else None
        self.downloads=snapshot;self.scan_policy=signature
        if baseline is None:return []
        return [{'key':key+':'+str(value[0])+':'+str(value[1]),'name':value[2].replace('\r',' ').replace('\n',' ')[:150]} for key,value in snapshot.items() if baseline.get(key)!=value][:5]

    def policy(self):return HostPolicy.model_validate(self.store.preference('windows_host',{}))

    def signature(self):return fingerprint(self.policy().model_dump(mode='json'))

    def capabilities(self):
        gpu=gpu_status() if self.policy().enabled and os.name=='nt' else None
        return {'supported':os.name=='nt','enabled':self.policy().enabled,'target':'backend_host','policy_hash':self.signature(),
                'cpu':os.name=='nt','ram':os.name=='nt','gpu':bool(gpu),'temperature':bool(gpu and any(item['temperature'] is not None for item in gpu)),
                'sensor_reason':'GPU/temperatuur via aanwezige NVIDIA NVML-driver; overige sensoren niet beschikbaar. Geen driver wordt geïnstalleerd.',
                'programs':list(self.policy().programs),'roots_configured':len(self.policy().roots)}

    def check(self):
        if os.name!='nt':raise ValueError('De backendhost is geen Windows-computer')
        policy=self.policy()
        if not policy.enabled:raise ValueError('Windows-hostbediening is niet door de eigenaar ingeschakeld')
        return policy

    @staticmethod
    def document(raw,policy):
        path=Path(raw).resolve(strict=True)
        roots=[Path(root).resolve(strict=True) for root in policy.roots]
        if not path.is_file() or path.suffix.casefold() not in DOCUMENTS or not any(path.is_relative_to(root) for root in roots):raise ValueError('Document valt buiten de toegestane mappen of bestandstypen')
        return path

    def read(self,payload,guard=lambda:None):
        policy=self.check();guard()
        if payload['kind']=='status':return self.status()
        query=payload.get('query','').casefold()
        if payload['kind']=='files' and len(query)<2:raise ValueError('Geef minstens twee letters van de bestandsnaam')
        items:list[dict]=[];visited=0;scanned=0
        for raw in policy.roots:
            root=Path(raw).resolve(strict=True)
            if payload['kind']=='downloads' and root.name.casefold()!='downloads':continue
            for parent,dirs,files in os.walk(root,followlinks=False):
                dirs[:]=[name for name in dirs if not name.startswith('.')]
                visited+=1
                if visited>500:return {'items':items,'truncated':True}
                for name in files:
                    scanned+=1
                    if scanned>5000:return {'items':items,'truncated':True}
                    if query and query not in name.casefold():continue
                    try:
                        path=self.document(str(Path(parent)/name),policy)
                        stat=path.stat();items.append({'name':path.name,'path':str(path),'bytes':stat.st_size,'modified':stat.st_mtime})
                    except (OSError,ValueError):continue
                    if len(items)>=50:return {'items':items,'truncated':True}
        guard();return {'items':sorted(items,key=lambda item:item['modified'],reverse=True),'truncated':False}

    @staticmethod
    def status():
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        memory=MemoryStatus();memory.length=ctypes.sizeof(memory)
        if not kernel.GlobalMemoryStatusEx(ctypes.byref(memory)):raise OSError('RAM-status niet beschikbaar')
        def times():
            values=[wintypes.FILETIME() for _ in range(3)]
            if not kernel.GetSystemTimes(*(ctypes.byref(value) for value in values)):raise OSError('CPU-status niet beschikbaar')
            return [value.dwLowDateTime+(value.dwHighDateTime<<32) for value in values]
        before=times();time.sleep(.15);after=times();delta=[b-a for a,b in zip(before,after)];total=delta[1]+delta[2]
        gpu=gpu_status();temperatures=[item['temperature'] for item in gpu or [] if item['temperature'] is not None]
        return {'target':'backend_host','cpu_percent':round(100*(1-delta[0]/total),1) if total else None,
                'ram_total':memory.physical,'ram_available':memory.available,'gpu':gpu,'temperature':max(temperatures) if temperatures else None,'cpu_temperature':None}

    def control(self,payload,guard=lambda:None):
        policy=self.check();action=payload['action']
        if payload.get('policy_hash')!=fingerprint(policy.model_dump(mode='json')):raise ValueError('Windows-configuratie is gewijzigd; maak een nieuw voorstel')
        program=None
        if action in ('open_program','close_program'):
            raw=policy.programs.get(payload['program'])
            if not raw:raise ValueError('Programma is niet door de eigenaar toegestaan')
            program=Path(raw).resolve(strict=True)
            if not program.is_file():raise ValueError('Programma niet beschikbaar')
        path=self.document(payload['path'],policy) if action=='open_file' else None
        guard()
        if self.policy()!=policy:raise ValueError('Windows-bevoegdheden zijn gewijzigd')
        if action=='open_program':
            child=subprocess.Popen([str(program)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,shell=False)
            def drain():
                count=0
                try:
                    if child.stdout:
                        while data:=child.stdout.read(4096):count+=len(data)
                finally:
                    if child.stdout:child.stdout.close()
                    if count:log.info('windows_program_output bytes=%s',count)
            threading.Thread(target=drain,name='jarvis-program-output',daemon=True).start()
            try:
                code=child.wait(timeout=.15)
                if code:raise OSError('Programma gaf een fout bij starten')
            except subprocess.TimeoutExpired:pass
            return {'requested':True,'state':'opening_requested','pid':child.pid}
        if action=='close_program':return self.close_program(program)
        if action=='open_file':
            os.startfile(str(path))
            return {'requested':True,'state':'document_handed_off'}
        user=ctypes.WinDLL('user32',use_last_error=True)
        if action=='lock':
            if not user.LockWorkStation():raise OSError('Windows accepteerde vergrendeling niet')
            return {'requested':True,'state':'lock_requested'}
        if action in ('shutdown','restart','cancel_shutdown'):
            executable=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32/shutdown.exe'
            args=['/a'] if action=='cancel_shutdown' else ['/r' if action=='restart' else '/s','/t','60']
            result=subprocess.run([str(executable),*args],capture_output=True,timeout=5,check=False,shell=False,creationflags=0x08000000)
            if result.stdout or result.stderr:log.info('windows_power_output bytes=%s',len(result.stdout)+len(result.stderr))
            if result.returncode:raise OSError('Windows accepteerde de energieopdracht niet')
            return {'requested':True,'state':'shutdown_cancelled' if action=='cancel_shutdown' else 'power_scheduled','delay_seconds':0 if action=='cancel_shutdown' else 60}
        if action=='sleep':
            power=ctypes.WinDLL('powrprof',use_last_error=True)
            power.SetSuspendState.argtypes=[ctypes.c_ubyte]*3;power.SetSuspendState.restype=ctypes.c_ubyte
            if not power.SetSuspendState(False,False,False):raise OSError('Windows accepteerde slaapstand niet')
            return {'requested':True,'state':'sleep_requested'}
        if action in ('play','pause'):
            user.GetForegroundWindow.restype=wintypes.HWND;user.GetShellWindow.restype=wintypes.HWND
            target=user.GetForegroundWindow() or user.GetShellWindow()
            if not target:raise OSError('Geen interactief mediadoel beschikbaar')
            user.SendMessageTimeoutW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM,wintypes.UINT,wintypes.UINT,ctypes.POINTER(ctypes.c_size_t)]
            user.SendMessageTimeoutW.restype=ctypes.c_ssize_t;media_result=ctypes.c_size_t()
            command=46 if action=='play' else 47
            if not user.SendMessageTimeoutW(target,0x319,target,command<<16,3,1000,ctypes.byref(media_result)):raise OSError('Mediaopdracht niet afgeleverd')
            return {'requested':True,'state':'media_command_delivered','handled':bool(media_result.value)}
        keys={'volume_up':0xAF,'volume_down':0xAE,'mute':0xAD,'play_pause':0xB3,'next':0xB0,'previous':0xB1}
        # SendInput returns the number of injected inputs; use a fixed media key only.
        class Key(ctypes.Structure):_fields_=[('vk',wintypes.WORD),('scan',wintypes.WORD),('flags',wintypes.DWORD),('time',wintypes.DWORD),('extra',ctypes.c_size_t)]
        class Mouse(ctypes.Structure):_fields_=[('dx',wintypes.LONG),('dy',wintypes.LONG),('data',wintypes.DWORD),('flags',wintypes.DWORD),('time',wintypes.DWORD),('extra',ctypes.c_size_t)]
        class Union(ctypes.Union):_fields_=[('key',Key),('mouse',Mouse)]
        class InputEvent(ctypes.Structure):_fields_=[('type',wintypes.DWORD),('value',Union)]
        events=(InputEvent*2)()
        for index,flags in enumerate((0,2)):events[index].type=1;events[index].value.key=Key(keys[action],0,flags,0,0)
        user.SendInput.argtypes=[wintypes.UINT,ctypes.POINTER(InputEvent),ctypes.c_int];user.SendInput.restype=wintypes.UINT
        if user.SendInput(2,events,ctypes.sizeof(InputEvent))!=2:raise OSError('Windows accepteerde de mediatoets niet')
        return {'requested':True,'state':'media_key_delivered'}

    @staticmethod
    def close_program(program):
        kernel=ctypes.WinDLL('kernel32',use_last_error=True);user=ctypes.WinDLL('user32',use_last_error=True)
        kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        kernel.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
        user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
        user.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
        matches=[];posted=[]
        callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
        def visit(window,_):
            process=wintypes.DWORD();user.GetWindowThreadProcessId(window,ctypes.byref(process))
            handle=kernel.OpenProcess(0x1000,False,process.value)
            if not handle:return True
            try:
                size=wintypes.DWORD(1024);name=ctypes.create_unicode_buffer(1024)
                if kernel.QueryFullProcessImageNameW(handle,0,name,ctypes.byref(size)) and Path(name.value).resolve()==program:
                    matches.append(process.value)
                    if user.PostMessageW(window,0x10,0,0):posted.append(process.value)
            except OSError:pass
            finally:kernel.CloseHandle(handle)
            return True
        user.EnumWindows.argtypes=[callback_type,wintypes.LPARAM]
        if not user.EnumWindows(callback_type(visit),0):raise OSError('Vensterlijst niet beschikbaar')
        if not matches:raise ValueError('Geen venster van dit toegestane programma gevonden')
        if not posted:raise OSError('Sluitverzoek niet geaccepteerd')
        return {'requested':True,'state':'close_requested','windows':len(posted),'unsaved_dialog_possible':True}
