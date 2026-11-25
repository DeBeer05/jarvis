"""One response policy for prompts, verified tool summaries and spoken output."""
import re
import time
from copy import deepcopy
from contextlib import aclosing
from providers.speech_format import format_speech

FULL=re.compile(r'\b(?:lees (?:de |het )?(?:volledige|hele|alles)|alle details|geef alles|volledige (?:mail|tekst|antwoord)|letterlijk)\b',re.I)
MORE=re.compile(r'\s*(?:vertel meer|leg dat verder uit|wat bedoel je|wat staat er precies|lees alles voor|geef alle details|maak het korter|vat dat samen|alleen de belangrijkste informatie|wat moet ik hiervan weten)[?.!\s]*',re.I)
CRITICAL=re.compile(r'\b(?:urgent|deadline|uiterlijk|vóór|voor \d|vervalt|conflict|waarschuwing|gevaar|mislukt|fout|onzeker|mogelijk|niet bevestigd|onvolledig|ingekort|eerste resultaten|maximaal vijf|toestemming|goedkeur|betaal|kosten|boete)\w*',re.I)
RESPONSE_PROFILES={'auto':{},'daily':{'mode':'auto','spoken':'short','written':'balanced','technical_detail':40,'background':20},'technical':{'mode':'auto','spoken':'balanced','written':'extended','technical_detail':85,'background':60},'briefing':{'mode':'auto','spoken':'short','written':'balanced','technical_detail':30,'background':10,'followup_questions':0},'custom':{}}
MODES={'ultrashort':'Eén directe zin wanneer veilig en voldoende.','short':'Gewoonlijk één tot drie natuurlijke zinnen.','balanced':'Direct antwoord met relevante toelichting.','extended':'Geef meer achtergrond en noodzakelijke technische details.','full':'Geef de volledige beschikbare relevante informatie; benoem beperkingen.','auto':'Kies een passende lengte; geef bij spraak gewoonlijk één tot drie zinnen.'}


def mode_for(config,message,voice):
    if FULL.search(message):return 'full'
    if re.search(r'korter|vat.*samen|alleen de belangrijkste',message,re.I):return 'short'
    if re.search(r'leg.*(?:uitgebreid|verder) uit|vertel meer|alle details',message,re.I):return 'extended'
    if config['responses']['technical_detail']>=70 and re.search(r'\b(?:server|python|code|api|ollama|hardware|database|technisch)\b',message,re.I):return 'extended'
    mode=config['responses']['mode']
    return config['responses']['spoken' if voice else 'written'] if mode=='auto' else mode


def response_prompt(config,message,voice):
    mode=mode_for(config,message,voice);personality=config['personality'];options=config['responses']
    text=' Reageer passend op het gesprek; geef bij een vraag eerst het antwoord. '+MODES[mode]
    text+=' Een verhaal, grap of gedachte vraagt een inhoudelijke reactie, geen automatische samenvatting, taak of vervolgvraag. '
    text+=' Behoud deadlines, waarschuwingen, onzekerheid, conflicten, financiële gevolgen en noodzakelijke acties. Een korte stijl mag die nooit verbergen. Bevestig alleen door de backend bewezen acties. '
    if options['summaries']:text+='Verwerk informatie tot een relevant antwoord; lees niet standaard ruwe toolgegevens, e-mails of documenten voor. '
    if options['progressive'] and mode not in ('full','extended'):text+='Begin met de kern; bewaar verwijzingen voor betrouwbare vervolgvragen. '
    if options['details_on_request'] and mode not in ('full','extended'):text+='Geef uitgebreide achtergrond pas op verzoek. '
    for category,label in (('email','e-mails'),('calendar','agendagegevens'),('news','nieuws'),('messages','berichten')):
        if options[category]:text+='Vat '+label+' samen voordat je ze presenteert, behalve bij expliciet volledig voorlezen. '
    if options['avoid_repetition']:text+='Vermijd herhaling van eerdere uitleg en vaste begroetingen of afsluitvragen. '
    text+=f"Technisch detailniveau {options['technical_detail']}/100, achtergrond {options['background']}/100, nuttige vervolgvragen {options['followup_questions']}/100. "
    if voice:text+='Schrijf natuurlijke Nederlandse spreektaal zonder Markdown, JSON, technische metadata of lange URL’s. '
    if personality['profile']=='classic_butler':text+='Je bent een rustige, professionele, elegante Nederlandse persoonlijke butler, met subtiele droge humor. Geen imitatie van een specifieke acteur. '
    if personality['honorific_frequency']=='off' or not personality['honorific']:text+='Gebruik geen aanspreekvorm als meneer. '
    else:text+='Gebruik de ingestelde aanspreekvorm hooguit af en toe, nooit in iedere zin. '
    return text


