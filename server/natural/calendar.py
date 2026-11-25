"""Validate spoken calendar slots against user text before a proposal is created."""
import re
from datetime import date,datetime,timedelta,UTC
from zoneinfo import ZoneInfo

from server.natural.temporal import resolve,local_time,AmbiguousTime,NUMBER,number


def create_parameters(payload,instruction,config=None):
    config=config or {};calendar=config.get("calendar",{})
    timezone=config.get("general",{}).get("timezone","Europe/Amsterdam");zone=ZoneInfo(timezone)
    def hour(value):
        h,m=map(int,value.split(":"));return h+m/60
    start_day=start_clock=duration=end_clock=None;reminder=None;explicit_reminder=False
    for utterance in instruction.split("\nAanvullende gegevens van dezelfde gebruiker: "):
        previous_clock=start_clock
        if end_clock and start_clock and duration is None:
            begin_h,begin_m=map(int,start_clock.split(":"));end_h,end_m=map(int,end_clock.split(":"))
            duration=(end_h*60+end_m-begin_h*60-begin_m)%(24*60)
        # Reminder offsets are not the appointment's clock or duration.
        parts=re.split(r"\b(?:herinner\w*\s+(?:me|mij)|herinnering)\b",utterance,maxsplit=1,flags=re.I)
        text=parts[0].strip()
        if len(parts)>1:
            explicit_reminder=True
            match=re.search(r"\b("+NUMBER+r")\s*(minuten?|uur|uren|dag|dagen|week|weken)\s+(?:van\s+)?(?:tevoren|vooraf|ervoor)\b",parts[1],re.I)
            if not match:raise AmbiguousTime("Hoeveel minuten, uren of dagen vóór de afspraak wil je worden herinnerd?")
            reminder=number(match[1].casefold())*({"uur":60,"uren":60,"dag":1440,"dagen":1440,"week":10080,"weken":10080}.get(match[2].casefold(),1))
            if not 0<=reminder<=40320:raise AmbiguousTime("Kies een herinnering tussen nul minuten en vier weken vóór de afspraak.")
        if re.match(r"\s*(?:"+NUMBER+r"|anderhalf|een half)\s+(?:uur|uren|minuten?)\b",text,re.I):text="duur "+text
        hint=resolve(text,timezone=timezone,work_start=hour(calendar.get("work_start","09:00")),work_end=hour(calendar.get("work_end","17:00")))
        if hint.clarification:raise AmbiguousTime(hint.clarification)
        if hint.date:start_day=hint.date
        if hint.clock:start_clock=hint.clock
        if hint.duration_minutes is not None:duration=hint.duration_minutes
        ending=re.search(r"\btot\s+((?:kwart\s+(?:voor|over)|half)\s+"+NUMBER+r"|"+NUMBER+r"(?::[0-5]\d)?)(?:\s+uur)?\b",text,re.I)
        if ending:
            end_hint=resolve("om "+ending[1],timezone=timezone,work_start=hour(calendar.get("work_start","09:00")),work_end=hour(calendar.get("work_end","17:00")))
            if end_hint.clarification:raise AmbiguousTime(end_hint.clarification)
            end_clock=end_hint.clock
        # A corrected duration supersedes a previously supplied end time.
        elif hint.duration_minutes is not None or hint.clock and hint.clock!=previous_clock:end_clock=None
    if not start_day or not start_clock:
        question="Voor welke datum en van hoe laat tot hoe laat wil je de afspraak?" if not start_day and not start_clock else "Op welke datum wil je de afspraak?" if not start_day else "Hoe laat begint de afspraak?"
        raise AmbiguousTime(question+" Ik heb nog geen afspraak ingepland.")
    start_hour,start_minute=map(int,start_clock.split(":"))
    start=local_time(date.fromisoformat(start_day),start_hour,start_minute,zone)
    if end_clock:
        end_hour,end_minute=map(int,end_clock.split(":"))
        end=local_time(start.date(),end_hour,end_minute,zone)
        if end<=start:end=local_time(start.date()+timedelta(days=1),end_hour,end_minute,zone)
        if duration is not None and (end.astimezone(UTC)-start.astimezone(UTC)).total_seconds()!=duration*60:
            raise AmbiguousTime("Je eindtijd en duur verschillen. Welke eindtijd of duur wil je gebruiken?")
    else:
        if duration is None:
            if not calendar.get("use_defaults",True):raise AmbiguousTime("Hoe lang duurt de afspraak?")
            duration=calendar.get("duration_minutes",60)
        if not 1<=duration<=1440:raise AmbiguousTime("Hoe lang duurt de afspraak, maximaal één dag?")
        end=(start.astimezone(UTC)+timedelta(minutes=duration)).astimezone(zone)
    result={**payload,"start":start.isoformat(),"end":end.isoformat(),"timezone":timezone}
    invitation=bool(re.search(r"\b(?:uitnodig\w*|genodigd\w*|invite)\b|\bnodig\b.*\buit\b",instruction,re.I))
    attendees=payload.get("attendees",[])
    if any(not isinstance(address,str) or address.casefold() not in instruction.casefold() for address in attendees):
        if invitation:raise AmbiguousTime("Wat is het e-mailadres van de persoon die je wilt uitnodigen?")
        attendees=[]
    if invitation and not attendees:raise AmbiguousTime("Wat is het e-mailadres van de persoon die je wilt uitnodigen?")
    result["attendees"]=attendees
    if not result.get("calendar_id") or result["calendar_id"]=="primary":result["calendar_id"]=calendar.get("default_calendar","primary")
    if explicit_reminder:result["reminder_minutes"]=reminder
    elif calendar.get("use_defaults",True):result["reminder_minutes"]=calendar.get("reminder_minutes",30)
    else:result["reminder_minutes"]=None
    return result


