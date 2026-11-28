"""Central local TTS selection; an utterance stays with one successful provider."""
import time
import asyncio
import hashlib
import json
import re
from collections import OrderedDict
from typing import Any,Protocol
from server.natural.capabilities import voice_capabilities
from server.security.types import AuthError

PROFILES:dict[str,dict[str,Any]]={
 'classic_butler':{'speed':.95,'supertonic_voice':'M1','pause_ms':180},
 'modern_butler':{'speed':1.,'supertonic_voice':'M2','pause_ms':140},
 'deep_butler':{'speed':.9,'supertonic_voice':'M3','pause_ms':220},
 'cinematic':{'speed':.92,'supertonic_voice':'M4','pause_ms':250},
 'professional':{'speed':1.,'supertonic_voice':'M1','pause_ms':160},
 'friendly':{'speed':1.02,'supertonic_voice':'M5','pause_ms':160},
 'fast':{'speed':1.15,'pause_ms':100},'custom':{},
}


class Synthesizer(Protocol):
    async def synthesize(self,request,text,voice,config)->dict:...


class LocalSynthesizer:
    def __init__(self,provider):self.provider=provider
    async def synthesize(self,request,text,voice,config):
        from server.mobile import audio_preferences,inference_call
        return await inference_call(request,'tts',{**await audio_preferences(request),'provider':self.provider,'voice':voice['voice'],'supertonic_voice':voice['supertonic_voice'],'steps':voice['steps'],'pause_ms':voice['pause_ms'],'speed':voice['speed'],'text':text})


