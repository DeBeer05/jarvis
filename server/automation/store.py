"""Small transactional store. External actions are claimed exactly once."""
import hashlib
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def fingerprint(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def migrate(db):
    db.execute("CREATE TABLE automation_jobs (id TEXT PRIMARY KEY, key TEXT NOT NULL UNIQUE, device_id TEXT NOT NULL, tool TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL, due REAL NOT NULL, repeat TEXT NOT NULL, timezone TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL, result TEXT, approval_hash TEXT, approval_expires REAL, parent_id TEXT, step INTEGER NOT NULL DEFAULT 0)")
    db.execute("CREATE INDEX automation_due ON automation_jobs(status,due)")
    db.execute("ALTER TABLE automation_jobs ADD COLUMN approved_device TEXT")
    db.execute("ALTER TABLE automation_jobs ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0")
    db.execute("ALTER TABLE automation_jobs ADD COLUMN approval_device TEXT")
    db.execute("CREATE TABLE automation_events (id INTEGER PRIMARY KEY AUTOINCREMENT, at REAL NOT NULL, job_id TEXT, device_id TEXT, event TEXT NOT NULL)")
    db.execute("CREATE TABLE automation_notifications (id TEXT PRIMARY KEY, dedupe TEXT NOT NULL UNIQUE, at REAL NOT NULL, category TEXT NOT NULL, text TEXT NOT NULL, job_id TEXT)")
    db.execute("CREATE TABLE automation_preferences (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    db.execute("CREATE TABLE integration_secrets (key TEXT PRIMARY KEY, ciphertext BLOB NOT NULL)")
    db.execute("CREATE TABLE integration_oauth (state_hash TEXT PRIMARY KEY, ciphertext BLOB NOT NULL, expires REAL NOT NULL, session_id TEXT NOT NULL, device_id TEXT NOT NULL)")
    db.execute("CREATE TABLE automation_followups (id TEXT PRIMARY KEY, thread_id TEXT NOT NULL, baseline TEXT NOT NULL, due REAL NOT NULL, status TEXT NOT NULL, device_id TEXT NOT NULL)")


class Store:
    def __init__(self, database, clock=time.time):
        self.database, self.clock = database, clock

    @contextmanager
    def db(self, write=False):
        with self.database.connection() as db:
            db.row_factory = sqlite3.Row
            if write: db.execute("BEGIN IMMEDIATE")
            yield db

    def event(self, db, event, job=None, device=None):
        db.execute("INSERT INTO automation_events(at,job_id,device_id,event) VALUES (?,?,?,?)", (self.clock(), job, device, event))
        db.execute("DELETE FROM automation_events WHERE id IN (SELECT id FROM automation_events ORDER BY id DESC LIMIT -1 OFFSET 10000)")

    def recover(self):
        # A crash after an external HTTP request has an unknown outcome. Never replay it.
        with self.db(True) as db:
            from server.automation.models import SIDE_EFFECT_TOOLS
            tools=sorted(SIDE_EFFECT_TOOLS)
            db.execute("UPDATE automation_jobs SET status=CASE WHEN tool IN ("+','.join('?' for _ in tools)+") THEN 'uncertain' ELSE 'queued' END,approval_hash=NULL WHERE status='running'",tools)
            # Keep idempotency tombstones, remove old sensitive action bodies.
            db.execute("UPDATE automation_jobs SET payload='{}',result=NULL,status='deleted' WHERE status IN ('completed','denied','cancelled','failed') AND updated<?",(self.clock()-30*86400,))

    def create(self, device, tool, payload, key, due, repeat="once", timezone="Europe/Amsterdam", approval=False, parent=None, step=0):
        now = self.clock()
        value = (str(uuid.uuid4()), key, device, tool, encode(payload), "approval" if approval else "queued", due, repeat, timezone, now, now, parent, step)
        with self.db(True) as db:
            old = db.execute("SELECT * FROM automation_jobs WHERE key=?", (key,)).fetchone()
            if old:
                if old["device_id"] != device or old["tool"] != tool or old["payload"] != encode(payload): raise ValueError("Idempotency conflict")
                return dict(old)
            if db.execute("SELECT COUNT(*) FROM automation_jobs WHERE status!='deleted'").fetchone()[0] >= 5000: raise ValueError("Job limit reached")
            db.execute("INSERT INTO automation_jobs(id,key,device_id,tool,payload,status,due,repeat,timezone,created,updated,parent_id,step) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", value)
            self.event(db, "proposed" if approval else "scheduled", value[0], device)
        return self.get(value[0])

    def get(self, identifier):
        with self.db() as db:
            row = db.execute("SELECT * FROM automation_jobs WHERE id=?", (identifier,)).fetchone()
        if not row: raise ValueError("Unknown job")
        return dict(row)

    def items(self, offset=0):
        with self.db() as db:
            return [dict(x) for x in db.execute("SELECT * FROM automation_jobs WHERE status!='deleted' ORDER BY CASE WHEN status='approval' THEN 0 ELSE 1 END,created DESC LIMIT 20 OFFSET ?",(offset,))]

    @staticmethod
    def public(job):
        return {k: json.loads(v) if k in ("payload", "result") and v else v for k, v in job.items() if k not in ("approval_hash", "key")}

    def preference(self, key, default):
        with self.db() as db:
            row = db.execute("SELECT value FROM automation_preferences WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set_preference(self, key, value):
        with self.db(True) as db:
            db.execute("INSERT INTO automation_preferences VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, encode(value)))
