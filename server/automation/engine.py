"""One light scheduler, durable workflows, one-use approvals and bounded audit."""
import asyncio
import hmac
import json
from datetime import datetime, UTC
from typing import Protocol

from server.automation.models import REGISTRY, validate, next_occurrence, UrgentEvent
from server.automation.store import Store, encode, fingerprint
from server.automation.google import IntegrationManager, WRITE_GUARD
from server.security.types import AuthError, digest, token

AUTOMATION_SCOPES = frozenset({"automation:read", "automation:write", "automation:approve", "integrations:manage"})


class PermissionManager:
    def __init__(self, store): self.store = store
    def check(self, device, permission):
        with self.store.db() as db:
            row=db.execute("SELECT 1 FROM auth_devices d JOIN auth_permissions p ON p.device_id=d.id WHERE d.id=? AND d.trusted=1 AND d.revoked_at IS NULL AND p.permission=?", (device,permission)).fetchone()
        if not row: raise AuthError("permission_denied", "Apparaat heeft geen automatiseringsrecht.", 403)

    def check_tool(self,device,tool):
        # Preferences only restrict authority; they never create a permission.
        with self.store.db() as db:
            row=db.execute("SELECT s.payload FROM natural_settings s JOIN auth_devices d ON d.user_id=s.user_id WHERE d.id=? AND s.scope='user' AND s.device_id=''",(device,)).fetchone()
        if not row:return
        autonomy=json.loads(row["payload"])["autonomy"]
        reads={"CalendarList","CalendarRead","EmailSearch","EmailRead","ReminderList","WorkflowStatus","CalendarSummary","EmailCheck","WaitForReply"}
        if autonomy["actions"].get(tool)=="block" or autonomy["profile"]=="read_propose" and tool not in reads:
            raise AuthError("permission_denied","Deze actie is geblokkeerd door je instellingen voor zelfstandigheid.",403)


class AuditLogger:
    def __init__(self, store): self.store=store
    def record(self,event,job=None,device=None):
        with self.store.db(True) as db: self.store.event(db,event,job,device)


class ApprovalManager:
    def __init__(self, engine): self.engine=engine
    def challenge(self, identifier, principal):
        e=self.engine; e.permissions.check(principal.device_id,"automation:approve")
        secret=token(); now=e.store.clock()
        with e.store.db(True) as db:
            row=db.execute("SELECT * FROM automation_jobs WHERE id=? AND status='approval'",(identifier,)).fetchone()
            if not row: raise ValueError("Geen openstaand voorstel")
            db.execute("UPDATE automation_jobs SET approval_hash=?,approval_expires=?,approval_device=? WHERE id=?",(digest(secret),now+300,principal.device_id,identifier))
        return {"token":secret,"expires_at":now+300,"fingerprint":fingerprint([row["tool"],json.loads(row["payload"])])}

    def decide(self, identifier, principal, secret, approve, *, expected_fingerprint=None):
        e=self.engine; e.permissions.check(principal.device_id,"automation:approve")
        with e.store.db(True) as db:
            row=db.execute("SELECT * FROM automation_jobs WHERE id=? AND status='approval'",(identifier,)).fetchone()
            if not row or row["approval_device"]!=principal.device_id or not row["approval_hash"] or row["approval_expires"]<=e.store.clock() or not hmac.compare_digest(row["approval_hash"],digest(secret)): raise ValueError("Goedkeuring verlopen of al gebruikt")
            if expected_fingerprint is not None and fingerprint([row["tool"],json.loads(row["payload"])])!=expected_fingerprint:raise ValueError("Voorstel gewijzigd; bekijk het opnieuw")
            db.execute("UPDATE automation_jobs SET status=?,approval_hash=NULL,approved_device=?,updated=? WHERE id=?",("queued" if approve else "denied",principal.device_id,e.store.clock(),identifier))
            e.store.event(db,"approved" if approve else "denied",identifier,principal.device_id)
        return e.store.public(e.store.get(identifier))


