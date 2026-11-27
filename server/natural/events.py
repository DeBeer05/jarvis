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
    def __init__(self,store):
        self.store=store

    def publish(self,db,user,device,kind,payload,key,*,priority=1,lifetime=86400):
        content=encode(payload)
        if len(content)>4000 or kind not in ('presence.return','briefing.ready','task.changed','integration.alert'):
            raise ValueError('Ongeldig intern event')
        identifier=str(uuid.uuid4());now=self.store.clock()
        db.execute('INSERT OR IGNORE INTO natural_events VALUES (?,?,?,?,?,?,?,?,?,NULL)',
                   (identifier,user,device,kind,content,key,priority,now,now+lifetime))
        db.execute('DELETE FROM natural_events WHERE user_id=? AND id IN (SELECT id FROM natural_events WHERE user_id=? ORDER BY created DESC LIMIT -1 OFFSET 1000)',(user,user))
        return db.execute('SELECT id FROM natural_events WHERE user_id=? AND dedupe=?',(user,key)).fetchone()[0]

    def list(self,principal,*,urgent_only=False):
        with self.store.transaction(principal) as (db,user):
            rows=db.execute('SELECT id,kind,payload,created,priority FROM natural_events WHERE user_id=? AND device_id=? AND acked IS NULL AND expires>? AND priority>=? ORDER BY priority DESC,created LIMIT 5',
                            (user,principal.device_id,self.store.clock(),2 if urgent_only else 0)).fetchall()
        return {'items':[{**dict(row),'payload':json.loads(row['payload'])} for row in rows]}

    def ack(self,principal,identifier):
        with self.store.transaction(principal,write=True) as (db,user):
            row=db.execute('SELECT id FROM natural_events WHERE id=? AND user_id=? AND device_id=?',(identifier,user,principal.device_id)).fetchone()
            if not row:raise ValueError('Event niet gevonden')
            db.execute('UPDATE natural_events SET acked=coalesce(acked,?) WHERE id=?',(self.store.clock(),identifier))
        return {'acknowledged':True}
