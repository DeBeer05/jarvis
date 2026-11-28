"""Owner-bound persistent queues. A started action is never automatically replayed."""
import json
from uuid import uuid4
from pydantic import Field
from typing import Literal
from server.natural.models import StrictModel,DeviceSettings
from server.natural.store import encode
from server.security.types import digest,token
from server.automation.store import fingerprint

TOOLS=frozenset(('DesktopRead','DesktopControl','DesktopMedia','DesktopPrograms'))

def migrate(db):
    statements=('''CREATE TABLE IF NOT EXISTS device_workers(
        device_id TEXT PRIMARY KEY REFERENCES auth_devices(id) ON DELETE CASCADE,user_id INTEGER NOT NULL,
        seen REAL NOT NULL,policy TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS device_commands(
        id TEXT PRIMARY KEY,job_id TEXT UNIQUE NOT NULL REFERENCES automation_jobs(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL,target TEXT REFERENCES auth_devices(id) ON DELETE SET NULL,
        tool TEXT NOT NULL,payload TEXT NOT NULL,state TEXT NOT NULL,
        expires REAL NOT NULL,lease_hash TEXT,lease_until REAL,result TEXT);
    CREATE INDEX IF NOT EXISTS device_commands_target ON device_commands(target,state);''')
    for statement in statements.split(';'):
        if statement.strip():db.execute(statement)

class Heartbeat(StrictModel):
    policy:dict=Field(default_factory=dict,max_length=10)

class Lease(StrictModel):
    lease:str=Field(min_length=32,max_length=100)

class Outcome(Lease):
    state:Literal['completed','failed','uncertain']
    result:dict=Field(default_factory=dict,max_length=20)