class NotificationManager:
    def __init__(self, store): self.store=store
    def send(self, category, text, key, job=None, *,device=None,proactive=False):
        now=self.store.clock(); rules=self.store.preference("notifications",{"quiet_start":22,"quiet_end":7,"max_hour":10,"categories":["urgent","appointments","important","news"],"timezone":"Europe/Amsterdam"})
        preferences=None
        with self.store.db() as db:
            if device is None and job:
                owner=db.execute("SELECT device_id FROM automation_jobs WHERE id=?",(job,)).fetchone()
                device=owner["device_id"] if owner else None
            if device:
                saved=db.execute("SELECT s.payload FROM natural_settings s JOIN auth_devices d ON d.user_id=s.user_id WHERE d.id=? AND s.scope='user' AND s.device_id=''",(device,)).fetchone()
                preferences=json.loads(saved["payload"]) if saved else None
        if preferences:
            notification=preferences["notifications"]
            if not notification["enabled"] or proactive and (notification["proactivity"]=="off" or notification["suggestions_per_hour"]==0):return {"suppressed":True}
            rules={**rules,"quiet_start":notification["quiet_start"],"quiet_end":notification["quiet_end"],"timezone":preferences["general"]["timezone"]}
            if proactive:rules["max_hour"]=min(rules["max_hour"],notification["suggestions_per_hour"])
        if rules["max_hour"]<=0:return {"suppressed":True}
        from zoneinfo import ZoneInfo
        hour=datetime.fromtimestamp(now,UTC).astimezone(ZoneInfo(rules["timezone"])).hour
        start,end=rules["quiet_start"],rules["quiet_end"]
        quiet=(start<=hour<end if start<end else hour>=start or hour<end) if start!=end else False
        if category not in rules["categories"]: return {"suppressed":True}
        deliver_at=now
        if category!="urgent" and quiet:
            from datetime import timedelta
            local=datetime.fromtimestamp(now,UTC).astimezone(ZoneInfo(rules["timezone"]))
            end_time=local.replace(hour=end,minute=0,second=0,microsecond=0)
            if end_time.timestamp()<=now:end_time+=timedelta(days=1)
            deliver_at=end_time.timestamp()
        with self.store.db(True) as db:
            while db.execute("SELECT COUNT(*) FROM automation_notifications WHERE at>? AND at<=?",(deliver_at-3600,deliver_at)).fetchone()[0]>=rules["max_hour"]:
                first=db.execute("SELECT MIN(at) FROM automation_notifications WHERE at>? AND at<=?",(deliver_at-3600,deliver_at)).fetchone()[0]
                deliver_at=first+3600.001
            db.execute("INSERT OR IGNORE INTO automation_notifications VALUES (?,?,?,?,?,?)",(digest(key),key,deliver_at,category,text,job))
            db.execute("DELETE FROM automation_notifications WHERE at<?",(now-30*86400,))
        return {"notification_id":digest(key),"delivery":"authenticated_inbox","external_push":False}


class EmailPriorityClassifier:
    def classify(self, sender, subject, text="", rules=None):
        rules=rules or {}; content=(subject+" "+text).casefold()
        if sender.casefold() in [x.casefold() for x in rules.get("important_senders",[])]: return {"priority":"important","reason":"Gebruikersregel","verified_urgent":False}
        if any(x in content for x in ("unsubscribe","nieuwsbrief","aanbieding","reclame")): return {"priority":"low_priority","reason":"Nieuwsbrief/reclamesignaal","verified_urgent":False}
        if any(x in content for x in rules.get("urgent_terms",["deadline vandaag","dringend","urgent"])): return {"priority":"urgent","reason":"Tijdgevoelig signaal; controleer zelf","verified_urgent":False}
        return {"priority":"normal","reason":"Geen expliciete prioriteitsregel","verified_urgent":False}


class MessagingProvider(Protocol):
    async def prepare(self, recipient: str, text: str) -> dict: ...


class ManualMessagingProvider:
    async def prepare(self,recipient,text):
        return {"recipient":recipient,"text":text,"delivery":"manual_share","sent":False,"reply_tracking":False}


