"""Bounded direct latest-mail retrieval; source IDs never come from model output."""
import re
from server.natural.responses import sentences,CRITICAL

COUNTS={'een':1,'twee':2,'drie':3,'vier':4,'vijf':5,'zes':6,'zeven':7,'acht':8,'negen':9,'tien':10,'elf':11,'twaalf':12,'dertien':13,'veertien':14,'vijftien':15,'zestien':16,'zeventien':17,'achttien':18,'negentien':19,'twintig':20}


def latest_count(message):
    if re.search(r'\b(?:stuur\w*|verstuur\w*|verzend\w*|schrijf\w*|antwoord\w*|concept\w*)\b',message,re.I):return None
    match=re.search(r'\b(?:laatste|recentste|recente|nieuwste)\s+(?:(\d{1,3}|'+ '|'.join(COUNTS)+r')\s+)?((?:e[-‑]?)?mails?|berichten)\b',message,re.I)
    if not match:return None
    # Specific sender/date/folder filters stay with the existing validated planner.
    if re.search(r'\b(?:van|over|uit|met|voor|tussen|sinds|na|vóór)\b',message[match.end():],re.I):return None
    if re.search(r'\b(?:ongelezen|verzonden|verstuurde|spam|prullenbak|onderwerp(?:en)?|afzenders?|agenda|afspraak)\b',message,re.I):return None
    value=match[1]
    return (int(value) if value.isdigit() else COUNTS[value.casefold()]) if value else (1 if match[2].casefold() in ('mail','email','e-mail','e‑mail') else 5)


def excerpt(text,budget):
    parts=sentences(text);critical=[part for part in parts if CRITICAL.search(part)]
    chosen=[];used=0
    for part in [*critical,*parts]:
        if part in chosen:continue
        if used+len(part)>budget:continue
        chosen.append(part);used+=len(part)+1
    if not chosen and text.strip():
        end=text.rfind(' ',0,budget);chosen=[text[:end if end>0 else budget]]
    return ' '.join(chosen),len(' '.join(chosen))<len(text.strip())
