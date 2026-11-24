"""Deterministic Dutch time hints, with explicit uncertainty and DST validation."""
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, time, UTC
from zoneinfo import ZoneInfo

NUMBERS={word:index for index,word in enumerate(("nul","een","twee","drie","vier","vijf","zes","zeven","acht","negen","tien","elf","twaalf","dertien","veertien","vijftien","zestien","zeventien","achttien","negentien","twintig","eenentwintig","tweeentwintig","drieentwintig"))}
WEEKDAYS=("maandag","dinsdag","woensdag","donderdag","vrijdag","zaterdag","zondag")
NUMBER=r"(?:\d{1,3}|"+"|".join(sorted(NUMBERS,key=len,reverse=True))+r")"


class AmbiguousTime(ValueError):
    """Ask a focused question rather than sending guessed parameters to a tool."""


@dataclass(frozen=True)
class TimeHint:
    start: datetime|None=None
    date: str|None=None
    clock: str|None=None
    window_end: datetime|None=None
    duration_minutes: int|None=None
    clarification: str|None=None


def number(value):
    return int(value) if value.isdecimal() else NUMBERS[value]


def local_time(day,hour,minute,zone):
    naive=datetime.combine(day,time(hour,minute))
    candidates:list[datetime]=[]
    for fold in (0,1):
        candidate=naive.replace(tzinfo=zone,fold=fold)
        if candidate.astimezone(UTC).astimezone(zone).replace(tzinfo=None)==naive:
            if not any(candidate.utcoffset()==old.utcoffset() for old in candidates):candidates.append(candidate)
    if not candidates:raise AmbiguousTime("Dit tijdstip bestaat niet door de overgang naar zomertijd. Welk ander tijdstip wil je?")
    if len(candidates)>1:raise AmbiguousTime("Dit tijdstip komt twee keer voor bij de overgang naar wintertijd. Bedoel je de eerste of de tweede keer?")
    return candidates[0]