class NewsProvider(Protocol):
    async def headlines(self, interests: list[str]) -> list[dict]: ...


class UrgentCallTrigger(Protocol):
    async def notify(self, event: UrgentEvent) -> None: ...


class FollowUpManager:
    def __init__(self, engine): self.engine=engine

    def options(self,device):
        with self.engine.store.db() as db:
            row=db.execute("SELECT s.payload FROM natural_settings s JOIN auth_devices d ON d.user_id=s.user_id WHERE d.id=? AND s.scope='user' AND s.device_id=''",(device,)).fetchone()
        return json.loads(row["payload"])["tasks"] if row else {"automatic_followups":False,"followup_hours":48}

    def schedule_automatic(self):
        """Recover optional read-only follow-ups from confirmed sends, never resend."""
        e=self.engine
        with e.store.db() as db:
            rows=db.execute("""SELECT j.*,s.payload AS settings_payload,s.updated AS settings_updated
                FROM automation_jobs j JOIN auth_devices d ON d.id=j.device_id
                JOIN natural_settings s ON s.user_id=d.user_id AND s.scope='user' AND s.device_id=''
                WHERE j.tool='EmailSend' AND j.status='completed' AND j.result IS NOT NULL
                AND j.updated>=s.updated AND NOT EXISTS
                    (SELECT 1 FROM automation_jobs f WHERE f.key='auto-followup:'||j.id)
                ORDER BY j.updated DESC LIMIT 20""").fetchall()
        for row in rows:
            config=json.loads(row["settings_payload"]);tasks=config["tasks"]
            if not tasks["automatic_followups"]:continue
            result=json.loads(row["result"])
            if result.get("verified") is not True or not result.get("threadId"):continue
            try:
                e.permissions.check(row["device_id"],"automation:read")
                e.permissions.check_tool(row["device_id"],"EmailRead")
                due=row["updated"]+tasks["followup_hours"]*3600
                e.submit(row["device_id"],"WaitForReply",{
                    "thread_id":result["threadId"],"since":datetime.fromtimestamp(row["updated"],UTC).isoformat(),
                    "due":datetime.fromtimestamp(due,UTC).isoformat()},"auto-followup:"+row["id"])
            except (AuthError,ValueError):
                # An optional read task cannot invalidate an already verified send.
                continue

    async def check(self):
        e=self.engine
        with e.store.db() as db: rows=db.execute("SELECT * FROM automation_followups WHERE status='waiting' AND due<=? LIMIT 3",(e.store.clock(),)).fetchall()
        for row in rows:
            automatic=False
            try:
                if {"EmailRead","WaitForReply"}.intersection(e.store.preference("disabled_tools",[])):
                    raise AuthError("permission_denied","Opvolging is uitgeschakeld",403)
                e.permissions.check(row["device_id"],"automation:write")
                e.permissions.check(row["device_id"],"automation:read")
                e.permissions.check_tool(row["device_id"],"WaitForReply")
                e.permissions.check_tool(row["device_id"],"EmailRead")
            except AuthError:
                with e.store.db(True) as db:db.execute("UPDATE automation_followups SET status='blocked' WHERE id=?",(row["id"],))
                continue
            try:
                job=e.store.get(row["id"])
                automatic=job["key"].startswith("auto-followup:")
                if automatic and not self.options(row["device_id"])["automatic_followups"]:
                    with e.store.db(True) as db:db.execute("UPDATE automation_followups SET due=? WHERE id=?",(e.store.clock()+900,row["id"]))
                    continue
                if job["parent_id"] and e.store.get(job["parent_id"])["status"]!="waiting":continue
            except ValueError:pass  # standalone follow-up has no workflow job
            with e.store.db(True) as db:db.execute("UPDATE automation_followups SET due=? WHERE id=?",(e.store.clock()+900,row["id"]))
            try:
                async with asyncio.timeout(8):
                    data=await e.integrations.api("gmail_read","/gmail/v1/users/me/threads/"+row["thread_id"],params={"format":"metadata"})
            except Exception:
                e.audit.record("followup_read_unavailable",device=row["device_id"])
                continue
            new=[m for m in data.get("messages",[]) if m["id"] not in json.loads(row["baseline"]) and "SENT" not in m.get("labelIds",[]) and "DRAFT" not in m.get("labelIds",[])]
            # Replies never imply permission to change an event. The owner reviews them.
            e.notifications.send("important","Er is een antwoord om te beoordelen." if new else "Nog geen antwoord op je verzoek.","followup:"+row["id"],device=row["device_id"],proactive=True)
            interval=self.options(row["device_id"])["followup_hours"]*3600 if automatic else 86400
            with e.store.db(True) as db:
                db.execute("UPDATE automation_followups SET status=?,due=? WHERE id=?",("reply_review" if new else "waiting",e.store.clock()+interval,row["id"]))
                db.execute("UPDATE automation_jobs SET status=?,result=? WHERE id=? AND tool='WaitForReply' AND status='waiting'",("completed" if new else "blocked",encode({"reply_requires_review":bool(new),"accepted":False}),row["id"]))
                e.store.event(db,"followup_reply" if new else "followup_reminder",device=row["device_id"])


