"""Validate spoken calendar slots against user text before a proposal is created."""
import re
from datetime import date,datetime,timedelta,UTC
from zoneinfo import ZoneInfo

from server.natural.temporal import resolve,local_time,AmbiguousTime,NUMBER,number,normalize_dayparts,daypart

TITLE_PREFIX=r'\b(?:genaamd|getiteld|titel(?:\s+is)?|(?:die|dat)\s+heet)\s*[:,]?\s+'


def timing_text(text,summary=''):
    text=re.sub(r'"[^"\n]*"|“[^”\n]*”|\b(?:die|dat)\s+(?!(?:je|u|jij)\b).+?\s+heet\b','',text,flags=re.I)
    if summary:text=re.sub(TITLE_PREFIX+re.escape(summary),'',text,flags=re.I)
    return text


def outing_title(instruction):
    """Literal title for simple personal outings; invitation/complex flows keep the planner."""
    text=instruction.split("\nAanvullende gegevens van dezelfde gebruiker: ")[0]
    # Only an unqualified own/default-calendar suffix can use this path.
    # A named calendar remains a planner lookup, never silently primary.
    text=re.sub(r"\s+(?:in|op)\s+(?:mijn|de)\s+(?:hoofd)?agenda(?:\s+(?:zet|zetten|toevoegen|toe))?[.!?\s]*$","",text,flags=re.I)
    if re.search(r"uitnodig|\bnodig\b|\b(?:agenda|kalender|calendar|locatie|adres|beschrijving|titel|genaamd|herhaal|wekelijks|dagelijks)\b|\b(?:en|of)\s+(?:maak|plan|stuur|verzet)\b",text,re.I):return None
    match=re.search(r"\buitje\b(.*?)(?=\s+(?:toevoegen|inplannen|plannen|toe|voor|op|morgen|overmorgen|vandaag|om|van|tussen)\b|[.!?]|$)",text,re.I)
    if not match:return None
    title="Uitje"+match[1].rstrip()
    return title if len(title)<=180 else None


def create_parameters(payload,instruction,config=None,*,now=None,default_duration=None):
    config=config or {};calendar=config.get("calendar",{})
    timezone=config.get("general",{}).get("timezone","Europe/Amsterdam");zone=ZoneInfo(timezone)
    def hour(value):
        h,m=map(int,value.split(":"));return h+m/60
    start_day=start_clock=duration=end_clock=None;reminder=None;explicit_reminder=False
    utterances:list[str]=[]
    for utterance in instruction.split("\nAanvullende gegevens van dezelfde gebruiker: "):
        utterance=normalize_dayparts(timing_text(utterance,payload.get('summary','')))
        # Apply a bound daypart reply before replaying an ambiguous clock.
        if utterances and re.fullmatch(r"\s*(?:(?:nee|toch|maar|in|de|['’]?s)\W+)*(?:middag|ochtend|avond|nacht)s?[.!?\s]*",utterance,re.I):
            utterances[-1]+=" "+utterance
        else:utterances.append(utterance)
    for utterance in utterances:
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
        start_text=re.split(r"\btot\b",text,maxsplit=1,flags=re.I)[0]
        if len(start_text)<len(text):
            start_text=re.sub(r"\bvan(?=\s+"+NUMBER+r"\s+uur\b)","vanaf",start_text,flags=re.I)
        # A shared trailing daypart applies to both clocks unless the start
        # already states a different daypart (09:00 morning to 17:00 afternoon).
        if not daypart(start_text) and daypart(text):start_text+=" "+daypart(text)
        hint=resolve(start_text,now=now,timezone=timezone,work_start=hour(calendar.get("work_start","09:00")),work_end=hour(calendar.get("work_end","17:00")))
        if hint.clarification:raise AmbiguousTime(hint.clarification)
        if hint.date:start_day=hint.date
        if hint.clock:start_clock=hint.clock
        if hint.duration_minutes is not None:duration=hint.duration_minutes
        ending=re.search(r"\btot\s+((?:kwart\s+(?:voor|over)|half)\s+"+NUMBER+r"|"+NUMBER+r"(?::[0-5]\d)?)(?:\s+uur)?\b",text,re.I)
        if ending:
            end_text="om "+ending[1]+" "+text[ending.end():]
            if not daypart(end_text) and daypart(start_text):end_text+=" "+daypart(start_text)
            end_hint=resolve(end_text,now=now,timezone=timezone,work_start=hour(calendar.get("work_start","09:00")),work_end=hour(calendar.get("work_end","17:00")))
            if end_hint.clarification:raise AmbiguousTime(end_hint.clarification)
            end_clock=end_hint.clock
            if end_hint.duration_minutes is not None:duration=end_hint.duration_minutes
        # A corrected duration supersedes a previously supplied end time.
        elif hint.duration_minutes is not None or hint.clock and hint.clock!=previous_clock:end_clock=None
    if not start_day or not start_clock:
        question="Op welke datum en hoe laat begint de afspraak?" if not start_day and not start_clock else "Op welke datum wil je de afspraak?" if not start_day else "Hoe laat begint de afspraak?"
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
            if default_duration is not None:duration=default_duration
            elif not calendar.get("use_defaults",True):raise AmbiguousTime("Hoe lang duurt de afspraak?")
            else:duration=calendar.get("duration_minutes",60)
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


def update_parameters(payload,instruction,event,config=None,*,now=None):
    """Use a verified event as the anchor, never a model-invented old time."""
    timezone=(config or {}).get("general",{}).get("timezone","Europe/Amsterdam");zone=ZoneInfo(timezone)
    try:
        start=datetime.fromisoformat(event["start"]["dateTime"]).astimezone(zone)
        end=datetime.fromisoformat(event["end"]["dateTime"]).astimezone(zone)
    except (KeyError,ValueError,TypeError):raise AmbiguousTime("Welke afspraak met een concrete begin- en eindtijd wil je wijzigen?") from None
    target=re.split(r"\bnaar\b",instruction,flags=re.I)[-1]
    hint=resolve(target,now=now,timezone=timezone,anchor=start)
    if hint.clarification:raise AmbiguousTime(hint.clarification)
    if not any((hint.start,hint.date,hint.clock,hint.duration_minutes)):
        return {**payload,"start":start.isoformat(),"end":end.isoformat(),"timezone":timezone}
    duration=round((end.astimezone(UTC)-start.astimezone(UTC)).total_seconds()/60)
    if not 1<=duration<=1440:raise AmbiguousTime("Deze afspraak duurt langer dan één dag. Controleer de wijziging in Google Calendar.")
    baseline=f"Maak op {start:%Y-%m-%d} om {start:%H:%M} een afspraak van {duration} minuten"
    # Relative corrections already resolve to an exact instant against the event.
    if hint.start and hint.clock and not hint.window_end:target=f"op {hint.start:%Y-%m-%d} om {hint.start:%H:%M}"+(f" van {hint.duration_minutes} minuten" if hint.duration_minutes else "")
    elif hint.clock and "dezelfde tijd als vorige keer" in target.casefold():target="om "+hint.clock
    result=create_parameters(payload,baseline+"\nAanvullende gegevens van dezelfde gebruiker: "+target,config,now=now)
    result["attendees"]=payload.get("attendees",[])
    if not re.search(r"\b(?:herinner\w*|herinnering)\b",instruction,re.I):result["reminder_minutes"]=payload.get("reminder_minutes")
    return result
