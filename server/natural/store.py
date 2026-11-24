"""User-scoped transactions and value-free audit for natural-conversation data."""
import json
import sqlite3
import time
from contextlib import contextmanager

from server.security.types import AuthError


def encode(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class Conflict(ValueError):
    pass


class NaturalStore:
    def __init__(self, database, security, clean=lambda value:value, clock=time.time):
        self.database, self.security, self.clean, self.clock = database, security, clean, clock

    @contextmanager
    def transaction(self, principal, *, write=False):
        with self.database.connection() as db:
            db.row_factory=sqlite3.Row
            if write: db.execute("BEGIN IMMEDIATE")
            self.security.store._require_live(db, principal)
            user=db.execute("SELECT user_id FROM auth_sessions WHERE id=? AND device_id=?",(principal.session_id,principal.device_id)).fetchone()
            if not user:raise AuthError()
            yield db, user["user_id"]

    def audit(self, db, user, device, event, target=None):
        db.execute("INSERT INTO natural_audit(user_id,device_id,at,event,target) VALUES (?,?,?,?,?)",(user,device,self.clock(),event,target))
        db.execute("DELETE FROM natural_audit WHERE id IN (SELECT id FROM natural_audit ORDER BY id DESC LIMIT -1 OFFSET 10000)")

    def safe_content(self, content):
        if self.clean(content)!=content or "\x00" in content:raise ValueError("Geheimen horen niet in instellingen of geheugen")
        return content