class WorkflowManager:
    def __init__(self, engine): self.engine=engine
    def advance(self):
        e=self.engine
        with e.store.db() as db: rows=db.execute("SELECT * FROM automation_jobs WHERE tool='WorkflowCreate' AND status='waiting' LIMIT 50").fetchall()
        for row in rows:
            steps=json.loads(row["payload"])["steps"]
            with e.store.db() as db: children=db.execute("SELECT * FROM automation_jobs WHERE parent_id=? ORDER BY step",(row["id"],)).fetchall()
            if children and children[-1]["status"] not in ("completed",):
                if children[-1]["status"] in ("denied","cancelled","uncertain","failed"):
                    with e.store.db(True) as db: db.execute("UPDATE automation_jobs SET status='blocked' WHERE id=?",(row["id"],))
                continue
            index=len(children)
            if index==len(steps):
                with e.store.db(True) as db: db.execute("UPDATE automation_jobs SET status='completed' WHERE id=?",(row["id"],))
            else:
                step=steps[index]
                try:e.submit(row["device_id"],step["tool"],step["input"],row["id"]+":"+str(index),parent=row["id"],step=index)
                except (AuthError,ValueError):
                    with e.store.db(True) as db:
                        db.execute("UPDATE automation_jobs SET status='blocked' WHERE id=?",(row["id"],))
                        e.store.event(db,"workflow_permission_blocked",row["id"],row["device_id"])


class TriggerManager:
    def __init__(self, engine): self.engine=engine
    def due(self):
        with self.engine.store.db() as db: return [dict(r) for r in db.execute("SELECT * FROM automation_jobs WHERE status='queued' AND due<=? ORDER BY CASE WHEN tool IN ('ReminderCreate','NotificationSend') THEN 0 ELSE 1 END,due LIMIT 10",(self.engine.store.clock(),))]


