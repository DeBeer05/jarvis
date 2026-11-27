"""Revisioned local lists and occasions, linked to the existing reminder engine."""
import json
import re
import uuid
from datetime import datetime,UTC
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import Field,model_validator
from server.natural.models import StrictModel
from server.natural.store import Conflict,encode
from server.natural.memory import SECRET


class Shopping(StrictModel):
    name:str=Field(min_length=1,max_length=120)
    amount:str=Field(default='',max_length=60)
    checked:bool=False


class Subscription(StrictModel):
    name:str=Field(min_length=1,max_length=120)
    amount:str=Field(pattern=r'^\d{1,6}(?:\.\d{1,2})?$')
    currency:Literal['EUR','USD','GBP']='EUR'
    cycle:Literal['monthly','yearly','weekly']='monthly'


class Occasion(StrictModel):
    name:str=Field(min_length=1,max_length=120)
    month:int=Field(ge=1,le=12)
    day:int=Field(ge=1,le=31)
    time:str=Field(default='09:00',pattern=r'^(?:[01]\d|2[0-3]):[0-5]\d$')
    category:Literal['birthday','anniversary']='birthday'
    @model_validator(mode='after')
    def valid_date(self):
        datetime(2000,self.month,self.day)
        return self


class Routine(StrictModel):
    name:str=Field(min_length=1,max_length=120)
    at:str=Field(max_length=50)
    repeat:Literal['once','daily','weekly','monthly','yearly']='once'
    @model_validator(mode='after')
    def valid_date(self):
        date=datetime.fromisoformat(self.at)
        if date.tzinfo is None or not 1970<=date.year<=2100:raise ValueError('Kies een datum met tijdzone tussen 1970 en 2100')
        return self


class Application(StrictModel):
    name:str=Field(min_length=1,max_length=120,title='Functie of sollicitatie')
    company:str=Field(default='',max_length=120,title='Werkgever')
    status:Literal['prepared','sent','reply_review','interview','rejected','offered','closed']='prepared'
    followup_at:str|None=Field(default=None,max_length=50,title='Optioneel opvolgmoment (ISO-datum met tijdzone)')
    thread_id:str=Field(default='',max_length=256,pattern=r'^[a-zA-Z0-9_-]*$',json_schema_extra={'x-internal':True})
    track_replies:bool=Field(default=False,json_schema_extra={'x-internal':True})
    @model_validator(mode='after')
    def date(self):
        if self.followup_at:
            date=datetime.fromisoformat(self.followup_at)
            if date.tzinfo is None or not 1970<=date.year<=2100:raise ValueError('Kies een datum met tijdzone tussen 1970 en 2100')
        return self


KINDS:dict[str,type[StrictModel]]={'shopping':Shopping,'subscription':Subscription,'occasion':Occasion,'routine':Routine,'application':Application}


class ItemInput(StrictModel):
    kind:Literal['shopping','subscription','occasion','routine','application']
    data:dict
    revision:int=Field(default=0,ge=0)
    request_id:str|None=Field(default=None,pattern=r'^[0-9a-f-]{36}$')


def migrate(db):
    if 'handled' not in {row[1] for row in db.execute('PRAGMA table_info(natural_events)')}:
        db.execute('ALTER TABLE natural_events ADD COLUMN handled INTEGER NOT NULL DEFAULT 0')
    db.execute('''CREATE TABLE IF NOT EXISTS natural_life_items(
        id TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,kind TEXT NOT NULL,payload TEXT NOT NULL,
        revision INTEGER NOT NULL,created REAL NOT NULL,updated REAL NOT NULL)''')
    db.execute('CREATE INDEX IF NOT EXISTS natural_life_owner ON natural_life_items(user_id,kind,updated)')


