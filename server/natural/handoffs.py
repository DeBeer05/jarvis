"""Bounded device handoffs; external apps retain their own final send/call action."""
import json

from server.natural.models import DeviceSettings
from server.automation.store import encode


class Handoffs:
    def __init__(self,natural):self.natural=natural

    def guard_job(self,row):
        engine=self.natural.automation
        if row['approval_expires']<=engine.store.clock():raise ValueError('Goedkeuring verlopen')
        if row['parent_id'] and engine.store.get(row['parent_id'])['status']!='waiting':raise ValueError('Bovenliggende taak is gestopt')
        engine.permissions.check(row['device_id'],'automation:write')
        engine.permissions.check_tool(row['device_id'],'MobileHandoff')
        engine.permissions.check(row['approved_device'],'automation:approve')
        if 'MobileHandoff' in engine.store.preference('disabled_tools',[]):raise ValueError('Telefoonopdrachten uitgeschakeld')

    @staticmethod
    def target(db,user,device):
        row=db.execute("SELECT d.type,d.trusted,d.revoked_at,s.payload FROM auth_devices d LEFT JOIN natural_settings s ON s.device_id=d.id AND s.user_id=d.user_id AND s.scope='device' WHERE d.id=? AND d.user_id=?",(device,user)).fetchone()
        if not row or row['type']!='android' or not row['trusted'] or row['revoked_at'] is not None:raise ValueError('Kies een vertrouwd Android-apparaat van dezelfde eigenaar')
        settings=DeviceSettings.model_validate_json(row['payload']) if row['payload'] else DeviceSettings()
        if not settings.handoff_allowed:raise ValueError('Telefoonopdrachten zijn op dat apparaat niet toegestaan')

    def publish(self,row,payload,guard):
        guard();n=self.natural
        with n.store.database.connection() as db:
            import sqlite3
            db.row_factory=sqlite3.Row;db.execute('BEGIN IMMEDIATE')
            source=db.execute('SELECT user_id FROM auth_devices WHERE id=?',(row['device_id'],)).fetchone()
            if not source:raise ValueError('Opdrachtgever niet beschikbaar')
            user=source['user_id'];self.target(db,user,payload['target_device'])
            identifier=n.events.publish(db,user,payload['target_device'],'device.handoff',{'job_id':row['id'],'request':payload},'handoff:'+row['id'],lifetime=120)
        return {'ready_on_phone':True,'event_id':identifier,'called':False,'sent':False}

    def list(self,principal):
        n=self.natural
        with n.store.transaction(principal) as (db,user):
            self.target(db,user,principal.device_id)
            rows=db.execute("SELECT e.id,e.payload,j.device_id,j.approved_device,j.approval_expires,j.parent_id FROM natural_events e JOIN automation_jobs j ON j.id=json_extract(e.payload,'$.job_id') WHERE e.user_id=? AND e.device_id=? AND e.kind='device.handoff' AND e.acked IS NULL AND e.expires>? AND j.status='waiting' ORDER BY e.created LIMIT 5",(user,principal.device_id,n.store.clock())).fetchall()
        result=[]
        for row in rows:
            try:self.guard_job(row)
            except Exception:continue
            result.append({'id':row['id'],**json.loads(row['payload'])})
        return {'items':result}

    def result(self,principal,identifier,state):
        n=self.natural
        with n.store.transaction(principal,write=True) as (db,user):
            self.target(db,user,principal.device_id)
            row=db.execute("SELECT payload,acked,expires FROM natural_events WHERE id=? AND user_id=? AND device_id=? AND kind='device.handoff'",(identifier,user,principal.device_id)).fetchone()
            if not row:raise ValueError('Telefoonopdracht niet gevonden')
            if row['acked'] is not None:return {'acknowledged':True,'replayed':True}
            if row['expires']<=n.store.clock():raise ValueError('Telefoonopdracht verlopen')
            job=json.loads(row['payload'])['job_id']
            self.guard_job(n.automation.store.get(job))
            if not db.execute("UPDATE automation_jobs SET status=?,result=?,updated=? WHERE id=? AND tool='MobileHandoff' AND status='waiting'",('completed' if state=='handed_off' else 'cancelled',encode({'handed_off':state=='handed_off','called':False,'sent':False}),n.store.clock(),job)).rowcount:raise ValueError('Opdracht is niet meer actief')
            db.execute('UPDATE natural_events SET acked=? WHERE id=?',(n.store.clock(),identifier))
            n.automation.store.event(db,'phone_'+state,job,principal.device_id)
        return {'acknowledged':True,'called':False,'sent':False}