class TTSRouter:
    def __init__(self,natural=None):
        self.natural=natural;self.pins={};self.cache=OrderedDict();self.cache_bytes=0
        self.providers:dict[str,Synthesizer]={'piper':LocalSynthesizer('piper'),'supertonic':LocalSynthesizer('supertonic')}
        if natural:
            from server.natural.elevenlabs import ElevenLabs
            from server.natural.voice_usage import VoiceUsage
            self.usage=VoiceUsage(natural.store)
            self.providers['elevenlabs']=ElevenLabs(natural.chat.settings,self.usage)

    def validate_text(self,text):
        from server.natural.memory import SECRET
        if SECRET.search(text) or re.search(r'\b(?:sk_[A-Za-z0-9]{16,}|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)|\b(?:api[- _]?key|authenticatietoken|wachtwoord|password)\s*(?:is|:|=)',text,re.I):
            raise AuthError('invalid_audio','Geheimen worden niet uitgesproken.',422)
        if self.natural:
            try:self.natural.store.safe_content(text)
            except ValueError:raise AuthError('invalid_audio','Geheimen worden niet uitgesproken.',422) from None

    def catalogue(self):
        caps=voice_capabilities();installed=caps.get('supertonic_voices',{})
        configured=bool(self.natural and self.natural.chat.settings.elevenlabs_api_key)
        return {'providers':[
            {'id':'elevenlabs','name':'ElevenLabs premium','available':configured,'offline':False,'streaming':'sentence; upstream PCM stream','voices':[],'parameters':['elevenlabs_voice_id','elevenlabs_model'],'requires_account_check':True},
            {'id':'supertonic','name':'Supertonic 3','available':any(installed.values()),'offline':True,'device':'cpu','streaming':'sentence','license':'OpenRAIL-M weights; MIT inference code','voices':[{'id':key,'name':'Mannenstem '+key,'available':value} for key,value in installed.items()], 'parameters':['speed','steps','pause_ms','volume']},
            {'id':'piper','name':'Piper','available':any(caps['voices'].values()),'offline':True,'device':'cpu','streaming':'sentence','license':'GPL-3.0 runtime; voice-specific dataset license','voices':[{'id':key,'name':key,'available':value} for key,value in caps['voices'].items()], 'parameters':['speed','speaker','volume']}],
            'profiles':PROFILES,'configuration_profiles_not_trained_voices':True,'online_text_transmission':configured,'online_notice':'Alleen uitgesproken tekst gaat naar ElevenLabs wanneer premium is gekozen. Onderbroken aanvragen kunnen credits kosten.',
            'unavailable':[{'id':'edge','reason':'Onofficieel online; niet geactiveerd. Geen gegarandeerde dienst.'},{'id':'xtts','reason':'Experimenteel; niet geïnstalleerd, zwaarder en afzonderlijke modellicentie.'}]}

    @staticmethod
    def select(config,caps):
        voice=config['voice'];mode=voice['mode'];provider=voice['tts_provider']
        if config['ai']['offline'] or mode in ('local','offline'):
            return 'supertonic' if caps.get('supertonic_voices',{}).get(voice['supertonic_voice'],False) else 'piper'
        if mode in ('premium','budget') or provider=='elevenlabs':return 'elevenlabs'
        if mode=='automatic' and provider=='auto' and caps.get('elevenlabs_ready'):return 'elevenlabs'
        if mode=='manual' and provider!='auto':return provider
        if (mode=='fast' or (mode in ('automatic','offline') and config['ai']['performance']=='saving')) and any(caps['voices'].values()):return 'piper'
        return 'supertonic' if caps.get('supertonic_voices',{}).get(voice['supertonic_voice'],False) else 'piper'

    async def synthesize(self,request,text,config,utterance=None):
        from server.natural.memory import SENSITIVE
        self.validate_text(text)
        principal=request.state.principal;now=time.monotonic()
        self.pins={key:value for key,value in self.pins.items() if now-value['at']<180}
        key=(principal.session_id,principal.device_id,utterance) if utterance else None
        pin=self.pins.get(key) if key else None
        voice=dict(config['voice']) if not pin else pin['voice']
        caps=voice_capabilities()
        caps['elevenlabs_ready']=bool(self.natural and self.natural.chat.settings.elevenlabs_api_key and (voice['elevenlabs_voice_id'] or self.natural.chat.settings.elevenlabs_voice_id))
        provider=self.select(config,caps) if not pin else pin['provider']
        if provider=='elevenlabs' and (config['ai']['offline'] or config['voice']['mode'] in ('offline','local')):
            if pin and pin['success']:raise AuthError('tts_private','Online spraak is uitgeschakeld; begin een nieuw lokaal antwoord.',409)
            provider=self.select(config,caps)
        if voice['mode']=='budget':voice['elevenlabs_model']='eleven_flash_v2_5'
        context=getattr(getattr(getattr(request,'app',None),'state',None),'natural',None)
        if context and getattr(context,'store',None):context.store.safe_content(text)
        if provider=='elevenlabs' and (voice['elevenlabs_sensitive_local'] or config['voice']['elevenlabs_sensitive_local']) and SENSITIVE.search(text):
            if pin and pin['success']:raise AuthError('tts_private','Gevoelige vervolgtekst wordt uitsluitend lokaal verwerkt; begin een nieuw antwoord.',409)
            provider='supertonic' if voice_capabilities().get('supertonic_voices',{}).get(voice['supertonic_voice'],False) else 'piper'
        if pin and provider!=pin['provider']:pin['provider']=provider
        if not pin:
            pin={'voice':voice,'provider':provider,'success':False,'at':now}
            if key:
                if len(self.pins)>=100:self.pins.pop(next(iter(self.pins)))
                self.pins[key]=pin
        cache_key=None
        if voice['cache'] and context:
            version=await asyncio.to_thread(context.context.memory_version,principal)
            cache_key=(principal.session_id,principal.device_id,version,hashlib.sha256(json.dumps({**voice,'provider':provider,'text':text},sort_keys=True).encode()).hexdigest())
            for expired in [key for key,value in self.cache.items() if now-value[0]>120]:self.cache_bytes-=len(self.cache.pop(expired)[1]['audio'])
            if cache_key in self.cache:
                result=self.cache[cache_key][1];self.cache.move_to_end(cache_key);pin['success']=True;pin['at']=now
                return {**result,'cache_hit':True}
        async def execute(selected):
            if selected not in self.providers:raise AuthError('speech_unavailable','Deze spraakprovider is niet beschikbaar.',503)
            if selected!='elevenlabs':return await self.providers[selected].synthesize(request,text,voice,config)
            work=asyncio.create_task(self.providers[selected].synthesize(request,text,voice,config))
            safety=self.natural.automation.safety if self.natural else None
            epoch=safety.state(principal.device_id)['epoch'] if safety else None
            async def watch():
                while True:
                    if await request.is_disconnected():return
                    if safety and safety.state(principal.device_id)['epoch']!=epoch:return
                    if not await asyncio.to_thread(request.app.state.security.store.live,principal):return
                    await asyncio.sleep(.15)
            monitor=asyncio.create_task(watch())
            try:
                done,_=await asyncio.wait((work,monitor),return_when=asyncio.FIRST_COMPLETED)
                if work in done:return await work
                raise AuthError('speech_cancelled','De stemaanvraag is gestopt.',499)
            finally:
                monitor.cancel()
                if not work.done():work.cancel()
                await asyncio.gather(work,monitor,return_exceptions=True)
        try:result=await execute(provider)
        except AuthError as error:
            if error.code not in ('speech_unavailable','tts_not_configured','tts_budget','tts_quota','tts_authentication') or pin['success'] or provider=='piper' or not voice['fallback']:raise
            # No audio was delivered. Retry once in the same private inference helper.
            result=await execute('piper')
            provider='piper';pin['provider']=provider
        pin['success']=True;pin['at']=time.monotonic()
        result={**result,'selected_provider':provider,'selected_voice':result.get('voice',voice['voice'])}
        if cache_key and context is not None and provider==self.select(config,caps) and len(result['audio'])<=8_000_000 and version==await asyncio.to_thread(context.context.memory_version,principal):
            while self.cache and self.cache_bytes+len(result['audio'])>8_000_000:self.cache_bytes-=len(self.cache.popitem(last=False)[1][1]['audio'])
            self.cache[cache_key]=(time.monotonic(),result);self.cache_bytes+=len(result['audio'])
        return result