class ActionExecutor:
    def __init__(self, engine): self.engine=engine
    async def execute(self, row):
        e=self.engine; tool=row["tool"]; p=json.loads(row["payload"])
        if tool=="CalendarSummary":
            from datetime import timedelta
            from zoneinfo import ZoneInfo
            local=datetime.fromtimestamp(e.store.clock(),UTC).astimezone(ZoneInfo(p["timezone"]))
            start=local.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=p["day_offset"])
            data=await e.integrations.events({"calendar_id":p["calendar_id"],"start":start.isoformat(),"end":(start+timedelta(days=1)).isoformat(),"query":""})
            events=data.get("items",[])
            previews=[str(item.get("start",{}).get("dateTime",item.get("start",{}).get("date","")))+" "+str(item.get("summary","Afspraak"))[:80] for item in events[:3]]
            text=(f"Je agenda bevat {len(events)} afspraken op {start.date()}. "+"; ".join(previews)+(" De lijst is mogelijk onvolledig." if data.get("nextPageToken") else ""))[:500]
            return e.notifications.send("appointments",text,row["key"]+":"+str(row["due"]),row["id"],proactive=True)
        if tool=="EmailCheck":
            data=await e.integrations.mail_search(p["query"])
            for message in data.get("messages",[])[:30]:
                mail=await e.integrations.mail_read(message["id"])
                headers={h["name"].lower():h["value"] for h in mail.get("payload",{}).get("headers",[])}
                priority=EmailPriorityClassifier().classify(headers.get("from",""),headers.get("subject",""),"unsubscribe" if "list-unsubscribe" in headers else "",e.store.preference("email_rules",{}))
                if priority["priority"] in ("urgent","important"):e.notifications.send("important","Er is een mogelijk belangrijk bericht. Controleer je inbox.","mail:"+message["id"],row["id"],proactive=True)
            return {"checked":len(data.get("messages",[])),"urgency_verified":False}
        if tool=="WaitForReply":
            e.permissions.check(row["device_id"],"automation:read")
            e.permissions.check_tool(row["device_id"],"EmailRead")
            if "EmailRead" in e.store.preference("disabled_tools",[]):raise ValueError("Lezen is uitgeschakeld")
            if row["key"].startswith("auto-followup:") and not e.followups.options(row["device_id"])["automatic_followups"]:
                raise ValueError("Automatische opvolging is uitgeschakeld")
            data=await e.integrations.api("gmail_read","/gmail/v1/users/me/threads/"+p["thread_id"],params={"format":"metadata"})
            since=datetime.fromisoformat(p["since"]).timestamp()*1000 if p.get("since") else None
            baseline=[m["id"] for m in data.get("messages",[]) if since is None
                or "SENT" in m.get("labelIds",[]) or "DRAFT" in m.get("labelIds",[])
                or not str(m.get("internalDate","")).isdigit() or int(m["internalDate"])<=since]
            with e.store.db(True) as db:
                db.execute("INSERT OR IGNORE INTO automation_followups VALUES (?,?,?,?,?,?)",(row["id"],p["thread_id"],encode(baseline),datetime.fromisoformat(p["due"]).timestamp(),"waiting",row["device_id"]))
            return {"waiting_for_reply":True}
        if tool=="CalendarRead": return await e.integrations.events(p)
        if tool=="CalendarList": return await e.integrations.calendar_list()
        if tool.startswith("Calendar"):
            if tool=="CalendarUpdate":
                analysis=await e.reschedule.analyze(p,row["device_id"])
                if analysis["conflicts"]: raise ValueError("Nieuwe tijd heeft een conflict; kies een alternatief en maak een nieuw voorstel")
            return await e.integrations.change(tool,p,row["key"])
        if tool=="EmailSearch": return await e.integrations.mail_search(p["query"])
        if tool=="EmailRead": return await e.integrations.mail_read(p["message_id"],p["include_body"])
        if tool=="EmailDraft": return await e.integrations.draft(p)
        if tool=="EmailSend": return await e.integrations.send(p)
        if tool=="ReminderCreate": return e.notifications.send("important",p["text"],row["key"]+":"+str(row["due"]),row["id"])
        if tool=="ReminderList": return {"items":[e.store.public(x) for x in e.store.items() if x["tool"]=="ReminderCreate"]}
        if tool=="ReminderCancel":
            if e.store.get(p["id"])["tool"]!="ReminderCreate":raise ValueError("Geen herinnering")
            e.control(p["id"],"cancelled",row["device_id"]); return {"cancelled":True}
        if tool=="NotificationSend":
            result=e.notifications.send(p["category"],p["text"],row["key"],row["id"])
            if p["category"]=="urgent":
                event=UrgentEvent(event_id=digest(row["key"]),created_at=e.store.clock(),reason=p["text"],job_id=row["id"])
                e.audit.record("urgent_event",row["id"],row["device_id"])
                result["urgent_event"]=event.model_dump(mode="json")
            return result
        if tool=="WorkflowCreate": return {"workflow":"waiting"}
        if tool=="WorkflowStatus": return e.store.public(e.store.get(p["id"]))
        raise ValueError("Unknown tool")