def update_parameters(payload,instruction,event,config=None):
    """Use a verified event as the anchor, never a model-invented old time."""
    timezone=(config or {}).get("general",{}).get("timezone","Europe/Amsterdam");zone=ZoneInfo(timezone)
    try:
        start=datetime.fromisoformat(event["start"]["dateTime"]).astimezone(zone)
        end=datetime.fromisoformat(event["end"]["dateTime"]).astimezone(zone)
    except (KeyError,ValueError,TypeError):raise AmbiguousTime("Welke afspraak met een concrete begin- en eindtijd wil je wijzigen?") from None
    target=re.split(r"\bnaar\b",instruction,flags=re.I)[-1]
    hint=resolve(target,timezone=timezone,anchor=start)
    if hint.clarification:raise AmbiguousTime(hint.clarification)
    if not any((hint.start,hint.date,hint.clock,hint.duration_minutes)):
        return {**payload,"start":start.isoformat(),"end":end.isoformat(),"timezone":timezone}
    duration=round((end.astimezone(UTC)-start.astimezone(UTC)).total_seconds()/60)
    if not 1<=duration<=1440:raise AmbiguousTime("Deze afspraak duurt langer dan één dag. Controleer de wijziging in Google Calendar.")
    baseline=f"Maak op {start:%Y-%m-%d} om {start:%H:%M} een afspraak van {duration} minuten"
    # Relative corrections already resolve to an exact instant against the event.
    if hint.start and hint.clock and not hint.window_end:target=f"op {hint.start:%Y-%m-%d} om {hint.start:%H:%M}"+(f" van {hint.duration_minutes} minuten" if hint.duration_minutes else "")
    elif hint.clock and "dezelfde tijd als vorige keer" in target.casefold():target="om "+hint.clock
    result=create_parameters(payload,baseline+"\nAanvullende gegevens van dezelfde gebruiker: "+target,config)
    result["attendees"]=payload.get("attendees",[])
    if not re.search(r"\b(?:herinner\w*|herinnering)\b",instruction,re.I):result["reminder_minutes"]=payload.get("reminder_minutes")
    return result
