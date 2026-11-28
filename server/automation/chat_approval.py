"""Explicit chat decisions, bound to the exact server preview most recently shown."""
import asyncio
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from server.automation.store import fingerprint

DECISION = re.compile(r"\s*(goedkeuren|keur (?:dit |het )?voorstel goed|weiger(?:en)?(?: (?:dit |het )?voorstel)?)\s*[.!]?\s*", re.I)
YES_NO = re.compile(r"\s*(ja(?:,?\s+(?:graag|doe maar|verstuur(?: hem)?|verzend(?: hem)?|goedkeuren))?|doe maar|dat is goed|is goed|akkoord|nee(?:,?\s+(?:niet doen|annuleren))?|laat maar|annuleer dat)\s*[.!?]?\s*", re.I)
SHOW = re.compile(r"\s*(?:toon|bekijk|laat zien)(?: mij)?(?: mijn| het| de)?(?: openstaande)? voorstel(?:len)?\s*([0-9a-f-]{36})?\s*[?.!]?\s*", re.I)
STATUS = re.compile(r"\s*(?:is (?:het|dit) voorstel klaar|wat is de status van (?:het|dit) voorstel)\s*[?.!]?\s*", re.I)


class ChatApprovals:
    def __init__(self, chat): self.chat = chat

    def candidate(self, message): return bool(DECISION.fullmatch(message) or SHOW.fullmatch(message) or STATUS.fullmatch(message))

    def is_answer(self, message): return bool(YES_NO.fullmatch(message))

    def record_display(self,run):
        pending=self.chat.memory(run).get('pending',[])
        if len(pending)==1 and pending[0].get('request_id')==run.request_id:
            self.chat.remember(run,'pending',[{**pending[0],'display_hash':fingerprint(run.text)}])

    def show(self, run, row):
        c = self.chat; c.guard(run, "automation:read")
        if row["status"] != "approval":
            c.remember(run,'pending',[])
            return self.status(row)
        payload = json.loads(row["payload"]); tool = row["tool"]
        if tool not in ("CalendarCreate", "CalendarUpdate", "CalendarDelete", "EmailSend"):
            return "Controleer dit uitgebreide voorstel bij Automatiseringen → Goedkeuringen."
        if tool == "EmailSend":
            text = "Voorstel: e-mail verzenden\n" + payload["preview"]
        else:
            if not payload.get("start") or not payload.get("end"):
                c.remember(run,"pending",[])
                return "De volledige datum en tijd ontbreken in dit voorstel. Controleer het bij Automatiseringen → Goedkeuringen."
            title = {"CalendarCreate":"Afspraak aanmaken", "CalendarUpdate":"Afspraak wijzigen", "CalendarDelete":"Afspraak verwijderen"}[tool]
            text = title + ': ' + payload['summary']
            for label, key in (("Van", "start"), ("Tot", "end")):
                value = payload.get(key)
                text += "\n" + label + ": " + (datetime.fromisoformat(value).astimezone(ZoneInfo(payload["timezone"])).strftime("%d-%m-%Y %H:%M %z") if value else "Hele dag / controleer Google")
            if payload.get('location'):text+='\nLocatie: '+payload['location']
            if payload.get('description'):text+='\nBeschrijving: '+payload['description']
            text += "\nGenodigden: " + (", ".join(payload.get("attendees", [])) or "Geen")
            text += "\nHerhaling: " + ("; ".join(payload.get("recurrence", [])) or "Geen")
            if tool!="CalendarDelete":text += "\nHerinnering: " + (str(payload["reminder_minutes"])+" minuten vooraf" if payload.get("reminder_minutes") is not None else "Bestaande agenda-instelling")
            if payload.get("attendees"): text += "\nGoogle Calendar stuurt updates aan de genodigden."
        if tool=='CalendarUpdate' and not payload.get('attendees') and not payload.get('recurrence'):
            text='Zal ik de afspraak voor u wijzigen?'
        else:text='Ik heb een wijzigingsvoorstel klaargezet.\n'+text+'\n\nZal ik dit voor u uitvoeren?'
        if c.clean(text)!=text or len(text) > min(16000, c.router.settings.max_response_chars):
            c.remember(run, "pending", [])
            return "Dit voorstel kan niet volledig in de chat worden getoond. Open Automatiseringen → Goedkeuringen voor de volledige controle."
        previous=c.memory(run).get("pending",[])
        instruction=run.message if c.write_intent(tool,run.message) else (previous[0].get("instruction","") if len(previous)==1 and previous[0]["id"]==row["id"] else "")
        c.remember_many(run,{'decision':[],"pending": [{"id":row["id"], "fingerprint":fingerprint([tool,payload]), "preview_hash":fingerprint(text), "request_id":run.request_id, "shown":c.clock(),"shown_at":c.engine.store.clock(),"device":run.principal.device_id,"session":run.principal.session_id,"instruction":instruction}]})
        return text

    @staticmethod
    def status(row):
        state = row["status"]
        if state=='advisory':return 'Dit is een adviesvoorstel; er is niets uitgevoerd.'
        if state=='expired':return 'De taakdeadline is verstreken; er is geen nieuwe uitvoering gestart.'
        if state == "completed":
            if row['tool'] in ('DesktopControl','DesktopMedia','DesktopPrograms','HomeControl'):
                result=json.loads(row.get('result') or '{}')
                return 'De nieuwe toestand is bevestigd.' if result.get('verified') is True else 'Het verzoek is doorgegeven; de uiteindelijke toestand is niet bevestigd.'
            return {"CalendarCreate":"Uw afspraak is aangemaakt, meneer.", "CalendarUpdate":"Uw afspraak is gewijzigd, meneer.", "CalendarDelete":"Uw afspraak is verwijderd, meneer.", "EmailSend":"Uw e-mail is verzonden, meneer."}.get(row["tool"], "De taak is uitgevoerd.")
        if state == "denied": return "Het voorstel is geweigerd. Er is niets uitgevoerd."
        if state in ("queued", "running"): return "Het voorstel is goedgekeurd en staat klaar of wordt uitgevoerd. Vraag ‘Is het voorstel klaar?’ voor de actuele status."
        if state == "uncertain": return "De uitvoering is niet bevestigd, meneer. Controleer de uitkomst; ik herhaal de opdracht niet automatisch."
        if state=='cancelled':return 'De opdracht is geannuleerd, meneer.'
        return 'De uitvoering is nog niet bevestigd, meneer. U vindt de actuele stand bij Taken.'

    def proposals(self):
        with self.chat.engine.store.db() as db:
            return [dict(row) for row in db.execute("SELECT * FROM automation_jobs WHERE status='approval' ORDER BY created DESC LIMIT 21")]

    def unbound(self,memory):
        identifiers=[item['id'] for item in memory.get('jobs',[]) if item.get('id')][:20]
        if identifiers:
            with self.chat.engine.store.db() as db:
                count=db.execute("SELECT count(*) FROM automation_jobs WHERE status='approval' AND id IN ("+','.join('?' for _ in identifiers)+')',identifiers).fetchone()[0]
            if count>1:return 'Er staan meerdere voorstellen klaar, meneer. Kies eerst het gewenste voorstel bij Taken.'
        return 'Er staat in dit gesprek geen voorstel ter bevestiging klaar, meneer.'

    async def handle(self, run):
        c = self.chat; message = run.message; memory = c.memory(run)
        show = SHOW.fullmatch(message); decision = DECISION.fullmatch(message)
        spoken = YES_NO.fullmatch(message)
        if spoken and memory.get("pending"):decision=spoken
        elif spoken and memory.get("decision"):
            previous=memory['decision'][0]
            if previous.get('device')==run.principal.device_id and previous.get('session')==run.principal.session_id:
                return self.status(c.engine.store.get(memory["decision"][0]["id"]))
        if spoken and not decision and memory.get("read_question"):return None
        if spoken and not decision:return self.unbound(memory)
        if STATUS.fullmatch(message):
            last = memory.get("decision", [])
            return self.status(c.engine.store.get(last[0]["id"])) if last else "Er is in dit gesprek nog geen voorstel goedgekeurd. Vraag ‘Toon mijn voorstellen’."
        if show:
            if show[1]: return self.show(run, c.engine.store.get(show[1]))
            rows = self.proposals()
            if len(rows) == 1: return self.show(run, rows[0])
            if not rows: return "Er zijn geen openstaande voorstellen."
            return 'Er staan meerdere voorstellen klaar, meneer. Kies het bedoelde voorstel bij Taken.'
        if not decision: return None
        pending = memory.get("pending", [])
        if len(pending) != 1:
            return self.unbound(memory)
        c.guard(run, "automation:approve")
        shown = pending[0]; row = c.engine.store.get(shown["id"])
        if row["status"] != "approval":
            c.remember(run, "pending", [])
            return self.status(row)
        with c.engine.store.db() as db:
            displayed=db.execute("SELECT status,assistant_text FROM chat_turns WHERE conversation_id=? AND id=?",(run.conversation_id,shown.get('request_id'))).fetchone()
        actual = fingerprint([row["tool"], json.loads(row["payload"])])
        if actual!=shown.get('fingerprint'):
            c.engine.control(row['id'],'cancelled',run.principal.device_id,expected_status='approval')
            c.remember_many(run,{'pending':[],'decision':[]})
            return 'De voorstelgegevens zijn intussen veranderd, meneer. Geef uw gewenste opdracht opnieuw; ik heb niets uitgevoerd.'
        if (not displayed or displayed['status']!='completed' or shown.get('display_hash')!=shown.get('preview_hash')
            or displayed['assistant_text'] and fingerprint(displayed['assistant_text'])!=shown.get('preview_hash')
            or shown.get('device')!=run.principal.device_id or shown.get('session')!=run.principal.session_id
            ):
            return self.show(run, row)
        if c.engine.store.clock()-shown.get('shown_at',0)>300 or c.clock()-shown.get('shown',0)>300:
            c.engine.control(row['id'],'cancelled',run.principal.device_id,expected_status='approval')
            c.remember(run,'pending',[])
            return 'Het voorstel is verlopen, meneer. Geef uw opdracht opnieuw als u die nog wilt uitvoeren.'
        # No model sees the nonce. Check the same payload again inside the decision transaction.
        challenge = c.engine.approvals.challenge(row["id"],run.principal)
        if challenge["fingerprint"]!=actual: return self.show(run,c.engine.store.get(row["id"]))
        c.guard(run, "automation:approve")
        approved = not decision[1].casefold().startswith(("weiger","nee","laat maar","annuleer"))
        result = c.engine.approvals.decide(row["id"],run.principal,challenge["token"],approved,expected_fingerprint=actual)
        c.remember(run,"pending",[]);c.remember(run,"decision",[{"id":row["id"],"device":run.principal.device_id,"session":run.principal.session_id}])
        if approved:
            started=__import__('time').perf_counter()
            await c.engine.tick(job_id=row['id'])
            run.timings['tool_execution_ms']=(__import__('time').perf_counter()-started)*1000
            for _ in range(20):
                c.guard(run,"automation:read")
                result=c.engine.store.get(row["id"])
                if result["status"] not in ("queued","running"):break
                await asyncio.sleep(.25)
        text=self.status(result)
        if approved and result['status']=='completed' and row['tool'] in ('CalendarCreate','CalendarUpdate'):
            event=json.loads(result.get('result') or '{}')
            if event.get('id') and event.get('etag') and event.get('start',{}).get('dateTime'):
                text=await c.calendar.result(run,result,row['tool'])
        c.remember(run,"decision",[{"id":row["id"],"response_hash":fingerprint(c.clean(text)),"device":run.principal.device_id,"session":run.principal.session_id}])
        return text
