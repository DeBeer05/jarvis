"""Conservative first-person preferences; no inferred facts or external text."""
import re

from server.natural.memory import SENSITIVE,SECRET


def preference(message):
    text=message.strip()
    if not 3<=len(text)<=500 or "?" in text or "\n" in text or any(mark in text for mark in ('"','“','”','`')):return None
    if SENSITIVE.search(text) or SECRET.search(text):return None
    if not re.match(r"^(?:ik\s+(?:\w+\s+){0,5}(?:liever|liefst)|mijn voorkeur is|ik geef de voorkeur aan|ik hou(?:d)? van)\b",text,re.I):return None
    key=""
    if re.search(r"\bafspr(?:aak|aken)\b",text,re.I):
        if re.search(r"\b(?:na|voor|tussen)\b",text,re.I):key="calendar:preferred_time"
        elif re.search(r"\b(?:maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag)\b",text,re.I):key="calendar:preferred_days"
    return {"content":text,"kind":"preference","category":"preference","key":key,"confidence":1.0}


def automatic_preference(message):
    value=preference(message)
    if value is None:return None
    # Automatic collection is deliberately a narrow positive grammar, not a
    # blacklist that might miss an unfamiliar medical or other sensitive term.
    text=message.casefold().strip().rstrip(".! ")
    if re.fullmatch(r"ik (?:gebruik|programmeer) (?:liever|liefst) (?:in )?(?:python|rust|kotlin|java|javascript|typescript|go|csharp|c\+\+)",text):
        return {**value,"category":"technical","key":"technical:preferred_language"}
    allowed=set("ik plan maak heb wil mijn afspraken voortaan liever liefst na voor tussen en om uur uren s ochtends middags avonds een twee drie vier vijf zes zeven acht negen tien elf twaalf dertien veertien vijftien zestien zeventien achttien negentien twintig maandag dinsdag woensdag donderdag vrijdag zaterdag zondag op".split())
    words=re.findall(r"\w+",text)
    if value["key"].startswith("calendar:") and all(word in allowed or word.isdecimal() for word in words):return value
    return None
