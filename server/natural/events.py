"""Small durable, user-scoped event inbox in the existing database, without LLMs."""
import json
import uuid

from server.natural.store import encode


def migrate(db):
    db.execute('''CREATE TABLE IF NOT EXISTS natural_events(
        id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,device_id TEXT NOT NULL,
        kind TEXT NOT NULL,payload TEXT NOT NULL,dedupe TEXT NOT NULL,priority INTEGER NOT NULL,
        created REAL NOT NULL,expires REAL NOT NULL,acked REAL,
        UNIQUE(user_id,dedupe))''')
    db.execute('CREATE INDEX IF NOT EXISTS natural_events_delivery ON natural_events(user_id,device_id,acked,expires)')


class EventInbox:
    def __init__(self,store,permissions=None):
        self.store=store;self.permissions=permissions

    def publish(self,db,user,device,kind,payload,key,*,priority=1,lifetime=86400):
        content=encode(payload)
        if len(content)>4000 or kind not in ('presence.return','presence.away','briefing.ready','briefing.prepared','task.changed','integration.alert','device.handoff'):
            raise ValueError('Ongeldig intern event')
        identifier=str(uuid.uuid4());now=self.store.clock()
        db.execute('INSERT OR IGNORE INTO natural_events(id,user_id,device_id,kind,payload,dedupe,priority,created,expires,acked) VALUES (?,?,?,?,?,?,?,?,?,NULL)',
                   (identifier,user,device,kind,content,key,priority,now,now+lifetime))
        db.execute('DELETE FROM natural_events WHERE user_id=? AND id IN (SELECT id FROM natural_events WHERE user_id=? ORDER BY created DESC LIMIT -1 OFFSET 1000)',(user,user))
        return db.execute('SELECT id FROM natural_events WHERE user_id=? AND dedupe=?',(user,key)).fetchone()[0]

    def list(self,principal,*,urgent_only=False):
        with self.store.transaction(principal) as (db,user):
            rows=db.execute("SELECT id,kind,payload,created,priority FROM natural_events WHERE user_id=? AND device_id=? AND kind NOT IN ('presence.away','briefing.prepared','device.handoff') AND acked IS NULL AND expires>? AND priority>=? ORDER BY priority DESC,created LIMIT 5",
                            (user,principal.device_id,self.store.clock(),2 if urgent_only else 0)).fetchall()
        result=[]
        for row in rows:
            payload=json.loads(row['payload'])
            if row['kind']=='briefing.ready':
                if not self.permissions:continue
                try:
                    disabled=self.permissions.store.preference('disabled_tools',[])
                    if 'PersonalBriefing' in disabled:continue
                    self.permissions.check_tool(principal.device_id,'PersonalBriefing')
                    for source,tool in (('calendar','CalendarRead'),('email','EmailRead')):
                        if payload.get('sources',{}).get(source,{}).get('status')=='available':
                            if tool in disabled:raise PermissionError('Bron uitgeschakeld')
                            self.permissions.check(principal.device_id,'automation:read')
                            self.permissions.check_tool(principal.device_id,tool)
                except Exception:continue
            result.append({**dict(row),'payload':payload})
        return {'items':result}

    def ack(self,principal,identifier):
        with self.store.transaction(principal,write=True) as (db,user):
            row=db.execute('SELECT id FROM natural_events WHERE id=? AND user_id=? AND device_id=?',(identifier,user,principal.device_id)).fetchone()
            if not row:raise ValueError('Event niet gevonden')
            db.execute('UPDATE natural_events SET acked=coalesce(acked,?) WHERE id=?',(self.store.clock(),identifier))
        return {'acknowledged':True}
