"""Composition root; shares the existing database, security service and AI router."""
from server.natural.store import NaturalStore
from server.natural.settings import SettingsManager
from server.natural.memory import MemoryManager
from server.natural.conversation import NaturalConversationManager,State
from server.natural.context import ContextManager
from server.natural.store import Conflict
from server.natural.tasks import TaskMemory
from server.natural.diagnostics import DiagnosticsManager
from server.natural.retention import RetentionManager
from server.natural.preferences import preference,automatic_preference
from server.natural.responses import IntelligentResponseManager
import re
import json
import uuid
from server.natural.store import encode

CAPABILITIES=re.compile(r"(?:jarvis[, ]+)?(?:wat (?:kan|kun) (?:je|jij|u)(?: allemaal)?(?: voor (?:me|mij))?(?: doen)?|wat zijn (?:je|jouw) (?:functies|mogelijkheden))[?.!]*",re.I)
OPEN_TASKS=re.compile(r"(?:jarvis[, ]+)?(?:welke taken staan (?:er )?nog open|wat zijn mijn openstaande taken|toon mijn openstaande taken)[?.!]*",re.I)


class NaturalService:
    def __init__(self,database,security,chat,automation):
        self.security,self.chat,self.automation=security,chat,automation
        self.store=NaturalStore(database,security,chat.store.clean)
        self.settings=SettingsManager(self.store)
        from server.natural.events import EventInbox
        from server.natural.presence import PresenceManager
        self.events=EventInbox(self.store,automation.permissions)
        automation.safety.natural=self
        automation.store.event_sink=self.task_event
        self.presence=PresenceManager(self)
        self.settings.presence=self.presence
        self.memory=MemoryManager(self.store)
        from server.natural.tts import TTSRouter
        self.tts=TTSRouter(self)
        from server.natural.progress_audio import ProgressAudio
        self.progress_audio=ProgressAudio(self)
        self.responses=IntelligentResponseManager(self)
        from server.natural.contacts import ContactManager
        self.contacts=ContactManager(self.store)
        self.conversations=NaturalConversationManager(self.store,self.settings,chat)
        self.context=ContextManager(self.store,self.settings,self.memory,chat.settings,self.responses)
        self.tasks=TaskMemory(self.store,self.settings,automation)
        self.diagnostics=DiagnosticsManager(self.store,self.settings)
        self.retention=RetentionManager(self)
        from server.natural.planning import ActivityPlanningManager
        self.planning=ActivityPlanningManager(self)
        from server.natural.life_items import LifeItems
        from server.natural.briefings import BriefingManager
        self.life=LifeItems(self);automation.life=self.life
        self.briefings=BriefingManager(self);automation.briefings=self.briefings
        from server.natural.public_reads import PublicReads
        self.public_reads=PublicReads(self)
        from server.natural.handoffs import Handoffs
        self.handoffs=Handoffs(self);automation.handoffs=self.handoffs
        from server.natural.device_status import DeviceStatus
        self.device_status=DeviceStatus(self)
        from server.natural.device_broker import DeviceBroker
        self.devices=DeviceBroker(self);automation.devices=self.devices
        from server.natural.desktop_commands import DesktopCommands
        self.desktop_commands=DesktopCommands(self)
        from server.natural.vision import VisionService
        self.vision=VisionService(self)
        from server.natural.environment import EnvironmentCommands
        self.environment=EnvironmentCommands(self)
        automation.desktop_monitor=self.desktop_commands.monitor
        chat.natural=self

    def task_event(self,db,identifier,event,job,device):
        labels={'completed':'afgerond','failed':'mislukt','uncertain':'uitkomst onzeker','deadline_expired':'deadline verstreken','blocked':'geblokkeerd'}
        if event not in labels or not device:return
        row=db.execute('SELECT status,tool FROM automation_jobs WHERE id=?',(job,)).fetchone()
        if not row or row['tool'] in ('PersonalBriefing','MobileHandoff','WaitForReply') or event=='completed' and row['status']!='completed':return
        owner=db.execute('SELECT user_id FROM auth_devices WHERE id=? AND revoked_at IS NULL',(device,)).fetchone()
        if not owner:return
        self.events.publish(db,owner[0],device,'task.changed',{'text':'Taakstatus: '+labels[event]+'. Bekijk Taken voor de bevestigde uitkomst.','job_id':job},'task-event:'+str(identifier),priority=2 if event in ('uncertain','failed') else 1)

    def authorize_conversation(self,principal,conversation):
        with self.store.transaction(principal,write=True) as (db,user):
            if not db.execute('SELECT id FROM chat_conversations WHERE id=?',(conversation,)).fetchone():
                from server.chat_store import ChatError
                raise ChatError('not_found','Gesprek niet gevonden.',404)
            owner=db.execute("SELECT user_id FROM natural_conversation_owners WHERE conversation_id=?",(conversation,)).fetchone()
            # The existing database has exactly one owner account (id=1).
            # Conversations created before natural mode belong to that owner.
            if not owner and user==1:
                db.execute("INSERT INTO natural_conversation_owners VALUES (?,?)",(conversation,user))
            elif not owner or owner["user_id"]!=user:
                raise ValueError("Gesprek niet gevonden")

    def prepare(self,run):
        self.authorize_conversation(run.principal,run.conversation_id)
        self.check_audio(run)
        if not run.persist_history:
            config=self.settings.get(run.principal)["settings"]
            turns=self.context.private_turns(run.principal,run.conversation_id,config)
            run.history=[item for row in turns for item in ({"role":"user","content":row["user_text"]},{"role":"assistant","content":row["assistant_text"]})]
        prepared=self.context.prepare(run)
        prepared['planning']=self.planning.prepare(run,prepared)
        messages,metrics=self.context.build(run,prepared)
        return prepared,messages,metrics

    def check_audio(self,run):
        if run.session_epoch is not None:
            if run.channel!="voice":raise Conflict("Audioversie vereist een spraakverzoek")
            state=self.conversations._get(run.principal,run.conversation_id)
            if state["state"] in (State.STANDBY,State.ENDING,State.RECONNECTING,State.ERROR):raise Conflict("Audiosessie niet actief")
            with self.store.transaction(run.principal) as (db,user):
                row=db.execute("SELECT * FROM natural_sessions WHERE conversation_id=? AND user_id=?",(run.conversation_id,user)).fetchone()
                if not row or row["device_id"]!=run.principal.device_id or row["auth_session"]!=run.principal.session_id or row["epoch"]!=run.session_epoch or row["lease_until"]<=self.store.clock():
                    raise Conflict("Audiosessie verlopen of overgenomen")

    async def phase(self,run,state):
        if run.session_epoch is not None:
            return await self.conversations.transition(run.principal,run.conversation_id,state,run.session_epoch)

    def command(self,run):
        response=self.responses.command(run)
        if response is not None:return response
        response=self.presence.command(run)
        if response is not None:return response
        response=self.life.command(run)
        if response is not None:return response
        """Explicit memory commands are executed locally, never by generated code."""
        message=run.message.strip();config=run.natural_context["settings"]
        if CAPABILITIES.fullmatch(message):
            features=self.automation.integrations.status().get("features",[])
            permissions=run.principal.permissions
            abilities=["met je praten en vragen beantwoorden"]
            if config["memory"]["long_term"]:abilities.append("op jouw verzoek voorkeuren onthouden en vergeten")
            if "automation:read" in permissions:
                if "calendar_read" in features:abilities.append("je agenda opvragen")
                if "gmail_read" in features:abilities.append("e-mails zoeken en op verzoek lezen")
            if "automation:write" in permissions and config["autonomy"]["profile"]!="read_propose":
                if "calendar_write" in features:abilities.append("afspraken voorbereiden")
                if "gmail_compose" in features:abilities.append("mailconcepten voorbereiden")
            return "Ik kan "+", ".join(abilities)+". Agenda wijzigen of een mail versturen gebeurt alleen na het volledige voorstel en jouw goedkeuring. Je kunt bijvoorbeeld zeggen: ‘Ik wil een afspraak maken’, en daarna de gegevens aanvullen."
        if OPEN_TASKS.fullmatch(message):
            self.automation.permissions.check(run.principal.device_id,"automation:read")
            with self.store.transaction(run.principal) as (db,user):
                rows=db.execute("SELECT j.id,j.tool,j.status FROM automation_jobs j JOIN auth_devices d ON d.id=j.device_id WHERE d.user_id=? AND j.status IN ('approval','queued','waiting','paused','blocked','uncertain') ORDER BY j.updated DESC LIMIT 21",(user,)).fetchall()
            if not rows:return "Er staan geen openstaande automatiseringstaken klaar."
            names={"approval":"wacht op jouw toestemming","queued":"ingepland","waiting":"wacht op resultaat","paused":"gepauzeerd","blocked":"geblokkeerd","uncertain":"uitkomst niet bevestigd"}
            return "Je openstaande taken:\n"+"\n".join(f"- {row['tool']}: {names[row['status']]} (taak {row['id']})." for row in rows[:20])+("\nBekijk Automatiseringen voor de overige taken." if len(rows)>20 else "")
        match=re.fullmatch(r"(?:jarvis[, ]+)?onthou(?:d)?(?: dat)?\s+(.+)",message,re.I|re.S)
        if match:
            if not config["memory"]["long_term"] or config["autonomy"]["actions"].get("MemorySave")=="block":
                return "Langetermijngeheugen is uitgeschakeld of geblokkeerd."
            content=match.group(1).strip()
            source=run.request_id
            if content.casefold().rstrip(".!") in ("dit","dat"):
                turns=run.natural_context["turns"]
                previous=turns[-1] if turns else None
                if not previous or "?" in previous["user_text"] or not re.match(r"(?:ik|mijn)\b",previous["user_text"],re.I):return "Wat wil je precies dat ik onthoud? Noem de voorkeur of het feit."
                content=previous["user_text"];source=previous["id"]
            value=preference(content) or {"content":content,"kind":"preference" if re.search(r"\b(liever|voorkeur|liefst)\b",content,re.I) else "fact"}
            if config['autonomy']['actions'].get('MemorySave')=='advise':value['status']='proposed'
            try:
                saved=self.memory.save(run.principal,value,source="conversation",source_turn=source)
                self.remember_memory_refs(run,[saved])
            except ValueError:
                return "Dit kan ik niet als gewone herinnering opslaan. Gevoelige gegevens vereisen expliciete toestemming via geheugenbeheer; geheimen sla ik niet op."
            return 'Ik heb dit als geheugenvoorstel klaargezet, meneer.' if saved['status']=='proposed' else 'Ik heb dit onthouden, meneer. U kunt het beheren bij Geheugen.'
        if re.fullmatch(r"(?:jarvis[, ]+)?wat (?:weet|onthoud) je (?:nog )?(?:over|van) mij[?.!]*",message,re.I):
            items=self.memory.list(run.principal,status="active",include_sensitive=False,limit=20)["items"]
            items=[item for item in items if item["expires"] is None or item["expires"]>self.store.clock()]
            self.remember_memory_refs(run,items)
            return ("Dit heb ik onthouden:\n"+"\n".join(f"- {item['content']}" for item in items)) if items else "Ik heb nog geen actieve gewone herinneringen over je opgeslagen."
        match=re.fullmatch(r"(?:jarvis[, ]+)?vergeet\s+(.+?)[.!]*",message,re.I|re.S)
        if match:
            if config["autonomy"]["actions"].get("MemoryUpdate")=="block":return "Geheugenwijzigingen zijn geblokkeerd."
            query=match.group(1).strip()
            if query.casefold() in ("dat","dit"):
                items=self.last_memory_refs(run)
                if len(items)!=1:return "Welke herinnering bedoel je precies? Noem de inhoud of kies haar in geheugenbeheer."
                try:self.memory.delete(run.principal,items[0]["id"],items[0]["revision"])
                except ValueError:return "Die herinnering is gewijzigd of al verwijderd. Bekijk de actuele herinnering voordat je haar vergeet."
                return "Die herinnering is verwijderd. De oorspronkelijke gesprekken bestaan nog afzonderlijk."
            if query.casefold()=="alles":
                return "Welke herinnering bedoel je precies? Noem de inhoud of verwijder haar via geheugenbeheer. De volledige geheugenlijst wissen vraagt daar een aparte bevestiging."
            items=self.memory.list(run.principal,query=query,status="active",limit=2,include_sensitive=False)["items"]
            if len(items)!=1:return "Ik vind geen unieke herinnering. Noem iets specifiekers of kies de herinnering in geheugenbeheer."
            self.memory.delete(run.principal,items[0]["id"],items[0]["revision"])
            return "Die herinnering is verwijderd en wordt niet meer als geheugen opgehaald. Het oorspronkelijke gesprek bestaat nog in de gespreksgeschiedenis."
        return None

    def remember_memory_refs(self,run,items):
        with self.store.transaction(run.principal,write=True) as (db,user):
            identifier=str(uuid.uuid5(uuid.NAMESPACE_URL,f"jarvis:memory-reference:{user}:{run.conversation_id}"));now=self.store.clock()
            payload=encode({"shown_turn":run.request_id,"items":[{"id":item["id"],"revision":item["revision"]} for item in items]})
            db.execute("INSERT INTO natural_pending VALUES (?,?,?,?,?,1,?,?,'completed') ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,revision=natural_pending.revision+1,updated=excluded.updated",(identifier,user,run.conversation_id,"memory_reference",payload,now,now))
            # Explicit list responses contain memory text too, even when ordinary
            # retrieval returned no candidates. Track those derived turns.
            if items:
                old=db.execute("SELECT payload FROM natural_pending WHERE id=? AND user_id=? AND kind='memory_context'",(run.request_id,user)).fetchone()
                ids=list(dict.fromkeys([*(json.loads(old["payload"]) if old else []),*(item["id"] for item in items)]))
                db.execute("INSERT INTO natural_pending VALUES (?,?,?,?,?,1,?,?,'completed') ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,revision=natural_pending.revision+1,updated=excluded.updated",(run.request_id,user,run.conversation_id,"memory_context",encode(ids),now,now))

    def last_memory_refs(self,run):
        turns=run.natural_context["turns"]
        if not turns:return []
        with self.store.transaction(run.principal) as (db,user):
            identifier=str(uuid.uuid5(uuid.NAMESPACE_URL,f"jarvis:memory-reference:{user}:{run.conversation_id}"))
            row=db.execute("SELECT payload FROM natural_pending WHERE id=? AND user_id=? AND kind='memory_reference'",(identifier,user)).fetchone()
        payload=json.loads(row["payload"]) if row else {}
        return payload.get("items",[]) if payload.get("shown_turn")==turns[-1]["id"] else []

    def automatic_memory(self,run):
        config=run.natural_context["settings"]
        if not run.persist_history or not config["memory"]["automatic"] or not config["memory"]["long_term"] or self.is_command(run):return
        autonomy=config["autonomy"]
        if autonomy["actions"].get("MemorySave")=="block":return
        value=automatic_preference(run.message)
        if value is None:return
        existing=self.memory.list(run.principal,query=value["content"],limit=100)["items"]
        if any(row["content"]==value["content"] for row in existing):return
        if value["key"] and autonomy["actions"].get("MemoryUpdate") in ('block','ask','advise'):value["status"]="proposed"
        else:value["status"]="active" if autonomy["profile"]=="within_rules" and autonomy["actions"].get("MemorySave") not in ('ask','advise') else "proposed"
        self.memory.save(run.principal,value,source="automatic_preference",source_turn=run.request_id,explicit=False)

    async def stream_command(self,run):
        import asyncio
        from server.natural.briefings import REQUEST as BRIEFING_REQUEST
        desktop=self.desktop_commands.parse(run.message)
        environment=self.environment.parse(run.message)
        public=self.public_reads.parse(run)
        if public:reply=await self.public_reads.answer(run,public)
        elif self.stop_command(run.message):
            await self.automation.safety.set(run.principal,True,exclude_request=run.request_id)
            self.chat.automation_chat.remember(run,'pending',[])
            reply='De noodstop is actief, meneer. Openstaande taken zijn gepauzeerd. Reeds verzonden opdrachten kunnen niet worden teruggehaald.'
        elif desktop and environment:
            from server.natural.presence import address
            reply=address('Bedoelt u het Windows-programma of de Home Assistant-koppeling?',run.natural_context['settings'])
        elif desktop:reply=await self.desktop_commands.answer(run,desktop)
        elif environment:reply=await self.environment.answer(run,environment)
        elif BRIEFING_REQUEST.fullmatch(run.message.strip()):reply=await self.briefings.answer(run)
        else:reply=await asyncio.to_thread(self.command,run)
        if reply is not None:
            yield {"type":"provider","provider":"local","model":"memory"}
            yield {"type":"delta","text":reply}

    def is_command(self,run):
        from server.natural.briefings import REQUEST as BRIEFING_REQUEST
        if self.public_reads.parse(run) or self.stop_command(run.message) or BRIEFING_REQUEST.fullmatch(run.message.strip()) or self.life.intent(run.message) or self.desktop_commands.parse(run.message) or self.environment.parse(run.message):return True
        return bool(self.presence.intent(run.message) or (run.natural_context and IntelligentResponseManager.preference(run.message,run.natural_context["settings"])) or CAPABILITIES.fullmatch(run.message.strip()) or OPEN_TASKS.fullmatch(run.message.strip()) or re.match(r"^(?:jarvis[, ]+)?(?:onthou(?:d)?\b|vergeet\b|wat (?:weet|onthoud) je (?:nog )?(?:over|van) mij[?.!]*$)",run.message.strip(),re.I))

    @staticmethod
    def stop_command(message):
        return bool(re.fullmatch(r'(?:jarvis[, ]+)?(?:noodstop|stop alle (?:acties|taken|automatiseringen))[.!?]*',message.strip(),re.I))
