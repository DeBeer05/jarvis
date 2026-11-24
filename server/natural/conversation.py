"""Async conversation lifecycle and durable device leases, independent of audio/LLM."""
import asyncio
import re
import uuid
from enum import StrEnum

from server.chat_store import now as chat_time
from server.natural.store import Conflict


class State(StrEnum):
    STANDBY="STANDBY"
    ACTIVATING="ACTIVATING"
    LISTENING="LISTENING"
    USER_SPEAKING="USER_SPEAKING"
    PROCESSING="PROCESSING"
    THINKING="THINKING"
    ASSISTANT_SPEAKING="ASSISTANT_SPEAKING"
    INTERRUPTED="INTERRUPTED"
    WAITING_FOR_INFORMATION="WAITING_FOR_INFORMATION"
    WAITING_FOR_APPROVAL="WAITING_FOR_APPROVAL"
    EXECUTING_ACTION="EXECUTING_ACTION"
    RECONNECTING="RECONNECTING"
    ENDING="ENDING"
    ERROR="ERROR"


TRANSITIONS={
    State.STANDBY:{State.ACTIVATING,State.ENDING},
    State.ACTIVATING:{State.LISTENING,State.RECONNECTING},
    State.LISTENING:{State.USER_SPEAKING,State.PROCESSING,State.INTERRUPTED,State.ENDING,State.RECONNECTING},
    State.USER_SPEAKING:{State.PROCESSING,State.LISTENING,State.INTERRUPTED,State.ENDING,State.RECONNECTING},
    State.PROCESSING:{State.THINKING,State.WAITING_FOR_INFORMATION,State.WAITING_FOR_APPROVAL,State.LISTENING,State.INTERRUPTED,State.ENDING},
    State.THINKING:{State.ASSISTANT_SPEAKING,State.WAITING_FOR_INFORMATION,State.WAITING_FOR_APPROVAL,State.EXECUTING_ACTION,State.LISTENING,State.INTERRUPTED,State.ENDING},
    State.ASSISTANT_SPEAKING:{State.INTERRUPTED,State.LISTENING,State.WAITING_FOR_INFORMATION,State.WAITING_FOR_APPROVAL,State.ENDING,State.RECONNECTING},
    State.INTERRUPTED:{State.USER_SPEAKING,State.PROCESSING,State.LISTENING,State.ENDING,State.RECONNECTING},
    State.WAITING_FOR_INFORMATION:{State.USER_SPEAKING,State.PROCESSING,State.LISTENING,State.ENDING},
    State.WAITING_FOR_APPROVAL:{State.USER_SPEAKING,State.PROCESSING,State.EXECUTING_ACTION,State.LISTENING,State.ENDING},
    State.EXECUTING_ACTION:{State.THINKING,State.ASSISTANT_SPEAKING,State.LISTENING,State.ENDING},
    State.RECONNECTING:{State.ACTIVATING,State.LISTENING,State.ENDING},
    State.ENDING:{State.STANDBY},
    State.ERROR:{State.ACTIVATING,State.LISTENING,State.RECONNECTING,State.ENDING},
}
CLIENT_EVENTS={"listening":State.LISTENING,"user_speaking":State.USER_SPEAKING,"processing":State.PROCESSING,"assistant_speaking":State.ASSISTANT_SPEAKING,"interrupted":State.INTERRUPTED,"ending":State.ENDING,"reconnecting":State.RECONNECTING}


def is_ending(text,phrases):
    normalize=lambda value:re.sub(r"[^\w\s]","",value.casefold()).strip()
    message=normalize(text)
    # Exact utterances only: 'bedankt, maar ...' is an ongoing conversation.
    return message in {normalize(value) for value in phrases}