def sentences(text):return [part.strip() for part in re.split(r'(?<=[.!?])\s+|\n+',text) if part.strip()]


def extractive(text,mode):
    parts=sentences(text)
    if mode in ('full','extended') or len(parts)<=3:return text
    selected=set(range(1 if mode=='ultrashort' else 2))
    selected.update(index for index,part in enumerate(parts) if CRITICAL.search(part))
    return ' '.join(part for index,part in enumerate(parts) if index in selected)


class IntelligentResponseManager:
    def __init__(self,natural):self.natural=natural;self.temporary={}

    @staticmethod
    def preference(message,config):
        text=re.sub(r"^jarvis[, ]+","",message.strip(),flags=re.I).rstrip('.!?').casefold()
        permanent=bool(re.search(r"\b(?:voortaan|permanent|vanaf nu)\b",text))
        text=re.sub(r"\b(?:voortaan|permanent|vanaf nu|voor dit gesprek|deze keer)\b","",text)
        text=' '.join(text.split())
        rules={
            'geef kortere antwoorden':{'responses':{'mode':'short'}},
            'je hoeft niet alles voor te lezen':{'responses':{'spoken':'short','mode':'auto','summaries':True}},
            'vat mijn e-mails samen':{'responses':{'email':True,'summaries':True}},
            'geef bij technische vragen meer uitleg':{'responses':{'technical_detail':80}},
            'je hoeft me geen meneer te noemen':{'personality':{'honorific':'','honorific_frequency':'off'}},
            'schakel over naar offline spraak':{'voice':{'mode':'offline','tts_provider':'auto'}},
            'gebruik de classic butler-stem':{'voice':{'profile':'classic_butler','mode':'automatic','tts_provider':'auto','speed':.95},'personality':{'profile':'classic_butler'}},
            'gebruik de classic butler stem':{'voice':{'profile':'classic_butler','mode':'automatic','tts_provider':'auto','speed':.95},'personality':{'profile':'classic_butler'}},
        }
        if text in ('praat iets langzamer','praat langzamer'):return {'voice':{'speed':max(.7,round(config['voice']['speed']-.05,2))}},permanent
        if text in ('praat iets sneller','praat sneller'):return {'voice':{'speed':min(1.5,round(config['voice']['speed']+.05,2))}},permanent
        if text in ('gebruik wat minder sarcasme','gebruik minder sarcasme'):return {'personality':{'sarcasm':max(0,config['personality']['sarcasm']-10)}},permanent
        if text=='gebruik een diepere stem':return {'unsupported':{}},False
        return (rules[text],permanent) if text in rules else None

    def apply(self,principal,conversation,config):
        now=time.monotonic();self.temporary={key:value for key,value in self.temporary.items() if now-value[0]<1800}
        changes=self.temporary.get((principal.session_id,principal.device_id,conversation),(0,{}))[1]
        result=deepcopy(config)
        for category,values in changes.items():result[category].update(values)
        return result

    def command(self,run):
        document=self.natural.settings.get(run.principal);config=self.apply(run.principal,run.conversation_id,document['settings'])
        preference=self.preference(run.message,config)
        if preference is None:return None
        changes,permanent=preference
        if 'unsupported' in changes:return 'Deze lokale stemmen ondersteunen geen toonhoogteregelaar. Vergelijk de mannenstemmen in Voice Studio om een diepere stem te kiezen.'
        if 'personality' in changes and 'profile' in changes['personality']:
            from server.natural.personality import PROFILES
            values=changes['personality'];changes['personality']={**PROFILES[values['profile']][1],**values}
        if 'voice' in changes and 'profile' in changes['voice']:
            from server.natural.tts import PROFILES as VOICE_PROFILES
            values=changes['voice'];changes['voice']={**VOICE_PROFILES[values['profile']],**values}
        # The only writable values are from the closed, deterministic parser above.
        key=(run.principal.session_id,run.principal.device_id,run.conversation_id)
        if permanent:
            data=deepcopy(document['settings'])
            for category,values in changes.items():data[category].update(values)
            self.natural.settings.replace(run.principal,data,document['revision'])
            self.temporary.pop(key,None)
            return 'Ik heb die voorkeur opgeslagen.'
        from server.natural.models import UserSettings
        previous=self.temporary.get(key,(0,{}))[1];combined=deepcopy(previous)
        data=deepcopy(document['settings'])
        for category,values in changes.items():combined.setdefault(category,{}).update(values)
        for category,values in combined.items():data[category].update(values)
        UserSettings.model_validate(data)
        if len(self.temporary)>=100:self.temporary.pop(next(iter(self.temporary)))
        self.temporary[key]=(time.monotonic(),combined)
        return 'Dat pas ik tijdelijk toe in dit gesprek. Zeg voortaan om de voorkeur blijvend op te slaan.'


    def summarize(self,run,text):
        config=run.natural_context['settings'];mode=mode_for(config,run.message,True);data=run.response_data
        if mode in ('full','extended') or not config['responses']['summaries'] or run.wait_state is not None:return text
        from server.natural.intents import compound_candidate
        if compound_candidate(run.message):return text
        if data and data['tool']=='EmailDigest':return text
        if data and data['tool']=='CalendarRead' and config['responses']['calendar']:
            events=data['items']
            if not events:return text
            if re.search(r'welke afspraken|noem.*afspraken|som.*op',run.message,re.I):return text
            first=events[0];zone=config['general']['timezone']
            when=self.natural.chat.automation_chat.when(first.get('start',{}),zone)
            result=f"Je hebt {len(events)} afspraken in de opgevraagde periode. De eerste is {first.get('summary','een afspraak')} om {when}."
            # Never claim free time or travel time without a complete reliable query.
            from datetime import datetime
            try:
                windows=sorted((datetime.fromisoformat(e['start']['dateTime'].replace('Z','+00:00')),datetime.fromisoformat(e['end']['dateTime'].replace('Z','+00:00'))) for e in events)
                if any(a[1]>b[0] for a,b in zip(windows,windows[1:])):result+=' Let op: er overlappen afspraken.'
            except (KeyError,ValueError,TypeError):pass
            critical=[e.get('summary','') for e in events[1:] if CRITICAL.search(e.get('summary',''))]
            if critical:result+=' Let ook op: '+ '; '.join(critical)+'.'
        elif data and data['tool']=='CalendarRead':return text
        elif data and data['tool']=='EmailSearch' and config['responses']['email']:
            items=data['items']
            if not items:return text
            important=[item['subject'] for item in items if re.search(r'sollicitat|uitnodiging|bevestig|deadline|urgent|factuur|afspraak|reactie',item['subject'],re.I)]
            result=f"Ik heb {len(items)} berichten opgehaald; dit is geen telling van alle nieuwe mail. "
            result+=('Aan de onderwerpen te zien verdienen deze aandacht: '+ '; '.join(important)+'. De inhoud is nog niet gelezen.' if important else 'Op basis van alleen de onderwerpen kan ik het belang niet zeker bepalen. Vraag naar een bericht om de inhoud te lezen.')
        elif data and data['tool']=='EmailSearch':return text
        elif data and data['tool']=='EmailRead' and config['responses']['email'] and data.get('body'):
            result=extractive(data['body'],mode)
        elif data and data['tool']=='EmailRead':return text
        else:return extractive(text,mode)
        limitations=[line for line in text.splitlines() if re.search(r'onvolledig|eerste resultaten|maximaal vijf|ingekort',line,re.I)]
        return result+(' '+' '.join(limitations) if limitations else '')

    async def stream(self,run,source,tool=False):
        pending='';original=''
        async with aclosing(source) as stream:
            async for event in stream:
                yield event
                if event['type']!='delta':continue
                original+=event['text']
                if tool and not run.conversational_reply:continue
                pending+=event['text']
                while (match:=re.search(r'[.!?](?:\s+|$)',pending)) and match.end()<len(pending):
                    if pending.lstrip().startswith(('{','[','<')) or pending[:match.end()].count('```')%2:break
                    part,pending=pending[:match.end()],pending[match.end():]
                    spoken=format_speech(part,run.natural_context["settings"]["general"]["timezone"])
                    if spoken:run.speech_message+=spoken+' ';yield {'type':'speech','text':spoken+' '}
        if tool and not run.conversational_reply:pending=self.summarize(run,original)
        spoken=format_speech(pending,run.natural_context["settings"]["general"]["timezone"])
        if spoken:run.speech_message+=spoken;yield {'type':'speech','text':spoken}
