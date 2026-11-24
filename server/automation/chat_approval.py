"""Explicit chat decisions, bound to the exact server preview most recently shown."""
import asyncio
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from server.automation.store import fingerprint

DECISION = re.compile(r"\s*(goedkeuren|keur (?:dit |het )?voorstel goed|weiger(?:en)?(?: (?:dit |het )?voorstel)?)\s*[.!]?\s*", re.I)
YES_NO = re.compile(r"\s*(ja(?:,?\s+(?:graag|doe maar|verstuur(?: hem)?|verzend(?: hem)?|goedkeuren))?|nee(?:,?\s+(?:niet doen|annuleren))?)\s*[.!?]?\s*", re.I)
SHOW = re.compile(r"\s*(?:toon|bekijk|laat zien)(?: mij)?(?: mijn| het| de)?(?: openstaande)? voorstel(?:len)?\s*([0-9a-f-]{36})?\s*[?.!]?\s*", re.I)
STATUS = re.compile(r"\s*(?:is (?:het|dit) voorstel klaar|wat is de status van (?:het|dit) voorstel)\s*[?.!]?\s*", re.I)


class ChatApprovals:
    def __init__(self, chat): self.chat = chat

    def candidate(self, message): return bool(DECISION.fullmatch(message) or SHOW.fullmatch(message) or STATUS.fullmatch(message))

    def is_answer(self, message): return bool(YES_NO.fullmatch(message))

    def show(self, run, row):
        c = self.chat; c.guard(run, "automation:read")
        if row["status"] != "approval": return self.status(row)
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
            text = "Voorstel: " + title + "\nAgenda: " + payload["calendar_id"] + "\nTitel: " + payload["summary"]
            for label, key in (("Van", "start"), ("Tot", "end")):
                value = payload.get(key)
                text += "\n" + label + ": " + (datetime.fromisoformat(value).astimezone(ZoneInfo(payload["timezone"])).strftime("%d-%m-%Y %H:%M %z") if value else "Hele dag / controleer Google")
            text += "\nTijdzone: " + payload["timezone"] + "\nLocatie: " + (payload.get("location") or "Geen")
            text += "\nGenodigden: " + (", ".join(payload.get("attendees", [])) or "Geen")
            text += "\nHerhaling: " + ("; ".join(payload.get("recurrence", [])) or "Geen")
            if payload.get("attendees"): text += "\nGoogle Calendar stuurt updates aan de genodigden."
        text = "Ik heb een wijzigingsvoorstel klaargezet.\n"+text
        text += "\nVoorstel-ID: " + row["id"] + "\n\nZal ik dit uitvoeren? Zeg ‘ja’ om dit voorstel te bevestigen, of ‘nee’ om het af te wijzen."
        if c.clean(text)!=text or len(text) > min(16000, c.router.settings.max_response_chars):
            c.remember(run, "pending", [])
            return "Dit voorstel kan niet volledig in de chat worden getoond. Open Automatiseringen → Goedkeuringen voor de volledige controle."
        c.remember(run, "pending", [{"id":row["id"], "fingerprint":fingerprint([tool,payload]), "preview_hash":fingerprint(text), "request_id":run.request_id, "shown":c.clock()}])
        return text

    @staticmethod
    def status(row):
        state = row["status"]
        if state == "completed":
            return {"CalendarCreate":"De afspraak is aangemaakt.", "CalendarUpdate":"De afspraak is gewijzigd.", "CalendarDelete":"De afspraak is verwijderd.", "EmailSend":"De e-mail is verzonden."}.get(row["tool"], "De taak is uitgevoerd.")
        if state == "denied": return "Het voorstel is geweigerd. Er is niets uitgevoerd."
        if state in ("queued", "running"): return "Het voorstel is goedgekeurd en staat klaar of wordt uitgevoerd. Vraag ‘Is het voorstel klaar?’ voor de actuele status."
        if state == "uncertain": return "De uitkomst is onzeker. Controleer Google voordat je de actie opnieuw probeert; ik herhaal hem niet automatisch."
        return "De uitvoering is niet bevestigd. Taakstatus: " + state + ". Controleer de taak bij Automatiseringen."

    def proposals(self):
        with self.chat.engine.store.db() as db:
            return [dict(row) for row in db.execute("SELECT * FROM automation_jobs WHERE status='approval' ORDER BY created DESC LIMIT 21")]

    async def handle(self, run):
        c = self.chat; message = run.message; memory = c.memory(run)
        show = SHOW.fullmatch(message); decision = DECISION.fullmatch(message)
        spoken = YES_NO.fullmatch(message)
        if spoken and memory.get("pending"):decision=spoken
        elif spoken and memory.get("decision"):
            previous=run.history[-1] if run.history else {}
            if fingerprint(previous.get("content",""))==memory["decision"][0].get("response_hash"):
                return self.status(c.engine.store.get(memory["decision"][0]["id"]))
        if STATUS.fullmatch(message):
            last = memory.get("decision", [])
            return self.status(c.engine.store.get(last[0]["id"])) if last else "Er is in dit gesprek nog geen voorstel goedgekeurd. Vraag ‘Toon mijn voorstellen’."
        if show:
            if show[1]: return self.show(run, c.engine.store.get(show[1]))
            rows = self.proposals()
            if len(rows) == 1: return self.show(run, rows[0])
            if not rows: return "Er zijn geen openstaande voorstellen."
            return "Openstaande voorstellen:\n" + "\n".join(row["tool"] + " — " + row["id"] for row in rows[:20]) + "\nTyp ‘Toon voorstel’ gevolgd door het gewenste voorstel-ID." + ("\nLijst ingekort." if len(rows)>20 else "")
        if not decision: return None
        c.guard(run, "automation:approve")
        pending = memory.get("pending", [])
        if len(pending) != 1:
            rows = self.proposals()
            return self.show(run, rows[0]) if len(rows)==1 else "Vraag eerst ‘Toon mijn voorstellen’ en bekijk het exacte voorstel dat je wilt goedkeuren."
        shown = pending[0]; row = c.engine.store.get(shown["id"])
        if row["status"] != "approval":
            c.remember(run, "pending", [])
            return self.status(row)
        previous = run.history[-1] if run.history else {}
        with c.engine.store.db() as db:
            latest=db.execute("SELECT id,status FROM chat_turns WHERE conversation_id=? AND id!=? ORDER BY sequence DESC LIMIT 1",(run.conversation_id,run.request_id)).fetchone()
        actual = fingerprint([row["tool"], json.loads(row["payload"])])
        if not latest or latest["id"]!=shown.get("request_id") or latest["status"]!="completed" or c.clock()-shown.get("shown",0)>300 or previous.get("role")!="assistant" or fingerprint(previous.get("content",""))!=shown.get("preview_hash") or actual!=shown.get("fingerprint"):
            return self.show(run, row)
        # No model sees the nonce. Check the same payload again inside the decision transaction.
        challenge = c.engine.approvals.challenge(row["id"],run.principal)
        if challenge["fingerprint"]!=actual: return self.show(run,c.engine.store.get(row["id"]))
        c.guard(run, "automation:approve")
        approved = not decision[1].casefold().startswith(("weiger","nee"))
        result = c.engine.approvals.decide(row["id"],run.principal,challenge["token"],approved,expected_fingerprint=actual)
        c.remember(run,"pending",[]);c.remember(run,"decision",[{"id":row["id"]}])
        if approved:
            for _ in range(20):
                c.guard(run,"automation:read")
                result=c.engine.store.get(row["id"])
                if result["status"] not in ("queued","running"):break
                await asyncio.sleep(.25)
        text=self.status(result)
        c.remember(run,"decision",[{"id":row["id"],"response_hash":fingerprint(c.clean(text))}])
        return text
