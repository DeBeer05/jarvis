"""Authenticated UI/API. Reading third-party content never invokes a tool."""
import asyncio
import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import Field, SecretStr

from server.api.routes import require_client_access
from server.automation.models import Input, REGISTRY, CalendarRead, CalendarChange, Identifier
from server.automation.engine import AUTOMATION_SCOPES, EmailPriorityClassifier, ManualMessagingProvider
from server.automation.store import fingerprint, encode
from server.security.gate import require_permission
from server.security.types import AuthError
from server.ai.policy import RequestPolicy, use_policy

async def rate(request:Request):
    principal=getattr(request.state,"principal",None)
    if principal:
        await asyncio.to_thread(request.app.state.security.store.rate,"automation:"+principal.device_id,60)


async def ai_preferences(request:Request):
    principal=getattr(request.state,"principal",None)
    document=await asyncio.to_thread(request.app.state.natural.settings.get,principal) if principal else None
    with use_policy(RequestPolicy.from_document(document) if document else None):yield


router=APIRouter(dependencies=[Depends(require_client_access),Depends(rate),Depends(ai_preferences)])
BASE="/api/v1/automation"
STATIC=Path(__file__).resolve().parents[1]/"static"


class Submit(Input):
    tool: str = Field(max_length=50)
    input: dict
    idempotency_key: UUID
    due: datetime | None = None
    repeat: Literal["once","daily","weekly"] = "once"
    timezone: str = Field(default="Europe/Amsterdam",max_length=80)


class Decision(Input):
    token: SecretStr = Field(min_length=32,max_length=128)
    approve: bool


class Control(Input):
    status: Literal["paused","queued","cancelled"]


class Grant(Input):
    device_id: UUID
    scopes: set[Literal["automation:read","automation:write","automation:approve","integrations:manage"]]


class OAuth(Input):
    features: set[Literal["calendar_read","calendar_write","gmail_read","gmail_compose"]]


class Rules(Input):
    calendar_buffer_minutes:int=Field(default=15,ge=0,le=240)
    disabled_tools:list[str]=Field(default_factory=list,max_length=30)
    important_senders:list[str]=Field(default_factory=list,max_length=50)
    urgent_terms:list[str]=Field(default_factory=lambda:["deadline vandaag","dringend","urgent"],max_length=50)


@router.put(BASE+"/rules",dependencies=[Depends(require_permission("admin:account"))])
async def rules(request:Request,body:Rules):
    if any(t not in REGISTRY for t in body.disabled_tools) or any(len(s)>254 for s in body.important_senders+body.urgent_terms): raise ValueError("Ongeldige regels")
    e=engine(request)
    e.store.set_preference("calendar_buffer_minutes",body.calendar_buffer_minutes)
    e.store.set_preference("disabled_tools",body.disabled_tools)
    e.store.set_preference("email_rules",{"important_senders":body.important_senders,"urgent_terms":body.urgent_terms})
    return {"saved":True,"sensitive_actions_require_approval":True}


class Policy(Input):
    quiet_start: int=Field(default=22,ge=0,le=23)
    quiet_end: int=Field(default=7,ge=0,le=23)
    max_hour: int=Field(default=10,ge=1,le=60)
    categories: set[Literal["urgent","appointments","important","news"]]=Field(default_factory=lambda:{"urgent","appointments","important","news"})
    timezone: str=Field(default="Europe/Amsterdam",max_length=80)


def engine(request): return request.app.state.automation


@router.get("/automations")
def page(): return FileResponse(STATIC/"automations.html")


@router.get(BASE)
async def dashboard(request:Request,offset:int=Query(default=0,ge=0,le=5000)):
    e=engine(request)
    with e.store.db() as db:
        notifications=[dict(x) for x in db.execute("SELECT * FROM automation_notifications WHERE at<=? ORDER BY at DESC LIMIT 50",(e.store.clock(),))]
        events=[dict(x) for x in db.execute("SELECT * FROM automation_events ORDER BY id DESC LIMIT 100")]
    from server.natural.presence import allowed_notification
    mode=request.app.state.natural.presence.snapshot(request.state.principal)['mode']
    notifications=[item for item in notifications if allowed_notification(mode,item['category'])]
    return {"items":[e.store.public(x) for x in e.store.items(offset)],"offset":offset,"next_offset":offset+20,"notifications":notifications,"history":events,"tools":list(REGISTRY),"notification_policy":e.store.preference("notifications",Policy().model_dump(mode="json")),"external_push_available":False,"scheduler_enabled":request.app.state.settings.automations_enabled}


