"""Explicit modes and opt-in presence transitions, without inferred permissions."""
import json
import re
from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import Field
from server.natural.models import StrictModel
from server.natural.store import encode

MODES={'normal':'Normaal','work':'Werk','gaming':'Gaming','away':'Afwezig',
       'sleeping':'Slapen','travelling':'Onderweg','private':'Privé','emergency':'Noodgeval'}
ABSENT={'away','sleeping','travelling'}
SIGNAL_TTL=120
MODE_COMMAND=re.compile(r'(?:zet|schakel) (?:mij |jarvis |de )?(?:in )?(normaal|normale|werk|gaming|afwezig|slapen|onderweg|privé|prive|noodgeval)(?:e)?(?: ?modus)?(?: aan| in)?[.!]*',re.I)


def address(text,settings):
    personality=settings['personality']
    honorific=personality['honorific'] if personality['honorific_frequency']!='off' else ''
    return text+(', '+honorific if honorific else '')+'.'


class Signal(StrictModel):
    sequence:int=Field(ge=1,le=2147483647)
    locked:bool=False
    idle_seconds:int=Field(default=0,ge=0,le=86400)
    hint:str=Field(default='normal',pattern=r'^(normal|work|gaming|travelling)$')


def migrate(db):
    db.execute('''CREATE TABLE IF NOT EXISTS natural_presence(
        user_id INTEGER PRIMARY KEY,mode TEXT NOT NULL,reason TEXT NOT NULL,
        revision INTEGER NOT NULL,updated REAL NOT NULL,away_since REAL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS natural_presence_devices(
        user_id INTEGER NOT NULL,device_id TEXT NOT NULL,sequence INTEGER NOT NULL,
        sample TEXT NOT NULL,updated REAL NOT NULL,PRIMARY KEY(user_id,device_id))''')


def allowed_notification(mode,category):
    if category=='urgent':return True
    if mode in ('away','sleeping','private','gaming','emergency'):return False
    return category in ('important','appointments') if mode in ('work','travelling') else True