class DeviceBroker:
    def __init__(self,n):self.n=n

    def target(self,db,user,device):
        row=db.execute("SELECT d.*,s.payload AS settings FROM auth_devices d LEFT JOIN natural_settings s ON s.user_id=d.user_id AND s.device_id=d.id AND s.scope='device' WHERE d.id=? AND d.user_id=? AND d.type='windows' AND d.trusted=1 AND d.revoked_at IS NULL",(device,user)).fetchone()
        if not row:raise ValueError('Kies een vertrouwde Windows-computer van dezelfde eigenaar')
        consent=DeviceSettings.model_validate_json(row['settings']) if row['settings'] else DeviceSettings()
        if not consent.execution_allowed:raise ValueError('Opdrachtontvangst staat op deze computer uit')
        return consent

    def heartbeat(self,principal,body):
        from server.automation.windows import HostPolicy
        policy=HostPolicy.model_validate(body.policy).model_dump(mode='json')
        with self.n.store.transaction(principal,write=True) as (db,user):
            self.target(db,user,principal.device_id)
            db.execute('INSERT INTO device_workers VALUES (?,?,?,?) ON CONFLICT(device_id) DO UPDATE SET seen=excluded.seen,policy=excluded.policy',(principal.device_id,user,self.n.store.clock(),encode(policy)))
        return {'online':True}

    def list(self,principal):
        with self.n.store.transaction(principal) as (db,user):
            rows=db.execute("SELECT d.id,d.name,d.type,w.seen FROM auth_devices d LEFT JOIN device_workers w ON w.device_id=d.id WHERE d.user_id=? AND d.trusted=1 AND d.revoked_at IS NULL",(user,)).fetchall()
            return {'items':[{**dict(row),'online':row['seen'] is not None and row['seen']>self.n.store.clock()-90} for row in rows]}

    def route(self,principal,operation,payload):
        preferred=self.n.settings.get(principal)['settings']['routing']['windows_device']
        with self.n.store.transaction(principal) as (db,user):
            rows=db.execute("SELECT w.device_id,w.policy FROM device_workers w JOIN auth_devices d ON d.id=w.device_id WHERE w.user_id=? AND w.seen>? AND d.trusted=1 AND d.revoked_at IS NULL ORDER BY w.seen DESC",(user,self.n.store.clock()-90)).fetchall()
            own=next((row for row in rows if row['device_id']==principal.device_id),None)
            if own:rows=[own]
            elif preferred:rows=[row for row in rows if row['device_id']==preferred]
            if len(rows)!=1:raise ValueError('Kies één beschikbare Windows-computer')
            row=rows[0];self.target(db,user,row['device_id'])
            if operation!='DesktopRead':payload={**payload,'policy_hash':fingerprint(json.loads(row['policy']))}
            return {'target_device':row['device_id'],'operation':operation,'input':payload}

    def enqueue(self,row,payload,guard):
        guard();n=self.n
        from server.automation.models import validate
        operation=payload['operation']
        if operation not in TOOLS:raise ValueError('Niet ondersteunde apparaatopdracht')
        args=validate(operation,payload['input'])
        with n.automation.store.db(True) as db:
            source=db.execute('SELECT user_id FROM auth_devices WHERE id=?',(row['device_id'],)).fetchone()
            self.target(db,source['user_id'],payload['target_device'])
            worker=db.execute('SELECT seen,policy FROM device_workers WHERE device_id=?',(payload['target_device'],)).fetchone()
            if not worker or worker['seen']<n.store.clock()-90:raise ValueError('De gekozen computer is niet bereikbaar')
            if operation!='DesktopRead' and args.get('policy_hash')!=fingerprint(json.loads(worker['policy'])):raise ValueError('Apparaatbeleid veranderd; maak een nieuw voorstel')
            db.execute('INSERT OR IGNORE INTO device_commands VALUES (?,?,?,?,?,?,?,?,?,?,?)',(str(uuid4()),row['id'],source['user_id'],payload['target_device'],operation,encode(args),'queued',min(n.store.clock()+120,row['approval_expires'] or n.store.clock()+120),None,None,None))
        return {'waiting_for_device':True,'executed':False}

    def recover(self,db):
        now=self.n.store.clock()
        for row in db.execute("SELECT * FROM device_commands WHERE state IN ('queued','leased','running')").fetchall():
            if row['state']=='running' and row['lease_until']<=now:state='uncertain'
            elif row['expires']<=now:state='expired'
            elif row['state']=='leased' and row['lease_until']<=now:
                db.execute("UPDATE device_commands SET state='queued',lease_hash=NULL WHERE id=?",(row['id'],));continue
            else:continue
            db.execute('UPDATE device_commands SET state=?,lease_hash=NULL WHERE id=?',(state,row['id']))
            db.execute("UPDATE automation_jobs SET status=?,updated=? WHERE id=? AND status='waiting'",('uncertain' if state=='uncertain' else 'expired',now,row['job_id']))

    def claim(self,principal):
        n=self.n
        with n.store.transaction(principal,write=True) as (db,user):
            self.target(db,user,principal.device_id);self.recover(db)
            row=db.execute("SELECT c.* FROM device_commands c JOIN automation_jobs j ON j.id=c.job_id WHERE c.target=? AND c.user_id=? AND c.state='queued' AND j.status='waiting' ORDER BY c.expires LIMIT 1",(principal.device_id,user)).fetchone()
            if not row:return {'item':None}
            n.automation.permissions.check(row['target'],'automation:read')
            n.automation.permissions.check_tool(row['target'],row['tool'])
            job=n.automation.store.get(row['job_id']);self.guard(job,row)
            lease=token();db.execute("UPDATE device_commands SET state='leased',lease_hash=?,lease_until=? WHERE id=?",(digest(lease),n.store.clock()+30,row['id']))
            return {'item':{'id':row['id'],'lease':lease,'tool':row['tool'],'input':json.loads(row['payload']),'expires':row['expires']}}

    def guard(self,job,row):
        e=self.n.automation
        if job['status']!='waiting':raise ValueError('Opdracht niet meer actief')
        e.permissions.check(job['device_id'],'automation:read' if row['tool']=='DesktopRead' else 'automation:write')
        e.permissions.check_tool(job['device_id'],row['tool'])
        if row['tool'] in e.store.preference('disabled_tools',[]):raise ValueError('Deze functie is uitgeschakeld')
        if job['approval_required']:
            e.permissions.check(job['approved_device'],'automation:approve')
            if job['approval_expires']<=self.n.store.clock():raise ValueError('Goedkeuring verlopen')

    def transition(self,principal,identifier,body,*,start=False):
        n=self.n
        with n.store.transaction(principal,write=True) as (db,user):
            self.target(db,user,principal.device_id);self.recover(db)
            row=db.execute('SELECT * FROM device_commands WHERE id=? AND user_id=? AND target=?',(identifier,user,principal.device_id)).fetchone()
            if not row or row['lease_hash']!=digest(body.lease):raise ValueError('Apparaatopdracht verlopen of onbekend')
            if not start and row['state'] in ('completed','failed','uncertain'):return {'acknowledged':True,'replayed':True}
            self.guard(n.automation.store.get(row['job_id']),row)
            if start:
                if row['state']!='leased':raise ValueError('Opdracht al gestart; niet opnieuw uitvoeren')
                db.execute("UPDATE device_commands SET state='running',lease_until=? WHERE id=?",(min(n.store.clock()+60,row['expires']),identifier))
            else:
                if row['state']!='running':raise ValueError('Opdracht niet gestart')
                raw=encode(body.result)
                if len(raw)>8000:raise ValueError('Apparaatresultaat te groot')
                db.execute('UPDATE device_commands SET state=?,result=? WHERE id=?',(body.state,raw,identifier))
                db.execute("UPDATE automation_jobs SET status=?,result=?,updated=? WHERE id=? AND status='waiting'",(body.state,raw,n.store.clock(),row['job_id']))
                n.automation.store.event(db,body.state,row['job_id'],principal.device_id)
            return {'acknowledged':True}
