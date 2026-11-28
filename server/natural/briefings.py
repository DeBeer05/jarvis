"""Source-bound briefings on the existing scheduler, without a second AI agent."""
import asyncio
import json
import re
import uuid
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo

from server.automation.google import REQUEST_GUARD
from server.automation.store import fingerprint
from server.natural.models import UserSettings
from server.natural.presence import address
from server.natural.public_sources import PublicSources
from server.security.types import AuthError

REQUEST=re.compile(r'(?:jarvis[, ]+)?(?:(?:geef|toon|lees)(?: mij| me)?(?: de| mijn| een)? (?:ochtend|avond|terugkomst)?briefing(?: voor)?|(?:mijn |een )?(?:ochtend|avond|terugkomst)?briefing graag)[.!?]*',re.I)


class BriefingManager:
    def __init__(self,natural,*,sources=None):
        self.natural=natural;self.engine=natural.automation;self.sources=sources or PublicSources(clock=natural.store.clock)

    async def close(self):await self.sources.close()

    @staticmethod
    def signature(settings):
        return fingerprint([settings['briefings'],settings['general']['timezone']])

    def device(self,device):
        with self.engine.store.db() as db:
            row=db.execute("SELECT d.user_id,s.payload FROM auth_devices d LEFT JOIN natural_settings s ON s.user_id=d.user_id AND s.scope='user' AND s.device_id='' WHERE d.id=? AND d.trusted=1 AND d.revoked_at IS NULL",(device,)).fetchone()
        if not row:raise ValueError('Apparaat is niet meer bevoegd')
        config=UserSettings.model_validate_json(row['payload']).model_dump(mode='json') if row['payload'] else UserSettings().model_dump(mode='json')
        return row['user_id'],config

    def guard(self,device,tool):
        self.engine.permissions.check(device,'automation:read');self.engine.permissions.check_tool(device,tool)
        if tool in self.engine.store.preference('disabled_tools',[]):raise ValueError('Bron uitgeschakeld door eigenaar')

    async def build(self,device,kind='morning'):
        user,settings=self.device(device);config=settings['briefings'];zone=settings['general']['timezone']
        now=datetime.fromtimestamp(self.engine.store.clock(),ZoneInfo(zone))
        async def calendar():
            self.guard(device,'CalendarRead')
            if 'calendar_read' not in self.engine.integrations.status()['features']:raise ValueError('Agenda niet gekoppeld')
            start=now.replace(hour=0,minute=0,second=0,microsecond=0)
            data=await self.engine.integrations.events({'calendar_id':settings['calendar']['default_calendar'],'start':start.isoformat(),'end':(start+timedelta(days=1)).isoformat(),'query':''})
            self.guard(device,'CalendarRead');items=[item for item in data.get('items',[]) if item.get('status')!='cancelled']
            if any(not item.get('id') or not isinstance(item.get('start',{}),dict) or not isinstance(item.get('end',{}),dict) for item in items):raise ValueError('Onbevestigde agendabron')
            intervals=[];alternatives=[]
            for item in items:
                try:
                    begin=datetime.fromisoformat(item['start']['dateTime']);end=datetime.fromisoformat(item['end']['dateTime'])
                    if begin.utcoffset() is not None and end.utcoffset() is not None:intervals.append((begin,end,item))
                except (KeyError,ValueError):continue
            intervals.sort(key=lambda item:item[0]);overlaps=[left[2] for left,right in zip(intervals,intervals[1:]) if left[1]>right[0]]
            if overlaps and settings['calendar']['alternatives']:
                item=overlaps[0]
                try:
                    analysis=await asyncio.wait_for(self.engine.reschedule.analyze({'calendar_id':settings['calendar']['default_calendar'],'event_id':item['id'],'start':item['start']['dateTime'],'end':item['end']['dateTime'],'timezone':zone},device),2)
                    alternatives=analysis['alternatives'][:2]
                except (ValueError,AuthError,TimeoutError):pass
            return {'items':[{'id':str(item['id']),'title':str(item.get('summary','Afspraak'))[:160],'start':item.get('start',{}),'end':item.get('end',{})} for item in items[:5]],'partial':bool(data.get('nextPageToken')) or len(items)>5,'count':len(items),'overlaps':len(overlaps),'alternatives':alternatives}
        async def email():
            self.guard(device,'EmailSearch');self.guard(device,'EmailRead')
            if 'gmail_read' not in self.engine.integrations.status()['features']:raise ValueError('Gmail niet gekoppeld')
            found=await self.engine.integrations.mail_search('in:inbox is:unread')
            ids=list(dict.fromkeys(item['id'] for item in found.get('messages',[])))[:3];items=[]
            for identifier in ids:
                self.guard(device,'EmailRead');mail=await self.engine.integrations.mail_read(identifier)
                if mail.get('id')!=identifier:raise ValueError('Onbevestigde mailbron')
                headers={item['name'].casefold():item['value'] for item in mail.get('payload',{}).get('headers',[])}
                items.append({'id':identifier,'subject':str(headers.get('subject','Zonder onderwerp'))[:160]})
            self.guard(device,'EmailRead')
            return {'items':items,'partial':bool(found.get('nextPageToken')) or len(found.get('messages',[]))>len(items),'bodies_read':False}
        calls=[]
        for name,enabled,read in (
            ('calendar',config['calendar'],calendar),('email',config['email'],email),
            ('weather',config['weather'],lambda:self.sources.weather(config['location'],zone)),
            ('news',config['news'],self.sources.news),
            ('traffic',config['traffic'],lambda:self.sources.traffic(config['location']))):
            if enabled:calls.append((name,read))
        async def fetch(name,read):
            guard=REQUEST_GUARD.set(lambda:self.engine.permissions.check(device,'automation:read')) if name in ('calendar','email') else None
            try:
                tool={'weather':'WeatherRead','news':'NewsRead','traffic':'TrafficRead'}.get(name)
                if tool:self.guard(device,tool)
                data=await asyncio.wait_for(read(),8)
                if tool:self.guard(device,tool)
                return name,{'status':'available','data':data}
            except asyncio.CancelledError:raise
            except Exception:return name,{'status':'unavailable','reason':'Niet gekoppeld, niet toegestaan of tijdelijk niet bereikbaar'}
            finally:
                if guard is not None:REQUEST_GUARD.reset(guard)
        sources=dict(await asyncio.gather(*(fetch(name,read) for name,read in calls)))
        self.device(device)  # revocation before publishing matters as much as before reads
        lines=[{'morning':'Ochtendbriefing','evening':'Avondbriefing','return':'Terugkomstbriefing','prepare':'Voorbereide briefing'}.get(kind,'Briefing')+f' · {now:%d-%m-%Y %H:%M}']
        for name,value in sources.items():
            if value['status']!='available':
                lines.append({'calendar':'Agenda','email':'E-mail','weather':'Weer','news':'Nieuws','traffic':'Verkeer'}[name]+': niet beschikbaar; niet gecontroleerd.');continue
            data=value['data']
            if name=='calendar':
                lines.append('Agenda: '+str(data['count'])+' afspraken in het ontvangen resultaat'+(' (gedeeltelijk).' if data['partial'] else '.'))
                intervals=[]
                for item in data['items'][:3]:
                    start=item['start'];clock=start.get('dateTime',start.get('date','tijd onbekend'))
                    lines.append('- '+str(clock)+' · '+item['title'])
                    try:
                        begin=datetime.fromisoformat(start['dateTime']);end=datetime.fromisoformat(item['end']['dateTime'])
                        if begin.utcoffset() is not None and end.utcoffset() is not None:intervals.append((begin,end))
                    except (KeyError,ValueError):pass
                intervals.sort()
                if data['overlaps']:lines.append('Let op: er overlappen afspraken. Ik heb niets verplaatst.')
                for proposal in data['alternatives']:lines.append('Beschikbaar voorstel volgens de agenda: '+proposal['start']+' tot '+proposal['end']+'. Reistijd niet gecontroleerd; wijziging vereist toestemming.')
            elif name=='email':
                lines.append('E-mail: recente ongelezen onderwerpen; inhoud niet gelezen'+(' (gedeeltelijk).' if data['partial'] else '.'))
                lines.extend('- '+item['subject'] for item in data['items'])
                if not data['items']:lines.append('- Geen ongelezen berichten gevonden in dit zoekresultaat.')
            elif name=='weather':
                values=data['values'];units=data['units']
                lines.append(f"Weer {data['location']}: {values['temperature_2m']:g} {units['temperature_2m']}, neerslag {values['precipitation']:g} {units['precipitation']}, wind {values['wind_speed_10m']:g} {units['wind_speed_10m']} (Open-Meteo, {data['observed_at']})."+(' Bron is verouderd; ophalen mislukt.' if data.get('stale') else ''))
            elif name=='traffic':
                lines.append('Verkeer rond '+data['location']+' (NDW): '+('; '.join(item['text'] for item in data['items'][:3]) if data['items'] else 'geen ontvangen meldingen binnen 25 kilometer')+'. Geen routevertraging berekend.'+(' Eerdere update; verversen lukte niet.' if data.get('stale') else ''))
            else:
                lines.append('NOS-nieuwskoppen (geen geverifieerde noodmeldingen):')
                lines.extend('- '+item['title'] for item in data['items'][:2])
        if not calls:lines.append('Er zijn geen bronnen ingeschakeld. Kies de gewenste briefingbronnen in Instellingen.')
        return {'kind':kind,'at':now.isoformat(),'text':'\n'.join(lines)[:3000],
                'sources':{key:{'status':value['status']} for key,value in sources.items()},'user_id':user,
                'references':{key:value['data'].get('items',[]) for key,value in sources.items() if key in ('calendar','email') and value['status']=='available'}}

    def schedule(self,principal):
        self.engine.permissions.check(principal.device_id,'automation:write')
        self.engine.permissions.check(principal.device_id,'automation:read')
        document=self.natural.settings.get(principal);settings=document['settings'];config=settings['briefings']
        if not config['enabled']:raise ValueError('Schakel geplande briefings eerst in')
        zone=settings['general']['timezone'];now=datetime.fromtimestamp(self.engine.store.clock(),ZoneInfo(zone))
        result={'scheduled':[],'blocked':[],'scheduler_enabled':self.natural.chat.settings.automations_enabled}
        signature=self.signature(settings)
        for kind in ('morning','evening'):
            if config[kind+'_channel']=='call':
                result['blocked'].append({'kind':kind,'reason':'Er is geen ondersteund oproepkanaal geconfigureerd; er is niet gebeld en geen beltaak ingepland.'});continue
            hour,minute=map(int,config[kind].split(':'));at=now.replace(hour=hour,minute=minute,second=0,microsecond=0)
            if at<=now:at+=timedelta(days=1)
            while at.astimezone(ZoneInfo('UTC')).astimezone(ZoneInfo(zone)).replace(tzinfo=None)!=at.replace(tzinfo=None):at+=timedelta(days=1)
            key=str(uuid.uuid5(uuid.NAMESPACE_URL,'briefing:'+str(principal.device_id)+':'+kind+':'+signature))
            row=self.engine.submit(principal.device_id,'PersonalBriefing',{'kind':kind,'config_hash':signature},key,at.timestamp(),'daily',zone)
            result['scheduled'].append({'kind':kind,'id':row['id'],'status':row['status'],'due':row['due']})
        return result

    def schedule_events(self):
        with self.engine.store.db() as db:
            rows=db.execute("SELECT e.* FROM natural_events e WHERE e.kind IN ('presence.return','presence.away') AND e.handled=0 AND e.expires>? ORDER BY e.created LIMIT 10",(self.engine.store.clock(),)).fetchall()
        for row in rows:
            handled=False
            try:
                user,settings=self.device(row['device_id'])
                if user!=row['user_id'] or not settings['briefings']['enabled'] or not settings['briefings']['on_return']:
                    handled=True;continue
                kind='prepare' if row['kind']=='presence.away' else 'return'
                self.engine.submit(row['device_id'],'PersonalBriefing',{'kind':kind,'config_hash':self.signature(settings),'source_event':row['id']},'briefing-event:'+row['id'])
                handled=True
            except (ValueError,PermissionError,AuthError):handled=True
            finally:
                if handled:
                    with self.engine.store.db(True) as db:db.execute('UPDATE natural_events SET handled=1 WHERE id=?',(row['id'],))

    async def execute(self,row,payload):
        user,settings=self.device(row['device_id'])
        if not settings['briefings']['enabled'] or payload['config_hash']!=self.signature(settings):raise ValueError('Briefinginstellingen gewijzigd; plan opnieuw')
        if payload['kind'] in ('morning','evening') and settings['briefings'][payload['kind']+'_channel']=='call':
            raise ValueError('Er is geen ondersteund oproepkanaal geconfigureerd')
        if payload['source_event']:
            with self.engine.store.db() as db:
                source=db.execute('SELECT id FROM natural_events WHERE id=? AND user_id=? AND device_id=?',(payload['source_event'],user,row['device_id'])).fetchone()
            if not source:raise ValueError('De bron van de terugkomstbriefing ontbreekt')
        bundle=None
        if payload['kind']=='return':
            with self.engine.store.db() as db:
                cached=db.execute("SELECT payload FROM natural_events WHERE user_id=? AND kind='briefing.prepared' AND created>? ORDER BY created DESC LIMIT 1",(user,self.engine.store.clock()-600)).fetchone()
            if cached:
                data=json.loads(cached['payload'])
                try:
                    if data.get('config_hash')!=payload['config_hash']:raise ValueError('Andere briefingconfiguratie')
                    for source,tool in (('calendar','CalendarRead'),('email','EmailRead')):
                        if data.get('sources',{}).get(source,{}).get('status')=='available':self.guard(row['device_id'],tool)
                    bundle={'text':data['text']+'\nVoorbereid tijdens uw afwezigheid; bronmoment hierboven vermeld.','at':data['at'],'sources':data['sources']}
                except (AuthError,ValueError,KeyError):pass
        if bundle is None:bundle=await self.build(row['device_id'],payload['kind'])
        kind='briefing.prepared' if payload['kind']=='prepare' else 'briefing.ready'
        with self.engine.store.db(True) as db:
            identifier=self.natural.events.publish(db,user,row['device_id'],kind,
                {'text':bundle['text'],'at':bundle['at'],'sources':bundle['sources'],'config_hash':payload['config_hash']},
                'briefing-result:'+row['id']+':'+str(row['due']),lifetime=3600)
        return {'prepared':True,'event_id':identifier,'sources':bundle['sources'],'called':False}

    async def answer(self,run):
        text=run.message.casefold();kind='evening' if 'avond' in text else 'return' if 'terugkomst' in text else 'morning'
        bundle=await self.build(run.principal.device_id,kind)
        self.natural.store.security.store.own_device(run.principal)
        chat=self.natural.chat.automation_chat
        if bundle['references'].get('calendar'):
            chat.remember(run,'events',[{'id':item['id'],'summary':item['title'],'start':item['start'],'end':item['end']} for item in bundle['references']['calendar']])
        if bundle['references'].get('email'):chat.remember(run,'messages',bundle['references']['email'])
        lead='Uw briefing staat klaar' if any(value['status']=='available' for value in bundle['sources'].values()) else 'Ik kon de ingeschakelde bronnen niet controleren'
        return address(lead,run.natural_context['settings'])+'\n\n'+bundle['text']
