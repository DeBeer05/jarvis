"""Persistent per-owner stop state and execution epochs. Never grants authority."""
import asyncio
import json

from server.security.types import AuthError
from server.automation.models import REGISTRY,SIDE_EFFECT_TOOLS


def migrate(db):
    columns={row[1] for row in db.execute('PRAGMA table_info(automation_jobs)')}
    for name,declaration in (('priority','INTEGER NOT NULL DEFAULT 1'),('deadline','REAL'),('approval_required','INTEGER NOT NULL DEFAULT 0')):
        if name not in columns:db.execute('ALTER TABLE automation_jobs ADD COLUMN '+name+' '+declaration)
    required=sorted(name for name,(_,mandatory) in REGISTRY.items() if mandatory)
    db.execute("UPDATE automation_jobs SET approval_required=1 WHERE status='approval' OR approval_device IS NOT NULL OR tool IN ("+','.join('?' for _ in required)+')',required)
    db.execute('CREATE INDEX IF NOT EXISTS automation_priority ON automation_jobs(status,priority DESC,due)')
    db.execute('CREATE TABLE IF NOT EXISTS automation_control(user_id INTEGER PRIMARY KEY REFERENCES auth_users(id) ON DELETE CASCADE,stopped INTEGER NOT NULL,epoch INTEGER NOT NULL,updated REAL NOT NULL)')


class ControlPlane:
    def __init__(self,engine):self.engine=engine;self.natural=None

    def state(self,device):
        with self.engine.store.db() as db:
            row=db.execute('SELECT d.user_id,coalesce(c.stopped,0) AS stopped,coalesce(c.epoch,0) AS epoch FROM auth_devices d LEFT JOIN automation_control c ON c.user_id=d.user_id WHERE d.id=?',(device,)).fetchone()
        if not row:raise AuthError('permission_denied','Apparaat niet beschikbaar.',403)
        return {'stopped':bool(row['stopped']),'epoch':row['epoch'],'user_id':row['user_id']}

    def check(self,device,epoch=None):
        state=self.state(device)
        if state['stopped'] or epoch is not None and state['epoch']!=epoch:raise AuthError('automation_stopped','De noodstop is actief of deze uitvoering is gestopt.',409)
        return state

    def directive(self,device,tool):
        with self.engine.store.db() as db:
            row=db.execute("SELECT s.payload FROM natural_settings s JOIN auth_devices d ON d.user_id=s.user_id WHERE d.id=? AND s.scope='user' AND s.device_id=''",(device,)).fetchone()
        autonomy=json.loads(row['payload']).get('autonomy',{}) if row else {}
        level=autonomy.get('actions',{}).get(tool)
        if level:return level
        if tool in ('DesktopMedia','DesktopPrograms'):return 'allow' if autonomy.get('profile')=='within_rules' else 'ask'
        return None

    def _set(self,principal,active):
        e=self.engine
        e.permissions.check(principal.device_id,'automation:write' if active else 'admin:account')
        with e.store.db(True) as db:
            e.security.store._require_live(db,principal)
            required='automation:write' if active else 'admin:account'
            if not db.execute('SELECT 1 FROM auth_permissions WHERE device_id=? AND permission=?',(principal.device_id,required)).fetchone():raise AuthError('permission_denied','Dit apparaat mag deze bevoegdheid niet wijzigen.',403)
            user=db.execute('SELECT user_id FROM auth_sessions WHERE id=?',(principal.session_id,)).fetchone()[0]
            row=db.execute('SELECT epoch FROM automation_control WHERE user_id=?',(user,)).fetchone()
            epoch=(row[0] if row else 0)+(1 if active else 0)
            db.execute('INSERT INTO automation_control VALUES (?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET stopped=excluded.stopped,epoch=excluded.epoch,updated=excluded.updated',(user,int(active),epoch,e.store.clock()))
            devices=[row[0] for row in db.execute('SELECT id FROM auth_devices WHERE user_id=? AND trusted=1 AND revoked_at IS NULL',(user,))]
            if active:
                db.execute("UPDATE automation_jobs SET status='paused',approval_hash=NULL,approved_device=NULL WHERE device_id IN (SELECT id FROM auth_devices WHERE user_id=?) AND status IN ('queued','approval','waiting','blocked')",(user,))
                db.execute("UPDATE automation_followups SET status='paused' WHERE device_id IN (SELECT id FROM auth_devices WHERE user_id=?) AND status='waiting'",(user,))
                tools=sorted(SIDE_EFFECT_TOOLS)
                db.execute("UPDATE automation_jobs SET status=CASE WHEN tool IN ("+','.join('?' for _ in tools)+") THEN 'uncertain' ELSE 'paused' END,approval_hash=NULL WHERE status='running' AND device_id IN (SELECT id FROM auth_devices WHERE user_id=?)",[*tools,user])
                if self.natural:
                    for device in devices:self.natural.events.publish(db,user,device,'control.stop',{'text':'De noodstop is actief, meneer.','epoch':epoch},'stop:'+str(epoch)+':'+device,priority=3)
            e.store.event(db,'emergency_stop' if active else 'emergency_stop_released',device=principal.device_id)
        return {'stopped':active,'epoch':epoch,'devices':devices,'paused_jobs_resumed':False}

    async def set(self,principal,active,*,exclude_request=None):
        result=await asyncio.to_thread(self._set,principal,active)
        if active and self.natural:
            for run in list(self.natural.chat.active.values()):
                if run.principal.device_id in result['devices'] and run.request_id!=exclude_request:self.natural.chat.cancel(run.request_id)
        result.pop('devices',None)
        return result
