"""Closed tool registry: external content is data, never an executable plan."""
from datetime import datetime, UTC, timedelta
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


def valid_zone(value):
    try:ZoneInfo(value)
    except (ZoneInfoNotFoundError,ValueError):raise ValueError("Unknown timezone") from None
    return value


class CalendarRead(Input):
    calendar_id: str = Field(default="primary", max_length=256)
    start: datetime
    end: datetime
    query: str = Field(default="", max_length=200)
    @model_validator(mode="after")
    def interval(self):
        aware(self.start); aware(self.end)
        if not timedelta(0) < self.end-self.start <= timedelta(days=366):
            raise ValueError("Invalid interval")
        return self


class CalendarChange(Input):
    calendar_id: str = Field(default="primary", max_length=256)
    event_id: str = Field(default="", max_length=512)
    summary: str = Field(default="", max_length=500)
    start: datetime | None = None
    end: datetime | None = None
    timezone: str = Field(default="Europe/Amsterdam", max_length=80)
    attendees: list[str] = Field(default_factory=list, max_length=50)
    location: str = Field(default="", max_length=500)
    description: str | None = Field(default=None,max_length=8000)
    recurrence: list[str] = Field(default_factory=list, max_length=5)
    reminder_minutes: int | None = Field(default=None, ge=0, le=40320, strict=True)
    etag: str = Field(default="", max_length=256)
    @model_validator(mode="after")
    def dates(self):
        valid_zone(self.timezone)
        if self.start is not None: aware(self.start)
        if self.end is not None: aware(self.end)
        if self.start and self.end and self.end <= self.start: raise ValueError("Invalid interval")
        if any("\r" in x or "\n" in x or "@" not in x for x in self.attendees): raise ValueError("Invalid recipient")
        return self


class EmailSearch(Input):
    query: str = Field(default="in:inbox", max_length=500)


class EmailRead(Input):
    message_id: str = Field(min_length=1, max_length=256, pattern=r"^[a-zA-Z0-9_-]+$")
    include_body: bool = False


class EmailDraft(Input):
    to: str = Field(min_length=3, max_length=254)
    subject: str = Field(max_length=500)
    text: str = Field(min_length=1, max_length=12000)
    thread_id: str = Field(default="", max_length=256, pattern=r"^[a-zA-Z0-9_-]*$")
    @model_validator(mode="after")
    def headers(self):
        if any(c in self.to+self.subject for c in "\r\n") or "@" not in self.to: raise ValueError("Invalid mail header")
        return self


class EmailSend(Input):
    draft_id: str = Field(min_length=1, max_length=256, pattern=r"^[a-zA-Z0-9_-]+$")
    # Approval binds to this immutable snapshot; draft is fetched again before send.
    message_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    preview: str = Field(min_length=1, max_length=20000)


class ReminderCreate(Input):
    text: str = Field(min_length=1, max_length=500)
    at: datetime
    timezone: str = Field(default="Europe/Amsterdam", max_length=80)
    repeat: Literal["once", "daily", "weekly", "monthly", "yearly"] = "once"
    source_id:str|None=Field(default=None,pattern=r'^[0-9a-f-]{36}$')
    source_revision:int|None=Field(default=None,ge=1)
    @model_validator(mode="after")
    def dates(self):
        aware(self.at); valid_zone(self.timezone)
        if (self.source_id is None)!=(self.source_revision is None):raise ValueError('Bron en revisie horen bij elkaar')
        return self


class Identifier(Input):
    id: str = Field(min_length=1, max_length=64)


class CalendarSummary(Input):
    calendar_id: str = Field(default="primary",max_length=256)
    timezone: str = Field(default="Europe/Amsterdam",max_length=80)
    day_offset: int = Field(default=0,ge=0,le=7)
    @model_validator(mode="after")
    def zone(self):
        valid_zone(self.timezone)
        return self


class WaitForReply(Input):
    thread_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,256}$")
    due: datetime
    since: datetime | None = None
    source_id:str|None=Field(default=None,pattern=r'^[0-9a-f-]{36}$')
    source_revision:int|None=Field(default=None,ge=1)
    @model_validator(mode="after")
    def dates(self):
        aware(self.due)
        if (self.source_id is None)!=(self.source_revision is None):raise ValueError('Bron en revisie horen bij elkaar')
        if self.since is not None:
            aware(self.since)
            if self.since>self.due:raise ValueError("Opvolging moet na het oorspronkelijke bericht vallen")
        return self