@router.post(BASE+"/jobs")
async def submit(request:Request,body:Submit):
    e=engine(request)
    from server.automation.models import valid_zone
    valid_zone(body.timezone)
    if body.due is not None and body.due.tzinfo is None: raise ValueError("Tijdzone vereist")
    row=e.submit(request.state.principal.device_id,body.tool,body.input,str(body.idempotency_key),body.due.timestamp() if body.due else None,body.repeat,body.timezone)
    return e.store.public(row)


@router.post(BASE+"/jobs/{identifier}/control")
async def control(request:Request,identifier:UUID,body:Control):
    e=engine(request); e.control(str(identifier),body.status,request.state.principal.device_id)
    return e.store.public(e.store.get(str(identifier)))


@router.delete(BASE+"/jobs/{identifier}")
async def delete_job(request:Request,identifier:UUID):
    e=engine(request)
    with e.store.db(True) as db:
        row=db.execute("SELECT status,parent_id FROM automation_jobs WHERE id=?",(str(identifier),)).fetchone()
        if not row or row[0] not in ("completed","cancelled","denied","failed","paused"): raise ValueError("Annuleer eerst; onzekere acties blijven bewaard voor controle")
        if row[1]:
            parent=db.execute("SELECT status FROM automation_jobs WHERE id=?",(row[1],)).fetchone()
            if parent and parent[0] in ("waiting","queued","paused"):raise ValueError("Annuleer eerst de bovenliggende workflow")
        # Retain the idempotency tombstone so a replay cannot repeat an external effect.
        db.execute("UPDATE automation_jobs SET status='deleted',payload='{}',result=NULL,approval_hash=NULL WHERE id=?",(str(identifier),))
        e.store.event(db,"deleted",str(identifier),request.state.principal.device_id)
    return {"deleted":True}


@router.post(BASE+"/jobs/{identifier}/challenge")
async def challenge(request:Request,identifier:UUID):
    return engine(request).approvals.challenge(str(identifier),request.state.principal)


@router.post(BASE+"/jobs/{identifier}/decision")
async def decide(request:Request,identifier:UUID,body:Decision):
    return engine(request).approvals.decide(str(identifier),request.state.principal,body.token.get_secret_value(),body.approve)


@router.post(BASE+"/grants",dependencies=[Depends(require_permission("admin:devices"))])
async def grant(request:Request,body:Grant):
    e=engine(request); owner=request.state.principal
    with e.store.db(True) as db:
        device=db.execute("SELECT * FROM auth_devices WHERE id=? AND revoked_at IS NULL",(str(body.device_id),)).fetchone()
        if not device or str(body.device_id)==owner.device_id: raise ValueError("Kies een gekoppeld ander apparaat")
        for scope in AUTOMATION_SCOPES: db.execute("DELETE FROM auth_permissions WHERE device_id=? AND permission=?",(str(body.device_id),scope))
        for scope in body.scopes: db.execute("INSERT INTO auth_permissions VALUES (?,?)",(str(body.device_id),scope))
        e.store.event(db,"automation_grants_updated",device=str(body.device_id))
    return {"updated":True}


@router.put(BASE+"/notifications")
async def policy(request:Request,body:Policy):
    from server.automation.models import valid_zone
    valid_zone(body.timezone)
    engine(request).store.set_preference("notifications",body.model_dump(mode="json"))
    return {"saved":True}


@router.get(BASE+"/integrations")
async def integrations(request:Request): return engine(request).integrations.status()


@router.post(BASE+"/integrations/google")
async def oauth(request:Request,body:OAuth):
    return engine(request).integrations.begin(request.state.principal,sorted(body.features))


@router.delete(BASE+"/integrations/google")
async def disconnect(request:Request): return await engine(request).integrations.disconnect()