class PresenceManager:
    def __init__(self,natural):
        self.natural=natural;self.store=natural.store

    def _mode(self,db,user,settings):
        config=settings['presence'];manual=config['mode'];now=self.store.clock()
        if not config['automatic'] or manual in ('private','emergency'):
            return manual,'manual'
        rows=db.execute('''SELECT p.sample,s.payload FROM natural_presence_devices p
            JOIN auth_devices d ON d.id=p.device_id AND d.user_id=p.user_id AND d.revoked_at IS NULL
            JOIN natural_settings s ON s.user_id=p.user_id AND s.scope='device' AND s.device_id=p.device_id
            WHERE p.user_id=? AND p.updated>? ORDER BY p.updated DESC''',(user,now-SIGNAL_TTL)).fetchall()
        known=[]
        for row in rows:
            device=json.loads(row['payload'])
            if not device.get('presence_allowed'):continue
            value=json.loads(row['sample']);known.append(value)
            if not value['locked'] and value['idle_seconds']<config['idle_seconds']:
                hint=value['hint'] if device.get('application_allowed') else 'normal'
                return hint,'device'
        if not known:
            if not db.execute('SELECT 1 FROM natural_presence_devices WHERE user_id=? LIMIT 1',(user,)).fetchone():
                return manual,'unknown'
            return 'away','unavailable'
        hour=datetime.fromtimestamp(now,ZoneInfo(settings['general']['timezone'])).hour
        start,end=config['sleep_start'],config['sleep_end']
        night=(start<=hour<end if start<end else hour>=start or hour<end) if start!=end else False
        return ('sleeping','schedule') if config['sleep_schedule'] and night else ('away','idle')

    def _transition(self,db,user,device,settings,mode,reason,*,notify=True):
        now=self.store.clock()
        old=db.execute('SELECT * FROM natural_presence WHERE user_id=?',(user,)).fetchone()
        revision=old['revision'] if old else 0
        changed=not old or old['mode']!=mode
        returned=bool(old and old['mode'] in ABSENT and mode not in ABSENT|{'private','emergency'})
        greeting=None
        if changed:
            revision+=1
            away=old['away_since'] if old and old['mode'] in ABSENT and mode in ABSENT else now if mode in ABSENT else None
            db.execute('INSERT INTO natural_presence VALUES (?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET mode=excluded.mode,reason=excluded.reason,revision=excluded.revision,updated=excluded.updated,away_since=excluded.away_since',
                       (user,mode,reason,revision,now,away))
            self.store.audit(db,user,device,'presence_transition',mode)
            if returned and settings['presence']['greetings']:
                greeting=address('Welkom terug',settings)
                if old['reason']=='meal':greeting+=' Ik hoop dat het u gesmaakt heeft.'
                notification=settings['notifications']
                recent=db.execute('SELECT count(*) FROM natural_events WHERE user_id=? AND created>? AND priority<2',(user,now-3600)).fetchone()[0]
                if notify and notification['enabled'] and notification['proactivity']!='off' and recent<notification['suggestions_per_hour']:
                    self.natural.events.publish(db,user,device,'presence.return',
                        {'text':greeting,'away_since':old['away_since'],'source':'presence_transition'},
                        'return:'+str(revision),lifetime=300)
        return {'mode':mode,'label':MODES[mode],'reason':reason,'revision':revision,
                'changed':changed,'greeting':greeting,'private':mode=='private'}

    def snapshot(self,principal,settings=None,*,notify=True):
        settings=settings or self.natural.settings.get(principal)['settings']
        with self.store.transaction(principal,write=True) as (db,user):
            mode,reason=self._mode(db,user,settings)
            return self._transition(db,user,principal.device_id,settings,mode,reason,notify=notify)

    def signal(self,principal,value):
        value=Signal.model_validate(value)
        settings=self.natural.settings.get(principal)['settings']
        device=self.natural.settings.get(principal,'device')['settings']
        if not device['presence_allowed'] or settings['presence']['mode']=='private':raise PermissionError('Aanwezigheid delen is uitgeschakeld of privé')
        if value.hint!='normal' and not device['application_allowed']:raise PermissionError('Applicatie-/activiteitsherkenning is niet toegestaan')
        with self.store.transaction(principal,write=True) as (db,user):
            previous=db.execute('SELECT sequence FROM natural_presence_devices WHERE user_id=? AND device_id=?',(user,principal.device_id)).fetchone()
            if not previous or value.sequence>previous['sequence']:
                db.execute('INSERT INTO natural_presence_devices VALUES (?,?,?,?,?) ON CONFLICT(user_id,device_id) DO UPDATE SET sequence=excluded.sequence,sample=excluded.sample,updated=excluded.updated',
                           (user,principal.device_id,value.sequence,encode(value.model_dump()),self.store.clock()))
            mode,reason=self._mode(db,user,settings)
            result=self._transition(db,user,principal.device_id,settings,mode,reason)
            result['sequence']=max(value.sequence,previous['sequence'] if previous else 0)
            return result

    def state(self,principal):
        result=self.snapshot(principal)
        with self.store.transaction(principal) as (db,user):
            row=db.execute('SELECT sequence FROM natural_presence_devices WHERE user_id=? AND device_id=?',(user,principal.device_id)).fetchone()
        result['sequence']=row['sequence'] if row else 0
        return result

    def runtime(self,principal,document):
        state=self.snapshot(principal,document['settings'])
        if not state['private']:
            if state['mode']==document['settings']['presence']['mode']:return document
            result=deepcopy(document);result['settings']['presence']['mode']=state['mode']
            return result
        result=deepcopy(document);result['revision']=max(1,result['revision'])
        settings=result['settings']
        settings['memory'].update(history=False,long_term=False,automatic=False,summaries=False)
        settings['privacy']['cloud_memories']=False
        settings['ai'].update(offline=True,provider='ollama',fallback='none')
        settings['voice']['mode']='offline'
        return result

    def set_mode(self,principal,mode,*,reason='manual',notify=True):
        if mode not in MODES:raise ValueError('Onbekende modus')
        document=self.natural.settings.get(principal)
        # Capture the previous effective mode before changing the explicit setting.
        self.snapshot(principal,document['settings'],notify=False)
        saved=self.natural.settings.patch(principal,'presence',{'mode':mode,'automatic':False},document['revision'])
        with self.store.transaction(principal,write=True) as (db,user):
            return self._transition(db,user,principal.device_id,saved['settings'],mode,reason,notify=notify)

    @staticmethod
    def intent(message):
        text=re.sub(r'^jarvis[, ]+','',message.strip(),flags=re.I)
        simple={'ik ga eten':('away','meal'),'ik ga nu eten':('away','meal'),
                'ik ga slapen':('sleeping','sleep'),'ik ga nu slapen':('sleeping','sleep'),
                'ik ben terug':('normal','return'),'ik ben weer terug':('normal','return')}
        normalized=text.casefold().rstrip('.!')
        if normalized in simple:return simple[normalized]
        match=MODE_COMMAND.fullmatch(text)
        if not match:return None
        labels={label.casefold():key for key,label in MODES.items()}
        labels.update(normale='normal',prive='private')
        return labels[match[1].casefold()],'manual'

    def command(self,run):
        intent=self.intent(run.message)
        if intent is None:return None
        mode,reason=intent
        state=self.set_mode(run.principal,mode,reason=reason,notify=False)
        settings=self.natural.settings.get(run.principal)['settings']
        if state['greeting']:return state['greeting']
        if reason=='meal':return address('Eet smakelijk',settings)
        if reason=='sleep':return address('Welterusten',settings)
        return address('Ik ben er' if reason=='return' else MODES[mode]+' is ingeschakeld',settings)