class NaturalConversationManager:
    def __init__(self,store,settings,chat):
        self.store,self.settings,self.chat=store,settings,chat
        self.mutation=asyncio.Lock()

    @staticmethod
    def public(row):
        return {key:row[key] for key in ("conversation_id","device_id","state","epoch","revision","started","activity","lease_until")}

    def owned(self,db,user,conversation):
        owner=db.execute("SELECT user_id FROM natural_conversation_owners WHERE conversation_id=?",(conversation,)).fetchone()
        if not owner or owner["user_id"]!=user:raise ValueError("Gesprek niet gevonden")

    def _claim(self,principal,conversation=None,*,takeover=False,revision=None):
        now=self.store.clock();preferences=self.settings.get(principal)["settings"]["conversations"]
        if not preferences["enabled"]:raise ValueError("Natuurlijke gesprekken zijn uitgeschakeld")
        with self.store.transaction(principal,write=True) as (db,user):
            if conversation is None:
                if db.execute("SELECT count(*) FROM chat_conversations").fetchone()[0]>=self.chat.store.max_conversations:raise Conflict("Gesprekslimiet bereikt")
                conversation=str(uuid.uuid4());stamp=chat_time()
                db.execute("INSERT INTO chat_conversations VALUES (?,?,?,?)",(conversation,"Spraakgesprek",stamp,stamp))
                db.execute("INSERT INTO natural_conversation_owners VALUES (?,?)",(conversation,user))
            else:self.owned(db,user,conversation)
            old=db.execute("SELECT * FROM natural_sessions WHERE conversation_id=? AND user_id=?",(conversation,user)).fetchone()
            if revision is not None and (old["revision"] if old else 0)!=revision:raise Conflict("Gesprek elders gewijzigd")
            if old and old["lease_until"]>now and old["state"] not in (State.STANDBY,State.ENDING) and (old["device_id"]!=principal.device_id or old["auth_session"]!=principal.session_id) and not takeover:
                raise Conflict("Dit gesprek is actief op een ander apparaat; neem het expliciet over")
            epoch=old["epoch"]+1 if old else 1;version=old["revision"]+1 if old else 1
            lease=min(now+60,now+preferences["maximum_seconds"])
            db.execute("INSERT INTO natural_sessions(conversation_id,user_id,device_id,auth_session,state,epoch,revision,started,activity,lease_until) VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(conversation_id) DO UPDATE SET device_id=excluded.device_id,auth_session=excluded.auth_session,state=excluded.state,epoch=excluded.epoch,revision=excluded.revision,started=excluded.started,activity=excluded.activity,lease_until=excluded.lease_until",(conversation,user,principal.device_id,principal.session_id,State.ACTIVATING,epoch,version,now,now,lease))
            self.store.audit(db,user,principal.device_id,"conversation_taken_over" if takeover else "conversation_activated",conversation)
            row=db.execute("SELECT * FROM natural_sessions WHERE conversation_id=?",(conversation,)).fetchone()
        return self.public(row)

    async def claim(self,principal,conversation=None,*,takeover=False,revision=None):
        async with self.mutation:
            snapshot=await asyncio.to_thread(self._claim,principal,conversation,takeover=takeover,revision=revision)
            if takeover:
                # Only generation/audio are interrupted. Durable tasks are not cancelled.
                for run in list(self.chat.active.values()):
                    if run.conversation_id==snapshot["conversation_id"]:run.cancel.set()
            return snapshot

    def _get(self,principal,conversation):
        with self.store.transaction(principal,write=True) as (db,user):
            self.owned(db,user,conversation)
            row=db.execute("SELECT * FROM natural_sessions WHERE conversation_id=? AND user_id=?",(conversation,user)).fetchone()
            if not row:raise ValueError("Gespreksessie niet gevonden")
            data=dict(row);now=self.store.clock();config=self.settings.get(principal)["settings"]["conversations"]
            idle=data["state"] in (State.LISTENING,State.WAITING_FOR_INFORMATION,State.WAITING_FOR_APPROVAL)
            expired=data["state"] not in (State.STANDBY,State.RECONNECTING) and (not config["enabled"] or now-data["started"]>config["maximum_seconds"] or (config["automatic_end"] and idle and now-data["activity"]>config["inactivity_seconds"]) or data["lease_until"]<=now)
            if expired:
                db.execute("UPDATE natural_sessions SET state=?,epoch=epoch+1,revision=revision+1,lease_until=0 WHERE conversation_id=?",(State.STANDBY,conversation))
                data=dict(db.execute("SELECT * FROM natural_sessions WHERE conversation_id=?",(conversation,)).fetchone())
            return self.public(data)

    async def get(self,principal,conversation):return await asyncio.to_thread(self._get,principal,conversation)

    def _transition(self,principal,conversation,target,epoch,*,heartbeat=False):
        config=self.settings.get(principal)["settings"]["conversations"];now=self.store.clock()
        if not config["enabled"]:raise Conflict("Natuurlijke gesprekken zijn uitgeschakeld")
        with self.store.transaction(principal,write=True) as (db,user):
            self.owned(db,user,conversation)
            row=db.execute("SELECT * FROM natural_sessions WHERE conversation_id=? AND user_id=?",(conversation,user)).fetchone()
            if not row or row["device_id"]!=principal.device_id or row["auth_session"]!=principal.session_id or row["epoch"]!=epoch or row["lease_until"]<=now:raise Conflict("Deze audiosessie is verlopen of overgenomen")
            current=State(row["state"]);target=State(target)
            if now-row["started"]>config["maximum_seconds"]:raise Conflict("Maximale gespreksduur bereikt")
            if heartbeat:target=current
            if target!=current and target!=State.ERROR and target not in TRANSITIONS[current]:raise Conflict("Ongeldige gespreksvolgorde")
            activity=now if not heartbeat and target in (State.USER_SPEAKING,State.PROCESSING,State.THINKING,State.ASSISTANT_SPEAKING,State.WAITING_FOR_INFORMATION,State.WAITING_FOR_APPROVAL) else row["activity"]
            if target==State.LISTENING and current==State.ASSISTANT_SPEAKING:activity=now
            next_epoch=epoch+1 if target==State.INTERRUPTED else epoch
            lease=0 if target in (State.STANDBY,State.ENDING) else min(now+60,row["started"]+config["maximum_seconds"])
            db.execute("UPDATE natural_sessions SET state=?,epoch=?,revision=revision+1,activity=?,lease_until=? WHERE conversation_id=?",(target,next_epoch,activity,lease,conversation))
            result=db.execute("SELECT * FROM natural_sessions WHERE conversation_id=?",(conversation,)).fetchone()
        return self.public(result)

    async def transition(self,principal,conversation,target,epoch,*,heartbeat=False):
        async with self.mutation:
            # Heartbeats must not keep an idle/expired session alive forever.
            await asyncio.to_thread(self._get,principal,conversation)
            state=await asyncio.to_thread(self._transition,principal,conversation,target,epoch,heartbeat=heartbeat)
            if target in (State.INTERRUPTED,State.ENDING):
                for run in list(self.chat.active.values()):
                    if run.conversation_id==conversation:run.cancel.set()
            return state

    def recover(self):
        with self.store.database.connection() as db:
            db.execute("UPDATE natural_sessions SET state=?,epoch=epoch+1,revision=revision+1,lease_until=0 WHERE state NOT IN (?,?)",(State.RECONNECTING,State.STANDBY,State.ENDING))
