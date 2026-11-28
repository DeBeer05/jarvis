"""One bounded worker on Qt's existing worker pool; no GUI on execution threads."""
import json
import sqlite3
import threading
import time
from pathlib import Path
from PySide6.QtCore import QObject,QTimer

BASE='/api/v1/natural'

class ReceiptStore:
    def __init__(self,path):self.path=Path(path)
    def remember(self,identifier,state,result=None):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS receipts(id TEXT PRIMARY KEY,state TEXT NOT NULL,result TEXT,at REAL NOT NULL)')
            db.execute('DELETE FROM receipts WHERE at<?',(time.time()-7*86400,))
            db.execute('INSERT INTO receipts VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET state=excluded.state,result=excluded.result,at=excluded.at',(identifier,state,json.dumps(result or {}),time.time()))
    def get(self,identifier):
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS receipts(id TEXT PRIMARY KEY,state TEXT NOT NULL,result TEXT,at REAL NOT NULL)')
            row=db.execute('SELECT state,result FROM receipts WHERE id=?',(identifier,)).fetchone()
            return (row[0],json.loads(row[1])) if row else None

class DeviceWorker(QObject):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.busy=False;self.epoch=0;self.stop=threading.Event()
        self.timer=QTimer(self);self.timer.setInterval(10000);self.timer.timeout.connect(self.poll);self.timer.start()
        self.receipts=ReceiptStore(window.store.directory/'device-receipts.sqlite3')
    def clear(self):self.epoch+=1;self.stop.set()
    def poll(self):
        w=self.window
        if self.busy or not w.principal or w.manager.state!='online' or w.closing:return
        self.busy=True;api=w.manager.api;epoch=self.epoch;stopped=threading.Event();self.stop=stopped
        def work(_):
            document=api.request('GET',BASE+'/device-settings')['settings']
            if not document.get('execution_allowed'):return
            from server.automation.windows import WindowsHost,HostPolicy
            from server.automation.models import validate
            policy=HostPolicy.model_validate(document.get('execution_policy',{}))
            if not policy.enabled:return
            class Store:
                clock=staticmethod(time.time)
                def preference(self,key,default):return policy.model_dump(mode='json') if key=='windows_host' else default
            host=WindowsHost(Store())
            def guard():
                if stopped.is_set():raise PermissionError('Opdrachtontvangst gestopt')
            guard();api.request('POST',BASE+'/devices/heartbeat',{'policy':policy.model_dump(mode='json')})
            item=api.request('POST',BASE+'/devices/claim',{})['item']
            if not item:return
            identifier=item['id'];lease={'lease':item['lease']};path=BASE+'/devices/commands/'+identifier
            prior=self.receipts.get(identifier)
            if prior:
                # A receipt is written BEFORE execution. Never execute a second time.
                if prior[0]=='running':state,result='uncertain',{'executed':None}
                else:state,result=prior
                api.request('POST',path+'/result',{**lease,'state':state,'result':result});return
            args=validate(item['tool'],item['input'])
            guard()
            if time.time()>=item['expires']:return
            self.receipts.remember(identifier,'running')
            api.request('POST',path+'/start',lease)
            try:
                guard()
                if item['tool']=='DesktopPrograms' and not policy.programs_allowed:raise PermissionError('Programmas niet toegestaan')
                if item['tool']=='DesktopMedia' and not policy.media_allowed:raise PermissionError('Media niet toegestaan')
                result=(host.read if item['tool']=='DesktopRead' else host.control)(args,guard)
                state='completed'
            except Exception:
                # Even an OS exception can happen after a partial effect.
                state,result='uncertain',{'executed':None}
            self.receipts.remember(identifier,state,result)
            api.request('POST',path+'/result',{**lease,'state':state,'result':result})
        def done(_):self.busy=False
        def failed(error):
            self.busy=False
            if epoch==self.epoch and getattr(error,'code','') not in ('permission_denied','invalid_action'):w.show_notice('Apparaatopdrachten zijn tijdelijk niet bereikbaar; er wordt niets dubbel uitgevoerd.')
        w.jobs.submit(work,done,failed)
