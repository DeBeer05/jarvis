"""Durable conversation references, reusing jobs and approvals in AutomationEngine."""
import json
import uuid

from server.natural.store import encode

# Approval nonces, shown timestamps and decision authority are intentionally absent.
FIELDS=("write_question","read_question","jobs","recent","calendar_query","calendars","events","messages","drafts","reminders")


class TaskMemory:
    def __init__(self,store,settings,engine):
        self.store,self.settings,self.engine=store,settings,engine

    def identifier(self,user,conversation):
        return str(uuid.uuid5(uuid.NAMESPACE_URL,f"jarvis:automation-context:{user}:{conversation}"))

    def load(self,run):
        if not self.settings.get(run.principal)["settings"]["tasks"]["resume"]:return {}
        self.engine.permissions.check(run.principal.device_id,"automation:read")
        with self.store.transaction(run.principal) as (db,user):
            row=db.execute("SELECT payload FROM natural_pending WHERE id=? AND user_id=? AND conversation_id=? AND kind='automation_context'",(self.identifier(user,run.conversation_id),user,run.conversation_id)).fetchone()
            return json.loads(row["payload"]) if row else {}

    def save(self,run,memory):
        if not self.settings.get(run.principal)["settings"]["tasks"]["resume"]:return
        self.engine.permissions.check(run.principal.device_id,"automation:read")
        retained={}
        for key in FIELDS:
            for item in memory.get(key,[])[:20]:
                candidate={**retained,key:[*retained.get(key,[]),item]}
                # Never truncate a parameter or external reference mid-structure.
                if len(encode(candidate).encode("utf-8"))<=65536:retained=candidate
        payload=self.store.clean(encode(retained));stamp=self.store.clock()
        with self.store.transaction(run.principal,write=True) as (db,user):
            owner=db.execute("SELECT user_id FROM natural_conversation_owners WHERE conversation_id=?",(run.conversation_id,)).fetchone()
            if not owner or owner["user_id"]!=user:raise ValueError("Gesprek niet gevonden")
            identifier=self.identifier(user,run.conversation_id)
            db.execute("INSERT INTO natural_pending(id,user_id,conversation_id,kind,payload,revision,created,updated,status) VALUES (?,?,?,?,?,1,?,?,'waiting') ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,revision=natural_pending.revision+1,updated=excluded.updated",(identifier,user,run.conversation_id,"automation_context",payload,stamp,stamp))

    def list(self,principal):
        self.engine.permissions.check(principal.device_id,"automation:read")
        with self.store.transaction(principal) as (db,user):
            rows=db.execute("SELECT id,conversation_id,revision,updated,payload FROM natural_pending WHERE user_id=? AND kind='automation_context' ORDER BY updated DESC LIMIT 100",(user,)).fetchall()
            items=[]
            for row in rows:
                values=json.loads(row["payload"])
                if not any(values.get(key) for key in ("write_question","read_question","jobs")):continue
                items.append({"id":row["id"],"conversation_id":row["conversation_id"],"revision":row["revision"],"updated":row["updated"],"questions":values.get("write_question",[])+values.get("read_question",[]),"jobs":values.get("jobs",[])})
            return {"items":items}