class LifeItems:
    def __init__(self,natural):self.natural=natural;self.store=natural.store

    @staticmethod
    def public(row):
        return {key:row[key] for key in ('id','kind','revision','created','updated')}|{'data':json.loads(row['payload'])}

    def list(self,principal,kind=None):
        if kind is not None and kind not in KINDS:raise ValueError('Onbekende lijst')
        with self.store.transaction(principal) as (db,user):
            rows=db.execute('SELECT * FROM natural_life_items WHERE user_id=? AND (? IS NULL OR kind=?) ORDER BY updated DESC LIMIT 201',(user,kind,kind)).fetchall()
        return {'items':[self.public(row) for row in rows[:200]],'has_more':len(rows)>200}

    def save(self,principal,value,identifier=None):
        body=ItemInput.model_validate(value);data=KINDS[body.kind].model_validate(body.data).model_dump(mode='json')
        payload=self.store.safe_content(encode(data))
        if SECRET.search(payload):raise ValueError('Geheimen horen niet in persoonlijke lijsten')
        updating=identifier is not None
        identifier=identifier or str(uuid.uuid4());now=self.store.clock()
        with self.store.transaction(principal,write=True) as (db,user):
            if not updating and body.request_id:
                identifier=str(uuid.uuid5(uuid.NAMESPACE_URL,'life:'+str(user)+':'+body.request_id))
                if db.execute("SELECT 1 FROM natural_audit WHERE user_id=? AND target=? AND event='life_item_deleted'",(user,identifier)).fetchone():raise Conflict('Dit item is eerder verwijderd')
            old=db.execute('SELECT * FROM natural_life_items WHERE id=? AND user_id=?',(identifier,user)).fetchone()
            if updating and not old:raise ValueError('Item niet gevonden')
            if not updating and old:
                if old['payload']==payload and old['kind']==body.kind:return self.public(old)
                raise Conflict('Dit verzoek is eerder met andere inhoud verwerkt')
            if (old and old['revision']!=body.revision) or (not old and body.revision):raise Conflict('Item gewijzigd; vernieuw eerst')
            if old and old['kind']!=body.kind:raise ValueError('Het lijsttype kan niet wijzigen')
            if not old and db.execute('SELECT count(*) FROM natural_life_items WHERE user_id=?',(user,)).fetchone()[0]>=1000:raise ValueError('Limiet van persoonlijke items bereikt')
            if old:self.cancel_linked(db,user,identifier)
            db.execute('INSERT INTO natural_life_items VALUES (?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,revision=excluded.revision,updated=excluded.updated',
                       (identifier,user,body.kind,payload,old['revision']+1 if old else 1,old['created'] if old else now,now))
            self.store.audit(db,user,principal.device_id,'life_item_saved',identifier)
            result=self.public(db.execute('SELECT * FROM natural_life_items WHERE id=?',(identifier,)).fetchone())
        result['reminder_requires_scheduling']=bool(old and body.kind in ('occasion','routine','application'))
        return result

    def cancel_linked(self,db,user,identifier):
        db.execute("UPDATE automation_jobs SET status='cancelled',updated=? WHERE tool IN ('ReminderCreate','WaitForReply') AND status IN ('queued','paused','blocked','waiting') AND json_extract(payload,'$.source_id')=? AND device_id IN (SELECT id FROM auth_devices WHERE user_id=?)",(self.store.clock(),identifier,user))
        db.execute("UPDATE automation_followups SET status='cancelled' WHERE id IN (SELECT id FROM automation_jobs WHERE status='cancelled')")

    def delete(self,principal,identifier,revision):
        with self.store.transaction(principal,write=True) as (db,user):
            changed=db.execute('DELETE FROM natural_life_items WHERE id=? AND user_id=? AND revision=?',(identifier,user,revision)).rowcount
            if not changed:raise Conflict('Item niet gevonden of gewijzigd')
            self.cancel_linked(db,user,identifier);self.store.audit(db,user,principal.device_id,'life_item_deleted',identifier)
        return {'deleted':True}

    def financial_overview(self,principal):
        totals:dict[str,Decimal]={}
        with self.store.transaction(principal) as (db,user):
            items=[self.public(row) for row in db.execute("SELECT * FROM natural_life_items WHERE user_id=? AND kind='subscription'",(user,)).fetchall()]
        for item in items:
            value=item['data'];amount=Decimal(value['amount'])
            annual=amount*{'monthly':12,'yearly':1,'weekly':52}[value['cycle']]
            totals[value['currency']]=totals.get(value['currency'],Decimal(0))+annual
        return {'source':'zelf ingevoerde abonnementen; geen bankkoppeling','annual':{key:str(value.quantize(Decimal('.01'))) for key,value in totals.items()},
                'monthly_estimate':{key:str((value/12).quantize(Decimal('.01'))) for key,value in totals.items()}}

    def reminder(self,principal,identifier,revision):
        with self.store.transaction(principal) as (db,user):
            row=db.execute('SELECT * FROM natural_life_items WHERE id=? AND user_id=?',(identifier,user)).fetchone()
            if not row or row['revision']!=revision:raise Conflict('Item gewijzigd; vernieuw eerst')
            value=self.public(row)
        settings=self.natural.settings.get(principal)['settings'];zone=settings['general']['timezone']
        data=value['data'];now=self.store.clock()
        if value['kind']=='occasion':
            local=datetime.fromtimestamp(now,ZoneInfo(zone));year=local.year
            for year in range(year,year+9):
                try:
                    at=datetime(year,data['month'],data['day'],int(data['time'][:2]),int(data['time'][3:]),tzinfo=ZoneInfo(zone))
                    if at.timestamp()>now and at.astimezone(UTC).astimezone(ZoneInfo(zone)).replace(tzinfo=None)==at.replace(tzinfo=None):break
                except ValueError:pass
            else:raise ValueError('Geen geldige jaarlijkse herinnering gevonden')
            repeat='yearly';text=('Verjaardag: ' if data['category']=='birthday' else 'Jubileum: ')+data['name']
        elif value['kind']=='routine':
            at=datetime.fromisoformat(data['at']);repeat=data['repeat'];text=data['name']
            if at.timestamp()<=now:
                if repeat=='once':raise ValueError('Kies een toekomstig herinneringsmoment')
                from server.automation.models import next_occurrence
                at=datetime.fromtimestamp(next_occurrence(at.timestamp(),repeat,zone,now),ZoneInfo(zone))
        elif value['kind']=='application':
            from datetime import timedelta
            at=datetime.fromisoformat(data['followup_at']) if data['followup_at'] else datetime.fromtimestamp(now,UTC)+timedelta(hours=settings['tasks']['followup_hours'])
            if at.timestamp()<=now:raise ValueError('Kies een toekomstig opvolgmoment')
            if data['thread_id'] and data['track_replies']:
                return self.natural.automation.submit(principal.device_id,'WaitForReply',
                    {'thread_id':data['thread_id'],'due':at.isoformat(),'source_id':identifier,'source_revision':revision},
                    str(uuid.uuid5(uuid.NAMESPACE_URL,'life-followup:'+identifier+':'+str(revision))))
            repeat='once';text='Sollicitatie opvolgen: '+data['name']
        else:raise ValueError('Voor dit lijsttype is geen herinnering ingesteld')
        engine=self.natural.automation
        return engine.submit(principal.device_id,'ReminderCreate',{'text':text,'at':at.isoformat(),'repeat':repeat,'timezone':zone,'source_id':identifier,'source_revision':revision},
                             str(uuid.uuid5(uuid.NAMESPACE_URL,'life:'+identifier+':'+str(revision))))

    def guard_reminder(self,device,payload):
        if not payload.get('source_id'):return
        with self.natural.automation.store.db() as db:
            row=db.execute('SELECT i.revision,i.kind,i.payload FROM natural_life_items i JOIN auth_devices d ON d.user_id=i.user_id WHERE i.id=? AND d.id=? AND d.revoked_at IS NULL',
                           (payload['source_id'],device)).fetchone()
        if not row or row['revision']!=payload['source_revision']:raise ValueError('De bron van deze herinnering is gewijzigd of verwijderd')
        if payload.get('thread_id') and (row['kind']!='application' or json.loads(row['payload']).get('thread_id')!=payload['thread_id']):raise ValueError('Mailgesprek hoort niet bij deze sollicitatie')

    async def link_mail(self,principal,identifier,revision,message_id):
        engine=self.natural.automation
        engine.permissions.check(principal.device_id,'automation:read');engine.permissions.check_tool(principal.device_id,'EmailRead')
        mail=await engine.integrations.mail_read(message_id)
        engine.permissions.check(principal.device_id,'automation:read');engine.permissions.check_tool(principal.device_id,'EmailRead')
        if mail.get('id')!=message_id or not mail.get('threadId'):raise ValueError('Mailbron kon niet worden bevestigd')
        with self.store.transaction(principal) as (db,user):
            row=db.execute("SELECT * FROM natural_life_items WHERE id=? AND user_id=? AND kind='application'",(identifier,user)).fetchone()
            if not row or row['revision']!=revision:raise Conflict('Sollicitatie gewijzigd; vernieuw eerst')
            data=json.loads(row['payload'])
        data.update(thread_id=mail['threadId'],track_replies=True)
        return self.save(principal,{'kind':'application','data':data,'revision':revision},identifier)

    def reply_detected(self,device,thread):
        engine=self.natural.automation
        engine.permissions.check(device,'automation:read');engine.permissions.check(device,'automation:write')
        with engine.store.db(True) as db:
            rows=db.execute("SELECT i.* FROM natural_life_items i JOIN auth_devices d ON d.user_id=i.user_id WHERE d.id=? AND d.revoked_at IS NULL AND i.kind='application' AND json_extract(i.payload,'$.thread_id')=? AND json_extract(i.payload,'$.track_replies')=1",(device,thread)).fetchall()
            for row in rows:
                value=json.loads(row['payload'])
                if value['status'] in ('closed','rejected','offered'):continue
                value['status']='reply_review'
                db.execute('UPDATE natural_life_items SET payload=?,revision=revision+1,updated=? WHERE id=?',(encode(value),self.store.clock(),row['id']))
                self.store.audit(db,row['user_id'],device,'application_reply_requires_review',row['id'])

    @staticmethod
    def intent(message):
        text=re.sub(r'^jarvis[, ]+','',message.strip(),flags=re.I).rstrip('.!?')
        if re.fullmatch(r'(?:toon|geef)(?: mij| me)? (?:mijn |de )?(?:boodschappenlijst|boodschappen)|wat staat (?:er )?op mijn boodschappenlijst',text,re.I):return 'shopping',''
        if re.fullmatch(r'(?:toon|geef)(?: mij| me)? (?:mijn |het )?(?:kostenoverzicht|financieel overzicht|abonnementen)|wat zijn mijn maandlasten',text,re.I):return 'finance',''
        match=re.fullmatch(r'(?:zet|voeg) (.{1,120}?) (?:op|toe aan) (?:mijn |de )?boodschappenlijst',text,re.I)
        if match:return 'add',match[1]
        match=re.fullmatch(r'(?:haal|verwijder) (.{1,120}?) van (?:mijn |de )?boodschappenlijst',text,re.I)
        if match:return 'remove',match[1]
        return None

    def command(self,run):
        intent=self.intent(run.message)
        if not intent:return None
        from server.natural.presence import address
        kind,name=intent;settings=run.natural_context['settings']
        if kind=='finance':
            overview=self.financial_overview(run.principal)
            if not overview['annual']:return address('Er zijn nog geen abonnementskosten ingevoerd',settings)
            return address('Uw financieel overzicht',settings)+'\n'+'\n'.join(f"{currency}: {overview['monthly_estimate'][currency]} per maand (raming), {amount} per jaar." for currency,amount in overview['annual'].items())+'\nZelf ingevoerde kosten; geen bankkoppeling. Valuta worden niet omgerekend.'
        if kind=='add':
            existing=[item for item in self.list(run.principal,'shopping')['items'] if item['data']['name'].casefold()==name.casefold() and not item['data']['checked']]
            if existing:return address(name+' staat al op uw boodschappenlijst',settings)
            self.save(run.principal,{'kind':'shopping','data':{'name':name},'request_id':run.request_id})
            return address(name+' staat op uw boodschappenlijst',settings)
        result=self.list(run.principal,'shopping')
        if kind=='shopping':
            items=result['items']
            return (address('Uw boodschappenlijst',settings)+'\n'+'\n'.join(('- [x] ' if item['data']['checked'] else '- ')+item['data']['name']+(' · '+item['data']['amount'] if item['data']['amount'] else '') for item in items)+ ('\nEerste 200 items; lijst is groter.' if result['has_more'] else '')) if items else address('Uw boodschappenlijst is leeg',settings)
        matches=[item for item in result['items'] if item['data']['name'].casefold()==name.casefold()]
        if len(matches)!=1:return address('Ik vind geen uniek item met die naam; kies het item in de lijst',settings)
        item=matches[0];self.delete(run.principal,item['id'],item['revision'])
        return address(name+' is van uw boodschappenlijst verwijderd',settings)