class Empty(Input):
    pass


class PersonalBriefing(Input):
    kind:Literal['morning','evening','return','prepare']='morning'
    config_hash:str=Field(pattern=r'^[0-9a-f]{64}$')
    source_event:str|None=Field(default=None,pattern=r'^[0-9a-f-]{36}$')


class DesktopRead(Input):
    kind:Literal['status','files','downloads']='status'
    query:str=Field(default='',max_length=80)


class HomeRead(Input):
    entity_id:str=Field(pattern=r'^(?:light|switch|climate|sensor|binary_sensor|scene|automation)\.[a-z0-9_]{1,100}$')


class HomeControl(HomeRead):
    action:Literal['on','off','temperature','scene','routine']
    temperature:float|None=Field(default=None,ge=5,le=30,allow_inf_nan=False)
    brightness:int|None=Field(default=None,ge=0,le=255)
    policy_hash:str=Field(default='',pattern=r'^(?:[0-9a-f]{64})?$')
    @model_validator(mode='after')
    def fields(self):
        if (self.action=='temperature')!=(self.temperature is not None):raise ValueError('Temperatuur hoort alleen bij een thermostaatopdracht')
        if self.brightness is not None and self.action!='on':raise ValueError('Helderheid hoort alleen bij licht aan')
        return self


class RouteRead(Input):
    coordinates:list[tuple[float,float]]=Field(min_length=2,max_length=10)
    @model_validator(mode='after')
    def points(self):
        import math
        if any(not math.isfinite(lon) or not math.isfinite(lat) or not -180<=lon<=180 or not -90<=lat<=90 for lon,lat in self.coordinates):raise ValueError('Ongeldige coördinaten')
        return self


