"""User-sourced calendar commands; durable slots and verified event references."""
import json
import re
from dataclasses import replace
from datetime import datetime,timedelta,UTC
from urllib.parse import quote
from typing import Any
from zoneinfo import ZoneInfo

from server.automation.google import REQUEST_GUARD
from server.automation.models import validate
from server.automation.store import fingerprint
from server.natural.calendar import create_parameters,update_parameters,timing_text,TITLE_PREFIX
from server.natural.temporal import AmbiguousTime,normalize_dayparts,resolve,NUMBER


def creating(text):
    source=timing_text(text,title(text))
    request=re.match(r'^\s*(?:jarvis[, ]+)?(?:graag\s+)?(?:(?:maak|plan|boek|zet|voeg)\b|(?:kun|kan|wil|zou)\s+(?:je|u|jij)\b|ik\s+(?:wil|zou\s+graag)\b)',source,re.I)
    return bool(request and not re.search(r'\b(?:vertellen|uitleggen|bespreken|weten|praten|hoe ik|hoe je)\b',source,re.I)
        and re.search(r'\b(?:afspraak|meeting|vergadering|agenda|kalender)\b',source,re.I)
        and re.search(r'\b(?:maak|maakt|maken|aanmaken|plan|plant|plannen|inplannen|zet|zetten|voeg|voegt|toevoegen|boek|boekt|boeken)\b',source,re.I)
        and not re.search(r'\b(?:niet|geen|misschien|uitleg|betekent)\b',source,re.I)
        and not re.match(r'\s*(?:hoe|waarom|wat betekent)\b',source,re.I))


def title(text):
    text=re.sub(r'\b(met\s+(?:de\s+)?titel)(?=[a-zÀ-ÿ])',r'\1 ',text,flags=re.I)
    for pattern in (r'\b(?:die|dat)\s+(?!(?:je|u|jij)\b)["“]?(.+?)["”]?\s+heet\b',
                    TITLE_PREFIX+r'["“]([^"”]+)["”]',
                    TITLE_PREFIX+r'(.+?)(?=[,;.!?]|$|\s+(?:op|voor|om|van|tot)\s+(?:'+NUMBER+r'|morgen|overmorgen|vandaag|half|kwart)\b)',
                    r'["“]([^"”]+)["”]'):
        match=re.search(pattern,text,re.I)
        if match:return match[1].strip(' "“”.,!?')[:500]
    match=re.search(r'\b(afspraak|meeting|vergadering)\s+(met|bij|over)\s+(.+?)(?=\s+(?:morgen|overmorgen|vandaag|op|om|voor|van|in)\b|[.!?]|$)',text,re.I)
    if match:return match[1].capitalize()+' '+match[2]+' '+match[3].strip()
    match=re.search(r'\bmet\s+(?!titel\b|onderwerp\b)(.+?)(?=\s+(?:morgen|overmorgen|vandaag|op|om|voor|van|in)\b|\s+en\s+herinner|[.!?]|$)',text,re.I)
    if match and re.search(r'\bafspraak\b',text,re.I):return 'Afspraak met '+match[1].strip()
    match=re.search(r'\b(?:zet|plan|boek|maak)\s+(.+?)\s+(?:(?:voor|op)\s+)?(?:morgen|overmorgen|vandaag|\d{1,2}\s+[a-z]+|om\s+)\b',text,re.I)
    if match and not re.search(r'\b(?:afspraak|voor|een|mijn|de|hem|die|dat|morgen|overmorgen|vandaag|om|op)\b',match[1],re.I):return match[1].strip()
    if re.search(r'\b(?:agenda|kalender)\b',text,re.I):
        from server.natural.calendar import outing_title
        return outing_title(text) or ''
    return ''


CHANGE=re.compile(r'^\s*(?:(?:maak|zet|verander|wijzig)\s+(?:daar|dat|die|hem|de tijd)\s+.+|(?:verplaats|verzet|verschuif)\s+(?:hem|haar|die|dat|de afspraak)\b.*|zet\s+.+\s+erbij)[.!?\s]*$',re.I)
UNRELATED=re.compile(r'^\s*(?:(?:wat|hoe|waarom|wie|vertel|hallo|hoi|bedankt)\b|(?:ik|wij|we)\s+(?:heb|ben|was|ga|vind|denk|wil\s+(?:praten|vertellen|uitleggen|bespreken|weten))\b)',re.I)


