"""Composition root; shares the existing database, security service and AI router."""
from server.natural.store import NaturalStore
from server.natural.settings import SettingsManager
from server.natural.memory import MemoryManager
from server.natural.conversation import NaturalConversationManager
from server.natural.context import ContextManager
from server.natural.store import Conflict
import re


class NaturalService:
    def __init__(self,database,security,chat,automation):
        self.store=NaturalStore(database,security,chat.store.clean)
        self.settings=SettingsManager(self.store)
        self.memory=MemoryManager(self.store)
        self.security,self.chat,self.automation=security,chat,automation
        self.conversations=NaturalConversationManager(self.store,self.settings,chat)
        self.context=ContextManager(self.store,self.settings,self.memory,chat.settings)
        chat.natural=self

    def authorize_conversation(self,principal,conversation):
        with self.store.transaction(principal,write=True) as (db,user):
            owner=db.execute("SELECT user_id FROM natural_conversation_owners WHERE conversation_id=?",(conversation,)).fetchone()
            # The existing database has exactly one owner account (id=1).
            # Conversations created before natural mode belong to that owner.
            if not owner and user==1:
                db.execute("INSERT INTO natural_conversation_owners VALUES (?,?)",(conversation,user))
            elif not owner or owner["user_id"]!=user:
                raise ValueError("Gesprek niet gevonden")

    def prepare(self,run):
        self.authorize_conversation(run.principal,run.conversation_id)
        if run.session_epoch is not None:
            with self.store.transaction(run.principal) as (db,user):
                row=db.execute("SELECT * FROM natural_sessions WHERE conversation_id=? AND user_id=?",(run.conversation_id,user)).fetchone()
                if not row or row["device_id"]!=run.principal.device_id or row["auth_session"]!=run.principal.session_id or row["epoch"]!=run.session_epoch or row["lease_until"]<=self.store.clock():
                    raise Conflict("Audiosessie verlopen of overgenomen")
        prepared=self.context.prepare(run)
        messages,metrics=self.context.build(run,prepared)
        return prepared,messages,metrics

    def command(self,run):
        """Explicit memory commands are executed locally, never by generated code."""
        message=run.message.strip();config=run.natural_context["settings"]
        match=re.fullmatch(r"(?:jarvis[, ]+)?onthoud(?: dat)?\s+(.+)",message,re.I|re.S)
        if match:
            if not config["memory"]["long_term"] or config["autonomy"]["actions"].get("MemorySave")=="block":
                return "Langetermijngeheugen is uitgeschakeld of geblokkeerd."
            content=match.group(1).strip()
            if content.casefold() in ("dit","dat"):
                return "Wat wil je precies dat ik onthoud?"
            try:self.memory.save(run.principal,{"content":content,"kind":"preference" if re.search(r"\b(liever|voorkeur|liefst)\b",content,re.I) else "fact"},source="conversation",source_turn=run.request_id)
            except ValueError:
                return "Dit kan ik niet als gewone herinnering opslaan. Gevoelige gegevens vereisen expliciete toestemming via geheugenbeheer; geheimen sla ik niet op."
            return "Ik heb dit onthouden. Je kunt het later bekijken, aanpassen of verwijderen in geheugenbeheer."
        if re.fullmatch(r"(?:jarvis[, ]+)?wat (?:weet|onthoud) je (?:nog )?(?:over|van) mij[?.!]*",message,re.I):
            items=self.memory.list(run.principal,status="active",include_sensitive=False,limit=20)["items"]
            items=[item for item in items if item["expires"] is None or item["expires"]>self.store.clock()]
            return ("Dit heb ik onthouden:\n"+"\n".join(f"- {item['content']}" for item in items)) if items else "Ik heb nog geen actieve gewone herinneringen over je opgeslagen."
        match=re.fullmatch(r"(?:jarvis[, ]+)?vergeet\s+(.+?)[.!]*",message,re.I|re.S)
        if match:
            if config["autonomy"]["actions"].get("MemoryUpdate")=="block":return "Geheugenwijzigingen zijn geblokkeerd."
            query=match.group(1).strip()
            if query.casefold() in ("dat","dit","alles"):
                return "Welke herinnering bedoel je precies? Noem de inhoud of verwijder haar via geheugenbeheer. De volledige geheugenlijst wissen vraagt daar een aparte bevestiging."
            items=self.memory.list(run.principal,query=query,status="active",limit=2,include_sensitive=False)["items"]
            if len(items)!=1:return "Ik vind geen unieke herinnering. Noem iets specifiekers of kies de herinnering in geheugenbeheer."
            self.memory.delete(run.principal,items[0]["id"],items[0]["revision"])
            return "Die herinnering is verwijderd en wordt niet meer als geheugen opgehaald. Het oorspronkelijke gesprek bestaat nog in de gespreksgeschiedenis."
        return None

    async def stream_command(self,run):
        import asyncio
        reply=await asyncio.to_thread(self.command,run)
        if reply is not None:
            yield {"type":"provider","provider":"local","model":"memory"}
            yield {"type":"delta","text":reply}

    @staticmethod
    def is_command(run):
        return bool(re.match(r"^(?:jarvis[, ]+)?(?:onthoud\b|vergeet\b|wat (?:weet|onthoud) je (?:nog )?(?:over|van) mij[?.!]*$)",run.message.strip(),re.I))
