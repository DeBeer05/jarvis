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
    recurrence: list[str] = Field(default_factory=list, max_length=5)
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
    repeat: Literal["once", "daily", "weekly"] = "once"
    @model_validator(mode="after")
    def dates(self):
        aware(self.at); valid_zone(self.timezone)
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
    @model_validator(mode="after")
    def dates(self):
        aware(self.due)
        return self


class Empty(Input):
    pass


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


def aware(value):
    if value.tzinfo is None or value.utcoffset() is None: raise ValueError("Timezone required")
    return value


def validate(tool, payload):
    if tool not in REGISTRY: raise ValueError("Unknown tool")
    result = REGISTRY[tool][0].model_validate(payload)
    if tool.startswith("Calendar") and tool != "CalendarRead":
        if tool != "CalendarCreate" and (not result.event_id or not result.etag): raise ValueError("Event and etag required")
        if tool != "CalendarDelete" and not (result.start and result.end and result.summary): raise ValueError("Event details required")
    if tool == "WorkflowCreate":
        for step in result.steps:
            if set(step) != {"tool", "input"} or step["tool"] == "WorkflowCreate": raise ValueError("Invalid step")
            validate(step["tool"], step["input"])
    return result.model_dump(mode="json")


def next_occurrence(at, repeat, timezone, now):
    """Wall-clock recurrence. Skip nonexistent DST times; use first fold once."""
    zone = ZoneInfo(timezone)
    local = datetime.fromtimestamp(at, UTC).astimezone(zone).replace(tzinfo=None)
    step = timedelta(days=7 if repeat == "weekly" else 1)
    while True:
        local += step
        candidate = local.replace(tzinfo=zone, fold=0)
        if candidate.astimezone(UTC).astimezone(zone).replace(tzinfo=None) != local: continue
        if candidate.timestamp() > now: return candidate.timestamp()
