"""Direct authorized public reads; a topic change cannot approve an older action."""
import re
import time

import httpx

from server.natural.presence import address
from server.security.types import AuthError

REQUEST=re.compile(r'^(?:jarvis[, ]+)?(?:en\s+)?(?:hoe|wat|welk\w*|is|wordt|gaat|regent|staan|zijn|geef|toon|vertel|bekijk|haal|kun|kan|wil|wilt|ik wil|het weer|weer\b|weerbericht|weersverwachting|nieuws)',re.I)


class PublicReads:
    def __init__(self,natural):self.natural=natural

    def parse(self,run):
        text=run.message.strip().rstrip('.!?')
        from server.natural.calendar_dialogue import creating
        if creating(text) or re.match(r'ik wil (?:niet|geen)\b',text,re.I):return None
        if REQUEST.match(text):
            if re.search(r'\b(?:het weer|weerbericht|weersverwachting|temperatuur|regent|regenen)\b',text,re.I) or re.fullmatch(r'(?:en )?weer(?: (?:vandaag|morgen|overmorgen))?',text,re.I):kind='WeatherRead'
            elif re.search(r'\bnieuws(?:koppen|berichten)?\b',text,re.I):kind='NewsRead'
            elif re.search(r'\b(?:verkeersinformatie|verkeersdrukte|het verkeer|files)\b',text,re.I):kind='TrafficRead'
            else:return None
            match=re.search(r'\b(?:in|rond|voor)\s+(.+?)(?:\s+(?:vandaag|morgen|overmorgen))?$',text,re.I)
            location=match[1].strip() if match else ''
            if re.fullmatch(r'(?:mijn|deze|de)\s+(?:omgeving|regio|buurt)',location,re.I):location=''
            return kind,{'location':location,'offset':2 if re.search(r'\bovermorgen\b',text,re.I) else 1 if re.search(r'\bmorgen\b',text,re.I) else 0}
        memory:dict=getattr(self.natural.chat.automation_chat,"memory",lambda run:{})(run)
        question=(memory.get('public_question') or [{}])[0]
        if question.get('expires',0)>time.time() and re.fullmatch(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ '\-]{1,99}",text) and not re.match(r'^(?:ja|nee|akkoord|ik|dat|het|een|maak|zet|wil|kun|kan|hoe|wat|vertel|hallo|hoi|bedankt|goedemorgen|goedenavond)\b',text,re.I):
            return question.get('kind','WeatherRead'),{'location':text,'offset':question.get('offset',0)}
        return None

    async def answer(self,run,parsed):
        n=self.natural;c=n.chat.automation_chat;kind,payload=parsed;config=run.natural_context['settings']
        # The job remains available in Tasks; casual 'ja' after a topic change
        # no longer points to an older calendar/mail proposal or result.
        c.remember_many(run,{**{field:[] for field in ('pending','decision','write_question','read_question','calendar_action','public_question')},'recent':[{'kind':'public','source':kind}]})
        started=time.perf_counter()
        try:
            n.settings.get(run.principal);n.briefings.guard(run.principal.device_id,kind)
            if config['ai']['offline']:return address('Offline kan ik geen actuele bron ophalen',config)
            if kind in ('WeatherRead','TrafficRead'):
                place=payload['location'] or config['briefings']['location']
                if not place:
                    c.remember(run,'public_question',[{'expires':time.time()+120,'offset':payload['offset'],'kind':kind}])
                    return address('Voor welke plaats wilt u het weer weten?' if kind=='WeatherRead' else 'Voor welke plaats wilt u de verkeersinformatie weten?',config)
                if kind=='TrafficRead':
                    data=await n.briefings.sources.traffic(place);n.briefings.guard(run.principal.device_id,kind)
                    text='NDW meldt rond '+data['location']+': '+('; '.join(item['text']+' op circa '+str(item['distance_km'])+' km' for item in data['items'][:3]) if data['items'] else 'geen meldingen binnen 25 kilometer')+'. Dit is regionale hinder; een vertraging op uw route is hiermee niet berekend.'
                    if data.get('stale'):text+=' Dit is een eerdere update; verversen lukte niet.'
                    return address(text,config)
                if payload['offset']:data=await n.briefings.sources.weather(place,'Europe/Amsterdam',offset=payload['offset'])
                else:data=await n.briefings.sources.weather(place,'Europe/Amsterdam')
                n.briefings.guard(run.principal.device_id,kind)
                values=data['values'];units=data['units']
                when=('Op dit moment','Morgen','Overmorgen')[payload['offset']]
                temperature=f"{values['minimum']:g} tot {values['temperature_2m']:g}" if data.get('forecast') else f"{values['temperature_2m']:g}"
                text=f"{when} in {data['location']}: {temperature} graden, {values['precipitation']:g} {units['precipitation']} neerslag en wind van {values['wind_speed_10m']:g} {units['wind_speed_10m']}."
                if data.get('stale'):text+=' Dit is een eerdere waarneming; verversen lukte niet.'
            else:
                data=await n.briefings.sources.news();n.briefings.guard(run.principal.device_id,kind)
                text='De laatste nieuwskoppen:\n'+'\n'.join('• '+n.chat.store.clean(item['title']) for item in data['items'][:3])
                if data.get('stale'):text+='\nDit is een eerdere update; verversen lukte niet.'
            return address(text,config)
        except AuthError:raise
        except (ValueError,KeyError,TypeError,httpx.HTTPError):return address('De actuele bron is niet betrouwbaar bereikbaar. Ik heb geen gegevens ingevuld',config)

        finally:run.timings['source_fetch_ms']=(time.perf_counter()-started)*1000