class CalendarDialogue:
    def __init__(self,chat):self.chat=chat

    def routing_text(self,text):return timing_text(text,title(text)) if creating(text) else text

    def bound(self,run,item):
        return item.get('device')==run.principal.device_id and item.get('session')==run.principal.session_id

    def candidate(self,run):
        memory=self.chat.memory(run)
        return bool(creating(run.message) or memory.get('calendar_action') and not UNRELATED.match(run.message) or CHANGE.fullmatch(run.message) and memory.get('last_calendar'))

    def save(self,run,**value):
        self.chat.remember(run,'calendar_action',[{'device':run.principal.device_id,'session':run.principal.session_id,
            'expires':self.chat.engine.store.clock()+900,**value}])

    async def handle(self,run):
        c=self.chat;memory=c.memory(run);pending=(memory.get('calendar_action') or [{}])[0]
        # A named/other calendar needs the existing CalendarList resolution;
        # never silently replace an explicit destination with the default.
        if creating(run.message) and (re.search(r'\b(?:andere|gedeelde|werk|privé|familie)[ -]*(?:agenda|kalender)\b',run.message,re.I)
            or re.search(r'\b(?:agenda|kalender)\s+(?!(?:zet\w*|toevoeg\w*|inplan\w*|op|om|voor|met|die|dat|en|morgen|overmorgen|vandaag|maken)\b)["“]?[a-zÀ-ÿ]',run.message,re.I)):
            return None
        if pending and (not self.bound(run,pending) or pending.get('expires',0)<c.engine.store.clock()):
            c.remember(run,'calendar_action',[]);pending={}
        if pending.get('job'):
            row=c.engine.store.get(pending['job'])
            if row['status'] in ('queued','running'):return 'De agenda verwerkt de wijziging nog. Ik heb nog geen bevestiging.'
            await self.result(run,row,pending['operation'])
            memory=c.memory(run);pending={}
        if pending and re.fullmatch(r'\s*(?:nee|laat maar|annuleer)[.!\s]*',run.message,re.I):
            c.remember(run,'calendar_action',[]);return 'Begrepen. Ik heb niets ingepland.'
        if CHANGE.fullmatch(run.message) and memory.get('last_calendar'):
            if memory.get('pending') or memory.get('write_question'):return None
            recent=(memory.get('recent') or [{}])[0].get('kind')
            if recent not in (None,'events') and not re.search(r'\b(?:afspraak|agenda|vergadering)\b',run.message,re.I):
                return 'Welke afspraak wilt u aanpassen?'
            c.remember(run,'pending',[]);c.remember(run,'decision',[])
            return await self.update(run,memory['last_calendar'][0])
        if creating(run.message):
            pending={}
            c.remember(run,'last_calendar',[]);c.remember(run,'pending',[]);c.remember(run,'decision',[])
        if not creating(run.message) and not pending:return None
        if pending and c.approvals.is_answer(run.message):
            return 'Welke titel mag ik de afspraak geven?' if pending.get('missing')=='title' else 'Welke datum en begintijd bedoelt u?'
        if pending and UNRELATED.match(run.message):return None
        if pending.get('operation')=='CalendarUpdate':return await self.update(run,pending['reference'])
        if re.search(r'\b(?:uitnodig\w*|herhaal\w*|wekelijks|dagelijks)\b',run.message,re.I):return None
        config=run.natural_context['settings'] if run.natural_context else {}
        config={**config,'general':{**config.get('general',{}),'timezone':'Europe/Amsterdam'},
            'calendar':{**config.get('calendar',{}),'duration_minutes':60,'use_defaults':True}}
        anchor=pending.get('anchor') or datetime.fromtimestamp(c.engine.store.clock(),UTC).isoformat()
        now=datetime.fromisoformat(anchor)
        instruction=pending.get('instruction','')
        if pending.get('missing')=='date_choice':
            correction=resolve(run.message,now=now,timezone='Europe/Amsterdam')
            if correction.date:instruction=re.sub(r'\b(?:vanmorgen|vanochtend)\b',correction.date,instruction,flags=re.I)
        if creating(run.message) and not pending:instruction=run.message
        elif instruction:
            if pending.get('missing')!='title':instruction+='\nAanvullende gegevens van dezelfde gebruiker: '+run.message
        else:instruction=run.message
        summary=title(run.message) or pending.get('summary','') or title(instruction)
        if pending.get('missing')=='title' and not summary and not creating(run.message):summary=run.message.strip(' .!?')[:500]
        try:
            timing=timing_text(instruction,summary)
            conflict=bool(re.search(r'\b(?:vanmorgen|vanochtend)\b',timing,re.I) and re.search(r'\b(?:middag|middags|avond|avonds)\b',timing,re.I))
            if conflict:raise AmbiguousTime("U noemt vanmorgen en 's middags. Bedoelt u vandaag of morgen?")
            payload=create_parameters({'summary':summary},timing,config,now=now)
            if not summary:raise AmbiguousTime('Welke titel mag ik de afspraak geven?')
        except AmbiguousTime as error:
            self.save(run,instruction=instruction,summary=summary,anchor=anchor,missing='date_choice' if conflict else 'title' if not summary and 'titel' in str(error) else 'time')
            question=str(error)
            if not config.get('tasks',{}).get('combine_questions',True) and question.startswith('Op welke datum en'):question='Op welke datum wilt u de afspraak?'
            return question
        for field,pattern in (('location',r'\b(?:locatie|adres)\s*:?\s*(.+?)(?=,\s*(?:locatie|adres|beschrijving)\b|[.!?]|$)'),('description',r'\bbeschrijving\s*:?\s*(.+?)(?=,\s*(?:locatie|adres|beschrijving)\b|[.!?]|$)')):
            match=re.search(pattern,instruction,re.I)
            if match:payload[field]=match[1].strip()
        if pending.get('missing')=='title':instruction+='\nAanvullende gegevens van dezelfde gebruiker: met titel "'+summary+'"'
        return await self.execute(replace(run,message=instruction),'CalendarCreate',payload)

    async def update(self,run,reference):
        c=self.chat
        if not self.bound(run,reference):return 'Welke afspraak wilt u aanpassen?'
        c.guard(run,'automation:read');c.engine.permissions.check_tool(run.principal.device_id,'CalendarRead')
        guard_context:Any=REQUEST_GUARD
        guard=guard_context.set(lambda:c.guard(run,'automation:read'))
        try:
            event=await c.engine.integrations.api('calendar_read','/calendar/v3/calendars/'+quote(reference['calendar_id'],safe='')+'/events/'+quote(reference['id'],safe=''))
        finally:guard_context.reset(guard)
        if event.get('id')!=reference['id'] or not event.get('etag') or event.get('status')=='cancelled':return 'Ik kan de bedoelde afspraak niet meer verifiëren.'
        payload={'calendar_id':reference['calendar_id'],'event_id':event['id'],'etag':event['etag'],
            'summary':event.get('summary',''),'location':event.get('location',''),'description':event.get('description'),
            'attendees':[item['email'] for item in event.get('attendees',[]) if item.get('email')], 'recurrence':event.get('recurrence',[])}
        text=normalize_dayparts(run.message)
        location=re.fullmatch(r'\s*zet\s+(.+?)\s+erbij[.!?\s]*',text,re.I)
        clock=re.fullmatch(r'\s*(?:maak|zet|verander|wijzig)\s+(?:daar|dat|die|hem|de tijd)\s+(.+?)(?:\s+van)?[.!?\s]*',text,re.I)
        if location:
            payload['location']=location[1].strip();text=''
        elif clock:
            text='om '+clock[1]
            if not re.search(r'middag|avond|ochtend|nacht|\d{1,2}:\d{2}',text,re.I):
                hour=datetime.fromisoformat(event['start']['dateTime']).astimezone(ZoneInfo('Europe/Amsterdam')).hour
                text+=' middag' if hour>=12 else ' ochtend'
        config=run.natural_context['settings'] if run.natural_context else {}
        config={**config,'general':{**config.get('general',{}),'timezone':'Europe/Amsterdam'}}
        try:payload=update_parameters(payload,text,event,config,now=datetime.fromtimestamp(c.engine.store.clock(),UTC))
        except AmbiguousTime as error:
            self.save(run,operation='CalendarUpdate',reference=reference,instruction=run.message,missing='time')
            return str(error)
        return await self.execute(run,'CalendarUpdate',payload)

    async def execute(self,run,tool,payload):
        c=self.chat;c.guard(run,'automation:write')
        if run.allowed_tools is not None and tool not in run.allowed_tools:raise ValueError('Actie buiten deze opdracht')
        payload=validate(tool,payload)
        config=run.natural_context['settings'] if run.natural_context else {}
        policy=config.get('autonomy',{}).get('actions',{}).get(tool)
        # Invitations, series and explicitly ask-only policies keep exact previews.
        direct=not payload['attendees'] and not payload['recurrence'] and policy!='ask'
        c.guard(run,'automation:approve')
        row=c.engine.submit(run.principal.device_id,tool,payload,'chat-calendar:'+run.principal.device_id+':'+run.request_id+run.tool_operation)
        c.remember(run,'write_question',[]);c.remember(run,'calendar_action',[])
        c.remember(run,'jobs',[{'id':row['id'],'tool':tool,'status':row['status']}])
        if not direct:return c.approvals.show(run,row)
        self.save(run,job=row['id'],operation=tool)
        if row['status']=='approval':
            challenge=c.engine.approvals.challenge(row['id'],run.principal)
            expected=fingerprint([tool,payload])
            if challenge['fingerprint']!=expected:return c.approvals.show(run,c.engine.store.get(row['id']))
            c.guard(run,'automation:approve')
            c.engine.approvals.decide(row['id'],run.principal,challenge['token'],True,expected_fingerprint=expected)
            c.engine.audit.record('explicit_calendar_request',row['id'],run.principal.device_id)
        await c.engine.tick(job_id=row['id'])
        c.guard(run,'automation:read');row=c.engine.store.get(row['id'])
        return await self.result(run,row,tool)

    async def result(self,run,row,tool):
        c=self.chat
        if row['status']!='completed':
            if row['status'] not in ('queued','running'):c.remember(run,'calendar_action',[])
            return c.approvals.status(row)
        event=json.loads(row['result'] or '{}');payload=json.loads(row['payload'])
        if not event.get('id') or not event.get('etag') or not event.get('start',{}).get('dateTime'):
            return 'De agenda heeft geen volledige bevestiging teruggegeven. Ik herhaal de actie niet automatisch.'
        c.remember(run,'last_calendar',[{'id':event['id'],'calendar_id':payload['calendar_id'],'device':run.principal.device_id,'session':run.principal.session_id}])
        c.remember(run,'events',[{**{key:event[key] for key in ('id','etag','summary','start','end','location','attendees','recurrence') if key in event},'calendar_id':payload['calendar_id']}])
        c.remember(run,'calendar_action',[]);c.remember(run,'decision',[{'id':row['id'],'device':run.principal.device_id,'session':run.principal.session_id}])
        start=datetime.fromisoformat(event['start']['dateTime']).astimezone(ZoneInfo(payload['timezone']))
        if tool=='CalendarUpdate':
            if re.fullmatch(r'\s*zet\s+.+\s+erbij[.!?\s]*',run.message,re.I):return 'Locatie aangepast naar '+event.get('location',payload['location'])+'.'
            if re.match(r'\s*(?:maak|zet|verander|wijzig)\s+(?:daar|dat|die|hem|de tijd)\b',run.message,re.I):return f'Aangepast naar {start:%H:%M} uur.'
            return f'Aangepast naar {start:%d-%m-%Y om %H:%M} uur.'
        today=datetime.fromtimestamp(c.engine.store.clock(),ZoneInfo(payload['timezone'])).date()
        label='morgen' if start.date()==today+timedelta(days=1) else 'vandaag' if start.date()==today else start.strftime('%d-%m-%Y')
        return f"{event.get('summary',payload['summary'])} staat {label} om {start:%H:%M} uur in uw agenda, meneer."