def resolve(text,*,now=None,timezone="Europe/Amsterdam",anchor=None,work_start=9,work_end=17):
    """Return only unambiguous explicit hints. Unmentioned slots remain None."""
    zone=ZoneInfo(timezone);now=(now or datetime.now(zone)).astimezone(zone)
    message=text.casefold().replace("één","een").replace("tweeën","tweeen")
    duration=None
    duration_match=re.search(r"\b(?:van|duurt|duur|ongeveer)\s+(anderhalf|een half|"+NUMBER+r")\s*(uur|uren|minuten?|min)\b",message)
    if duration_match:
        amount=1.5 if duration_match[1]=="anderhalf" else .5 if duration_match[1]=="een half" else number(duration_match[1])
        duration=int(amount*(60 if duration_match[2].startswith("u") else 1))
        if not 1<=duration<=1440:raise AmbiguousTime("Hoe lang moet de afspraak duren? Kies een duur tussen één minuut en één dag.")
    relative=re.search(r"\b(?:over|binnen)\s+(anderhalf|een half|"+NUMBER+r")\s*(uur|uren|minuten?|min|dagen?)\b",message)
    if relative:
        amount=1.5 if relative[1]=="anderhalf" else .5 if relative[1]=="een half" else number(relative[1])
        seconds=amount*(3600 if relative[2].startswith("u") else 86400 if relative[2].startswith("dag") else 60)
        at=(now.astimezone(UTC)+timedelta(seconds=seconds)).astimezone(zone)
        return TimeHint(at,at.date().isoformat(),at.strftime("%H:%M"),duration_minutes=duration)
    shift=re.search(r"\b(een halfuur|een uur|"+NUMBER+r"\s+minuten?)\s+(later|eerder)\b",message)
    if shift:
        if anchor is None:return TimeHint(duration_minutes=duration,clarification="Ten opzichte van welke afspraak of welk tijdstip?")
        minutes=30 if shift[1]=="een halfuur" else 60 if shift[1]=="een uur" else number(shift[1].split()[0])
        at=(anchor.astimezone(UTC)+timedelta(minutes=minutes*(1 if shift[2]=="later" else -1))).astimezone(zone)
        return TimeHint(at,at.date().isoformat(),at.strftime("%H:%M"),duration_minutes=duration)
    if re.search(r"\bdezelfde tijd als vorige keer\b",message):
        return TimeHint(clock=anchor.astimezone(zone).strftime("%H:%M") if anchor else None,duration_minutes=duration,clarification=None if anchor else "Welke eerdere afspraak bedoel je?")
    day=None
    iso=re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b",message)
    months=("januari","februari","maart","april","mei","juni","juli","augustus","september","oktober","november","december")
    absolute=re.search(r"\b(\d{1,2})\s+("+"|".join(months)+r")(?:\s+(\d{4}))?\b",message)
    try:
        if iso:day=date(*map(int,iso.groups()))
        elif absolute:
            day=date(int(absolute[3] or now.year),months.index(absolute[2])+1,int(absolute[1]))
            if not absolute[3] and day<now.date():day=day.replace(year=day.year+1)
    except ValueError:raise AmbiguousTime("Die datum bestaat niet. Welke datum bedoel je?") from None
    if re.search(r"\bovermorgen\b",message):day=now.date()+timedelta(days=2)
    elif re.search(r"\bmorgen(?:ochtend|middag|avond)?\b",message):day=now.date()+timedelta(days=1)
    elif re.search(r"\b(?:vandaag|vanavond|vanochtend|vanmiddag)\b",message):day=now.date()
    weekday=re.search(r"\b(?:(volgende week|volgende|aanstaande|komende|deze)\s+)?("+"|".join(WEEKDAYS)+r")\b",message)
    if weekday:
        target=WEEKDAYS.index(weekday[2]);modifier=weekday[1]
        offset=(target-now.weekday())%7
        if modifier in ("volgende week","volgende"):offset=7-now.weekday()+target
        day=now.date()+timedelta(days=offset)
    if day is None and re.search(r"\bvolgende week\b",message):
        start=now.date()+timedelta(days=7-now.weekday())
        return TimeHint(local_time(start,0,0,zone),window_end=local_time(start+timedelta(days=7),0,0,zone),duration_minutes=duration,clarification="Welke dag volgende week bedoel je?")
    if re.search(r"\bna mijn werk\b",message):return TimeHint(date=day.isoformat() if day else None,duration_minutes=duration,clarification="Hoe laat ben je klaar met werken en wil je afspreken?")
    # Avoid matching appointment durations and reminder offsets as a clock.
    clock_text=re.sub(r"\b(?:van|duurt|duur|ongeveer)\s+(?:anderhalf|een half|"+NUMBER+r")\s*(?:uur|uren|minuten?|min)\b","",message)
    hour=minute=None
    complex_half=re.search(r"\b("+NUMBER+r")\s+(voor|over)\s+half\s+("+NUMBER+r")\b",clock_text)
    quarter=re.search(r"\bkwart\s+(over|voor)\s+("+NUMBER+r")\b",clock_text)
    half=re.search(r"\bhalf\s+("+NUMBER+r")\b",clock_text)
    numeric=re.search(r"\b(?:om|vanaf|van|tussen)\s+("+NUMBER+r")(?::([0-5]\d))?(?:\s+uur)?\b|\b([0-2]?\d):([0-5]\d)\b",clock_text)
    if complex_half:
        amount=number(complex_half[1])
        if not 0<amount<30:raise AmbiguousTime("Welk exact tijdstip bedoel je?")
        hour=number(complex_half[3])-1;minute=30+amount*(1 if complex_half[2]=="over" else -1)
    elif quarter:
        hour=number(quarter[2])-(1 if quarter[1]=="voor" else 0);minute=45 if quarter[1]=="voor" else 15
    elif half:hour=number(half[1])-1;minute=30
    elif numeric:hour=number(numeric[1]) if numeric[1] else int(numeric[3]);minute=int(numeric[2] or numeric[4] or 0)
    if hour is not None:
        if not 0<=hour<24:raise AmbiguousTime("Welk tijdstip tussen 00:00 en 23:59 bedoel je?")
        explicit24=bool(numeric and (numeric[2] or numeric[3]))
        if hour<12 and not explicit24:
            if re.search(r"\b(?:middags?|avonds?|vanavond|morgenavond|morgenmiddag)\b",message):hour+=12
            elif not re.search(r"ochtend|nacht",message):
                candidates=[h for h in (hour,hour+12) if work_start<=h<work_end]
                if len(candidates)!=1:return TimeHint(date=day.isoformat() if day else None,duration_minutes=duration,clarification="Bedoel je dat tijdstip 's ochtends of 's middags/avonds?")
                hour=candidates[0]
        at=local_time(day,hour,minute,zone) if day else None
        return TimeHint(at,day.isoformat() if day else None,f"{hour:02}:{minute:02}",duration_minutes=duration)
    part=re.search(r"\b(eind van de middag|morgenochtend|morgenmiddag|morgenavond|vanavond|ochtend|middag|avond)\b",message)
    if part:
        return TimeHint(date=day.isoformat() if day else None,duration_minutes=duration,clarification="Welk exact tijdstip bedoel je "+part[1]+"?")
    if day:
        start=local_time(day,0,0,zone)
        return TimeHint(start,date=day.isoformat(),window_end=local_time(day+timedelta(days=1),0,0,zone),duration_minutes=duration)
    return TimeHint(duration_minutes=duration)