@router.get("/oauth/google/callback")
async def callback(request:Request):
    # Public callback, authorized only by one-use state + live initiating owner session.
    state=request.query_params.get("state",""); code=request.query_params.get("code","")
    if not 32<=len(state)<=128 or not 1<=len(code)<=4096: return HTMLResponse("Koppeling geweigerd of ongeldig. Start opnieuw in JARVIS.",status_code=400)
    try: await engine(request).integrations.callback(state,code)
    except Exception:
        # Do not log Google codes/tokens or remote error messages.
        engine(request).audit.record("oauth_failed")
        return HTMLResponse("Google-koppeling mislukt. Ga terug naar JARVIS en start opnieuw.",status_code=400)
    return HTMLResponse("Google is gekoppeld. Je kunt dit tabblad sluiten en teruggaan naar JARVIS.")


@router.get(BASE+"/calendar/calendars")
async def calendars(request:Request):
    engine(request).permissions.check_tool(request.state.principal.device_id,"CalendarList")
    return await engine(request).integrations.calendar_list()


@router.post(BASE+"/calendar/search")
async def calendar(request:Request,body:CalendarRead):
    engine(request).permissions.check_tool(request.state.principal.device_id,"CalendarRead")
    return await engine(request).integrations.events(body.model_dump(mode="json"))


@router.post(BASE+"/reschedule")
async def reschedule(request:Request,body:CalendarChange):
    e=engine(request)
    e.permissions.check_tool(request.state.principal.device_id,"CalendarRead")
    return await e.reschedule.analyze(body.model_dump(mode="json"),request.state.principal.device_id)


class MailQuery(Input):
    query:str=Field(default="in:inbox",max_length=500)


@router.post(BASE+"/email/search")
async def email_search(request:Request,body:MailQuery):
    engine(request).permissions.check_tool(request.state.principal.device_id,"EmailSearch")
    return await engine(request).integrations.mail_search(body.query)


@router.get(BASE+"/email/{identifier}")
async def email_read(request:Request,identifier:str,include_body:bool=False):
    engine(request).permissions.check_tool(request.state.principal.device_id,"EmailRead")
    from server.automation.models import EmailRead
    p=EmailRead(message_id=identifier,include_body=include_body)
    return await engine(request).integrations.mail_read(p.message_id,p.include_body)


class Summary(Input):
    text:str=Field(min_length=1,max_length=12000)


@router.post(BASE+"/summarize")
async def summarize(request:Request,body:Summary):
    # Model has no executor reference. Received content cannot call tools.
    return {"summary":await request.app.state.chat.router.summarize_untrusted(body.text)}


class Plan(Input):
    instruction:str=Field(min_length=1,max_length=2000)


@router.post(BASE+"/plan")
async def plan(request:Request,body:Plan):
    return await request.app.state.chat.router.propose_tool(body.instruction)


class Priority(Input):
    sender:str=Field(default="",max_length=254)
    subject:str=Field(default="",max_length=500)
    text:str=Field(default="",max_length=12000)


@router.post(BASE+"/email-priority")
async def priority(request:Request,body:Priority):
    e=engine(request)
    return EmailPriorityClassifier().classify(body.sender,body.subject,body.text,e.store.preference("email_rules",{}))


class ManualMessage(Input):
    recipient:str=Field(min_length=1,max_length=254)
    text:str=Field(min_length=1,max_length=4000)


@router.post(BASE+"/manual-message")
async def manual(request:Request,body:ManualMessage): return await ManualMessagingProvider().prepare(body.recipient,body.text)


class FollowUp(Input):
    thread_id:str=Field(pattern=r"^[a-zA-Z0-9_-]{1,256}$")
    due:datetime


@router.post(BASE+"/followups")
async def followup(request:Request,body:FollowUp):
    e=engine(request)
    e.permissions.check_tool(request.state.principal.device_id,"WaitForReply")
    if body.due.tzinfo is None or body.due.timestamp()<=e.store.clock(): raise ValueError("Kies een toekomstig tijdstip met tijdzone")
    data=await e.integrations.api("gmail_read","/gmail/v1/users/me/threads/"+body.thread_id,params={"format":"metadata"})
    from uuid import uuid4
    identifier=str(uuid4())
    with e.store.db(True) as db:
        db.execute("INSERT INTO automation_followups VALUES (?,?,?,?,?,?)",(identifier,body.thread_id,encode([m["id"] for m in data.get("messages",[])]),body.due.timestamp(),"waiting",request.state.principal.device_id))
    return {"id":identifier,"status":"waiting"}