class MobileHandoff(Input):
    target_device:str=Field(pattern=r'^[0-9a-f-]{36}$')
    action:Literal['dial','sms','email','whatsapp','signal','navigate']
    target:str=Field(default='',max_length=300)
    text:str=Field(default='',max_length=1800)
    subject:str=Field(default='',max_length=120)
    @model_validator(mode='after')
    def fields(self):
        import re
        if self.action in ('dial','sms','whatsapp') and not re.fullmatch(r'\+?[0-9]{6,15}',self.target):raise ValueError('Gebruik een volledig telefoonnummer')
        if self.action=='email' and (not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+',self.target) or any(ch in self.subject for ch in '\r\n')):raise ValueError('Ongeldig mailadres of onderwerp')
        if self.action=='navigate' and not self.target.strip():raise ValueError('Geef een bestemming')
        if self.action=='signal' and self.target:raise ValueError('Kies de ontvanger in Signal zelf')
        if self.action in ('dial','navigate') and (self.text or self.subject):raise ValueError('Ongebruikte actiegegevens')
        if self.action!='email' and self.subject:raise ValueError('Alleen e-mail heeft een onderwerp')
        return self


class DesktopControl(Input):
    action:Literal['open_program','close_program','open_file','volume_up','volume_down','mute','play','pause','play_pause','next','previous','lock','sleep','shutdown','restart','cancel_shutdown']
    program:str=Field(default='',max_length=50)
    path:str=Field(default='',max_length=400)
    policy_hash:str=Field(default='',pattern=r'^(?:[0-9a-f]{64})?$')
    @model_validator(mode='after')
    def fields(self):
        if self.action in ('open_program','close_program'):
            if not self.program or self.path:raise ValueError('Kies één toegestaan programma')
        elif self.action=='open_file':
            if not self.path or self.program:raise ValueError('Kies één toegestaan document')
        elif self.path or self.program:raise ValueError('Ongebruikte actiegegevens')
        return self


class NotificationSend(Input):
    category: Literal["urgent", "appointments", "important", "news"] = "important"
    text: str = Field(min_length=1, max_length=500)


class UrgentEvent(Input):
    model_config=ConfigDict(extra="forbid",frozen=True)
    event_id:str
    category:Literal["urgent"]="urgent"
    created_at:float
    reason:str=Field(min_length=1,max_length=500)
    job_id:str
    call_started:Literal[False]=False


class WorkflowCreate(Input):
    title: str = Field(min_length=1, max_length=200)
    # All steps are validated separately. No nested workflow or recursion.
    steps: list[dict] = Field(min_length=1, max_length=10)


REGISTRY = {
    'DesktopRead':(DesktopRead,False),'DesktopControl':(DesktopControl,True),
    'MobileHandoff':(MobileHandoff,True),
    'HomeRead':(HomeRead,False),'HomeControl':(HomeControl,True),'RouteRead':(RouteRead,False),
    "PersonalBriefing": (PersonalBriefing,False),
    "CalendarList": (Empty, False),
    "CalendarSummary": (CalendarSummary, False), "EmailCheck": (EmailSearch, False),
    "WaitForReply": (WaitForReply, False),
    "CalendarRead": (CalendarRead, False), "CalendarCreate": (CalendarChange, True),
    "CalendarUpdate": (CalendarChange, True), "CalendarDelete": (CalendarChange, True),
    "EmailSearch": (EmailSearch, False), "EmailRead": (EmailRead, False),
    "EmailDraft": (EmailDraft, False), "EmailSend": (EmailSend, True),
    "ReminderCreate": (ReminderCreate, False), "ReminderList": (Empty, False),
    "ReminderCancel": (Identifier, False), "NotificationSend": (NotificationSend, False),
    "WorkflowCreate": (WorkflowCreate, False), "WorkflowStatus": (Identifier, False),
}

SIDE_EFFECT_TOOLS=frozenset({'CalendarCreate','CalendarUpdate','CalendarDelete','EmailDraft','EmailSend','DesktopControl','MobileHandoff','HomeControl'})


def aware(value):
    if value.tzinfo is None or value.utcoffset() is None: raise ValueError("Timezone required")
    return value


def validate(tool, payload):
    if tool not in REGISTRY: raise ValueError("Unknown tool")
    result = REGISTRY[tool][0].model_validate(payload)
    if tool in ("CalendarCreate", "CalendarUpdate", "CalendarDelete"):
        if tool != "CalendarCreate" and (not result.event_id or not result.etag): raise ValueError("Event and etag required")
        if tool != "CalendarDelete" and not (result.start and result.end and result.summary): raise ValueError("Event details required")
    if tool == "WorkflowCreate":
        for step in result.steps:
            if set(step) != {"tool", "input"} or step["tool"] == "WorkflowCreate": raise ValueError("Invalid step")
            validate(step["tool"], step["input"])
    data=result.model_dump(mode="json")
    if tool in ('ReminderCreate','WaitForReply') and data.get('source_id') is None:
        data.pop('source_id',None);data.pop('source_revision',None)
    return data


def next_occurrence(at, repeat, timezone, now):
    """Wall-clock recurrence. Skip nonexistent DST times; use first fold once."""
    zone = ZoneInfo(timezone)
    local = datetime.fromtimestamp(at, UTC).astimezone(zone).replace(tzinfo=None)
    current=datetime.fromtimestamp(now,UTC).astimezone(zone).replace(tzinfo=None)
    if repeat in ('daily','weekly'):
        days=7 if repeat=='weekly' else 1
        jump=max(1,(current.date()-local.date()).days//days)
    elif repeat=='monthly':jump=max(1,(current.year-local.year)*12+current.month-local.month)
    elif repeat=='yearly':jump=max(1,current.year-local.year)
    else:raise ValueError('Onbekende herhaling')
    for _ in range(400):
        try:
            if repeat in ('daily','weekly'):following=local+timedelta(days=jump*days)
            elif repeat=='monthly':
                year,month=divmod(local.year*12+local.month-1+jump,12)
                following=local.replace(year=year,month=month+1)
            else:following=local.replace(year=local.year+jump)
        except ValueError:jump+=1;continue
        jump+=1
        candidate = following.replace(tzinfo=zone, fold=0)
        if candidate.astimezone(UTC).astimezone(zone).replace(tzinfo=None) != following: continue
        if candidate.timestamp() > now: return candidate.timestamp()
    raise ValueError('Geen geldige volgende herhaling gevonden')
