"""Reviewed Dutch progress vocabulary. No model calls and no success assertions."""
import hashlib
import json
import re
import time
from collections import deque

GROUPS={
 'general':(
 'Een ogenblik','Ik kijk even','Ik bekijk uw vraag','Ik zoek het voor u uit',
 'Laat mij even kijken','Ik neem het door','Ik ga het na','Ik bekijk de mogelijkheden',
 'Ik ga ermee aan de slag','Ik zoek het zorgvuldig uit'),
 'calendar':(
 'Ik bekijk uw agenda','Ik controleer de tijden','Ik zoek een passend moment',
 'Ik kijk naar uw afspraken','Ik controleer de planning','Ik vergelijk de tijdstippen',
 'Ik bekijk de beschikbare ruimte','Ik ga de datum na','Ik controleer de afspraak',
 'Ik kijk wat er aansluit'),
 'email':(
 'Ik bekijk uw correspondentie','Ik neem de berichten door','Ik zoek de juiste e-mail',
 'Ik bekijk de afzender','Ik controleer het bericht','Ik ga de correspondentie na',
 'Ik lees het even zorgvuldig','Ik zoek de relevante berichten','Ik bekijk de eerdere reactie',
 'Ik controleer wat aandacht vraagt'),
 'weather':(
 'Ik bekijk het weer','Ik haal de verwachting op','Ik controleer de vooruitzichten',
 'Ik kijk naar de temperatuur','Ik bekijk de weersverwachting','Ik ga de neerslag na',
 'Ik raadpleeg de weerbron','Ik bekijk het lokale weer','Ik controleer de wind',
 'Ik kijk wat het weer brengt'),
 'news':(
 'Ik bekijk het nieuws','Ik haal de nieuwskoppen op','Ik raadpleeg de nieuwsbron',
 'Ik zoek de recente berichten','Ik bekijk de ontwikkelingen','Ik neem de koppen door',
 'Ik controleer de actualiteit','Ik zoek het laatste overzicht','Ik vergelijk de nieuwsberichten',
 'Ik bekijk wat relevant is'),
 'traffic':(
 'Ik bekijk het verkeer','Ik controleer de verkeersmeldingen','Ik raadpleeg de verkeersbron',
 'Ik bekijk de regionale hinder','Ik zoek de actuele meldingen','Ik ga de verkeerssituatie na',
 'Ik controleer de omgeving','Ik bekijk de bereikbaarheid','Ik zoek de verkeersinformatie',
 'Ik neem de verkeersmeldingen door'),
 'research':(
 'Ik onderzoek uw vraag','Ik vergelijk de bronnen','Ik zoek de relevante informatie',
 'Ik controleer de gegevens','Ik bekijk de achtergrond','Ik zoek een betrouwbare bron',
 'Ik onderzoek de mogelijkheden','Ik ga de details na','Ik vergelijk de informatie',
 'Ik neem de bevindingen door'),
 'planning':(
 'Ik bekijk uw wensen','Ik vergelijk de mogelijkheden','Ik zoek passende opties',
 'Ik zet de opties op een rij','Ik bekijk wat haalbaar is','Ik controleer de samenhang',
 'Ik onderzoek een passende indeling','Ik zoek een praktische oplossing','Ik weeg de opties af',
 'Ik bekijk de volgende stap'),
 'device':(
 'Ik controleer het apparaat','Ik bekijk de verbinding','Ik controleer de beschikbaarheid',
 'Ik raadpleeg uw apparaat','Ik bekijk de apparaatstatus','Ik ga de verbinding na',
 'Ik controleer het verzoek','Ik bekijk de beschikbare bediening','Ik controleer de uitvoering',
 'Ik wacht op het apparaat'),
 'memory':(
 'Ik zoek de relevante notitie','Ik bekijk uw voorkeuren','Ik raadpleeg uw notities',
 'Ik zoek het eerdere gesprek','Ik controleer de context','Ik bekijk wat u eerder aangaf',
 'Ik haal de relevante context erbij','Ik zoek de bijbehorende informatie','Ik ga uw voorkeur na',
 'Ik kijk het even terug'),
}
PHRASES={f'{kind}-{index:02}':{'id':f'{kind}-{index:02}','kind':kind,'text':text}
         for kind,phrases in GROUPS.items() for index,text in enumerate(phrases)}


def spoken(item,config):
    settings=config['progress'];personality=config['personality']
    name=personality['honorific'] if settings['honorific'] and personality['honorific_frequency']!='off' else ''
    return item['text']+(', '+name if name else '')+'.'


def voice_key(config,bootstrap):
    # A voice/model/speed/address change must never replay a previous voice.
    fields=('tts_provider','mode','elevenlabs_model','elevenlabs_stability','elevenlabs_similarity','elevenlabs_style','elevenlabs_speaker_boost','voice','speaker','speed','supertonic_voice','steps','pause_ms')
    voice={key:config['voice'][key] for key in fields}
    voice['elevenlabs_voice_id']=config['voice']['elevenlabs_voice_id'] or bootstrap.elevenlabs_voice_id
    voice['offline']=config['ai']['offline']
    return hashlib.sha256(json.dumps([voice,config['progress']['honorific'],config['personality']['honorific'],config['personality']['honorific_frequency']],sort_keys=True).encode()).hexdigest()[:32]


def category(message):
    for kind,pattern in [('calendar',r'\b(agenda|afspraak|verplaats)\b'),('email',r'\b(mail|bericht|correspondentie)\b'),
       ('weather',r'\b(weer|temperatuur|regent)\b'),('news',r'\bnieuws\b'),('traffic',r'\b(verkeer|files|file)\b'),
       ('device',r'\b(computer|apparaat|programma)\b'),('memory',r'\b(onthoud|herinner|voorkeur)\b'),
       ('planning',r'\b(plan|uitjes|mogelijkheden)\b'),('research',r'\b(onderzoek|zoek|vergelijk)\b')]:
        if re.search(pattern,message,re.I):return kind
    return 'general'


class Selector:
    def __init__(self,clock=time.monotonic):self.clock=clock;self.history={}

    def choose(self,key,kind,available,config):
        settings=config['progress'];now=self.clock()
        if not settings['enabled']:return None
        recent=self.history.get(key,deque(maxlen=20))
        if recent and now-recent[-1][1]<settings['minimum_interval_seconds']:return None
        used={item[0] for item in recent}
        choices=[name for name in available if PHRASES.get(name,{}).get('kind')==kind and name not in used]
        if not choices:choices=[name for name in available if name.startswith('general-') and name not in used]
        if not choices:return None
        identifier=sorted(choices)[0];recent.append((identifier,now))
        if len(self.history)>=100 and key not in self.history:self.history.pop(next(iter(self.history)))
        self.history[key]=recent
        return identifier