class TaskScheduler:
    def __init__(self, engine): self.engine=engine; self.task=None
    def start(self): self.task=asyncio.create_task(self.run())
    async def run(self):
        while True:
            try: await self.engine.tick()
            except asyncio.CancelledError: raise
            except Exception: self.engine.audit.record("scheduler_check_failed")
            await asyncio.sleep(5)
    async def stop(self):
        if self.task:
            self.task.cancel()
            try: await self.task
            except asyncio.CancelledError: pass


class AutomationEngine:
    def __init__(self, database, security, *, clock=None, integrations=None):
        self.store=Store(database,**({"clock":clock} if clock else {}))
        self.permissions=PermissionManager(self.store); self.audit=AuditLogger(self.store)
        self.integrations=integrations or IntegrationManager(self.store,security,security.settings.port)
        from server.automation.reschedule import SmartRescheduleEngine
        self.reschedule=SmartRescheduleEngine(self.integrations,self.store)
        self.approvals=ApprovalManager(self); self.notifications=NotificationManager(self.store)
        self.workflows=WorkflowManager(self); self.followups=FollowUpManager(self)
        self.triggers=TriggerManager(self); self.executor=ActionExecutor(self); self.scheduler=TaskScheduler(self)
        self.lock=asyncio.Lock()

    def submit(self, device, tool, payload, key, due=None, repeat="once", timezone="Europe/Amsterdam", parent=None, step=0):
        self.permissions.check(device,"automation:write")
        self.permissions.check_tool(device,tool)
        if tool in self.store.preference("disabled_tools",[]): raise ValueError("Deze actie is uitgeschakeld door de eigenaar")
        payload=validate(tool,payload)
        if repeat!="once" and REGISTRY[tool][1]: raise ValueError("Externe wijzigingen mogen niet terugkerend worden goedgekeurd")
        if tool=="ReminderCreate":
            due=datetime.fromisoformat(payload["at"]).timestamp(); repeat=payload["repeat"]; timezone=payload["timezone"]
        return self.store.create(device,tool,payload,key,due if due is not None else self.store.clock(),repeat,timezone,REGISTRY[tool][1],parent,step)

    def control(self, identifier, status, device, *, expected_status=None):
        self.permissions.check(device,"automation:write")
        if status not in ("paused","queued","cancelled"): raise ValueError("Invalid state")
        with self.store.db(True) as db:
            row=db.execute("SELECT * FROM automation_jobs WHERE id=?",(identifier,)).fetchone()
            if not row or row["status"] not in ("paused","queued","waiting","approval","blocked"): raise ValueError("Taak kan niet gewijzigd worden")
            if expected_status is not None and row["status"]!=expected_status:raise ValueError("Taakstatus gewijzigd; controleer het actuele voorstel")
            if status=="queued" and row["status"]!="paused": raise ValueError("Alleen gepauzeerde taken hervatten")
            if row["status"]=="approval" and status!="cancelled": raise ValueError("Voorstel vereist goedkeuring")
            db.execute("UPDATE automation_jobs SET status=?,approval_hash=NULL WHERE id=?",(status,identifier))
            if status=="cancelled": db.execute("UPDATE automation_jobs SET status='cancelled',approval_hash=NULL WHERE parent_id=? AND status IN ('queued','approval','paused')",(identifier,))
            self.store.event(db,status,identifier,device)

    async def tick(self):
        async with self.lock:
            self.followups.schedule_automatic()
            self.workflows.advance()
            for row in self.triggers.due():
                if row["parent_id"] and self.store.get(row["parent_id"])["status"]!="waiting": continue
                if row["tool"] in self.store.preference("disabled_tools",[]):
                    with self.store.db(True) as db:db.execute("UPDATE automation_jobs SET status='blocked' WHERE id=? AND status='queued'",(row["id"],))
                    continue
                if REGISTRY[row["tool"]][1]:
                    try:
                        if not row["approved_device"] or row["approval_expires"]<=self.store.clock(): raise ValueError("Approval expired")
                        self.permissions.check(row["approved_device"],"automation:approve")
                    except (AuthError,ValueError):
                        with self.store.db(True) as db: db.execute("UPDATE automation_jobs SET status='approval',approval_hash=NULL,approved_device=NULL WHERE id=? AND status='queued'",(row["id"],))
                        continue
                try:
                    self.permissions.check(row["device_id"],"automation:write")
                    self.permissions.check_tool(row["device_id"],row["tool"])
                except AuthError:
                    with self.store.db(True) as db: db.execute("UPDATE automation_jobs SET status='blocked' WHERE id=? AND status='queued'",(row["id"],))
                    continue
                with self.store.db(True) as db:
                    if not db.execute("UPDATE automation_jobs SET status='running',updated=? WHERE id=? AND status='queued'",(self.store.clock(),row["id"])).rowcount: continue
                    self.store.event(db,"started",row["id"],row["device_id"])
                try:
                    def guard():
                        self.permissions.check(row["device_id"],"automation:write")
                        self.permissions.check_tool(row["device_id"],row["tool"])
                        if row["tool"] in self.store.preference("disabled_tools",[]): raise ValueError("Actie uitgeschakeld")
                        current=self.store.get(row["id"])
                        if current["status"]!="running" or current["payload"]!=row["payload"]: raise ValueError("Actie gewijzigd of gestopt")
                        if row["parent_id"] and self.store.get(row["parent_id"])["status"]!="waiting": raise ValueError("Workflow gepauzeerd of geannuleerd")
                        if REGISTRY[row["tool"]][1]:
                            if current["approval_expires"]<=self.store.clock(): raise ValueError("Goedkeuring verlopen")
                            self.permissions.check(current["approved_device"],"automation:approve")
                    context=WRITE_GUARD.set(guard)
                    try:
                        async with asyncio.timeout(90): result=await self.executor.execute(row)
                    finally: WRITE_GUARD.reset(context)
                    # Never persist email bodies or event descriptions in execution history.
                    safe_result={"available":True} if row["tool"] in ("EmailRead","EmailSearch","CalendarRead","CalendarList") else result
                    status="waiting" if row["tool"] in ("WorkflowCreate","WaitForReply") else "completed"
                    with self.store.db(True) as db:
                        if row["repeat"]!="once":
                            due=next_occurrence(row["due"],row["repeat"],row["timezone"],self.store.clock()); status="queued"
                            db.execute("UPDATE automation_jobs SET due=? WHERE id=?",(due,row["id"]))
                        db.execute("UPDATE automation_jobs SET status=?,result=?,updated=? WHERE id=?",(status,encode(safe_result),self.store.clock(),row["id"]))
                        self.store.event(db,"completed",row["id"],row["device_id"])
                except asyncio.CancelledError: raise
                except Exception:
                    with self.store.db(True) as db:
                        external=row["tool"] in ("EmailDraft","EmailSend","CalendarCreate","CalendarUpdate","CalendarDelete")
                        retry=not external and row["tool"] in ("CalendarRead","EmailSearch","EmailRead","EmailCheck","CalendarSummary") and row["attempts"]<5
                        db.execute("UPDATE automation_jobs SET status=?,result=?,attempts=attempts+1,due=? WHERE id=?",("uncertain" if external else "queued" if retry else "failed",encode({"error":"Uitvoering niet bevestigd; controleer integratie of provider vóór een nieuwe actie."}),self.store.clock()+min(3600,30*2**row["attempts"]) if retry else row["due"],row["id"]))
                        self.store.event(db,"execution_unconfirmed",row["id"],row["device_id"])
            await self.followups.check()

    async def close(self):
        await self.scheduler.stop()
        await self.integrations.http.aclose()
