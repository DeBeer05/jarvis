"""Owner-scoped, voice-bound prerecorded WAVs. GET never synthesizes audio."""
import asyncio
import base64
import hashlib
import io
import os
import time
import wave

from server.natural.progress_phrases import PHRASES,Selector,category,spoken,voice_key
from server.security.types import AuthError


class ProgressAudio:
    def __init__(self,natural):
        self.natural=natural;self.selector=Selector();self.lock=asyncio.Lock()
        self.root=natural.chat.settings.database_path.parent/'progress-audio'

    def location(self,principal,config):
        with self.natural.store.transaction(principal) as (db,user):pass
        return self.root/str(user)/voice_key(config,self.natural.chat.settings)

    @staticmethod
    def validate(raw):
        if not 44<=len(raw)<=800000:raise ValueError('Ongeldige cacheaudio')
        with wave.open(io.BytesIO(raw)) as wav:
            if wav.getnchannels()!=1 or wav.getsampwidth()!=2 or not 8000<=wav.getframerate()<=48000 or wav.getnframes()>48000*8:
                raise ValueError('Ongeldig cacheformaat')
        return raw

    def manifest(self,principal,config):
        directory=self.location(principal,config);entries=[]
        for name,item in PHRASES.items():
            path=directory/(name+'.wav')
            if not path.is_file() or path.is_symlink():continue
            try:raw=self.validate(path.read_bytes())
            except (OSError,ValueError,wave.Error):continue
            entries.append({'id':name,'kind':item['kind'],'text':spoken(item,config),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
        return {'version':directory.name,'items':entries,'catalogue_count':len(PHRASES),'total_characters':sum(len(spoken(item,config)) for item in PHRASES.values())}

    def read(self,principal,config,identifier):
        if identifier not in PHRASES:raise AuthError('not_found','Deze tussenzin bestaat niet.',404)
        path=self.location(principal,config)/(identifier+'.wav')
        if path.is_symlink() or not path.is_file():raise AuthError('not_found','Deze opname is nog niet voorbereid.',404)
        try:return self.validate(path.read_bytes())
        except (OSError,ValueError,wave.Error):raise AuthError('speech_unavailable','De opname is niet leesbaar.',503) from None

    async def prepare(self,request,*,one_time_credits=0):
        if self.lock.locked():raise AuthError('speech_busy','Er wordt al een stemcache voorbereid.',429)
        async with self.lock:
            n=self.natural;principal=request.state.principal
            config=(await asyncio.to_thread(n.settings.runtime,principal))['settings']
            if one_time_credits:
                if config['ai']['offline'] or config['voice']['mode'] in ('offline','local'):raise AuthError('tts_private','Offline wordt geen premium voorbereidingsbudget gebruikt.',409)
                if 'admin:account' not in principal.permissions:raise AuthError('permission_denied','Een eenmalig extra budget vereist eigenaarstoestemming.',403)
                # Explicit one-off owner allowance; global settings remain unchanged.
                counts=await asyncio.to_thread(n.tts.usage.usage,principal,config)
                config['voice']['elevenlabs_daily_limit']=min(1000000,counts['daily_reserved_credits']+one_time_credits)
            manifest=await asyncio.to_thread(self.manifest,principal,config)
            known={item['id'] for item in manifest['items']}
            directory=self.location(principal,config);directory.mkdir(parents=True,exist_ok=True)
            baseline=(await asyncio.to_thread(n.tts.usage.usage,principal,config))['monthly_reserved_credits']
            for identifier,item in PHRASES.items():
                if await request.is_disconnected():return
                if identifier in known:continue
                current=(await asyncio.to_thread(n.settings.runtime,principal))['settings']
                if voice_key(current,n.chat.settings)!=directory.name:raise AuthError('speech_cancelled','Uw steminstellingen zijn gewijzigd; voorbereiding gestopt.',409)
                text=spoken(item,config)
                if one_time_credits:
                    counts=await asyncio.to_thread(n.tts.usage.usage,principal,config)
                    metadata=await n.tts.providers['elevenlabs'].inspect()
                    multiplier=next((m['reserve_multiplier'] for m in metadata['models'] if m['id']==config['voice']['elevenlabs_model']),1)
                    if counts['monthly_reserved_credits']-baseline+len(text)*multiplier>one_time_credits:
                        raise AuthError('tts_budget','Het eenmalige voorbereidingsbudget is bereikt.',429)
                result=await n.tts.synthesize(request,text,config)
                selected=result.get('selected_provider')
                from server.natural.capabilities import voice_capabilities
                caps=voice_capabilities();caps['elevenlabs_ready']=bool(n.chat.settings.elevenlabs_api_key)
                expected=n.tts.select(config,caps)
                if selected!=expected:raise AuthError('speech_unavailable','De gekozen stem is niet beschikbaar; er wordt geen andere stem gecachet.',503)
                raw=self.validate(base64.b64decode(result['audio'],validate=True))
                target=directory/(identifier+'.wav');temporary=target.with_suffix('.pending')
                with temporary.open('wb') as file:file.write(raw)
                if os.name!='nt':temporary.chmod(0o600)
                temporary.replace(target);known.add(identifier)
                yield {'id':identifier,'prepared':len(known),'total':len(PHRASES),'at':time.time()}

    def choose(self,run):
        config=run.natural_context['settings']
        if not config['progress']['enabled']:return None
        manifest=self.manifest(run.principal,config)
        identifier=self.selector.choose((run.principal.device_id,run.conversation_id),category(run.message),[item['id'] for item in manifest['items']],config)
        if identifier:
            item=next(item for item in manifest['items'] if item['id']==identifier)
            return {'type':'progress','text':item['text'],'audio_id':identifier,'voice_key':manifest['version'],'sha256':item['sha256']}
