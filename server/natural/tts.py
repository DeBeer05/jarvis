"""Central local TTS selection; an utterance stays with one successful provider."""
import time
import asyncio
import hashlib
import json
from collections import OrderedDict
from typing import Any
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


class TTSRouter:
    def __init__(self):self.pins={};self.cache=OrderedDict();self.cache_bytes=0

    @staticmethod
    def catalogue():
        caps=voice_capabilities();installed=caps.get('supertonic_voices',{})
        return {'providers':[
            {'id':'supertonic','name':'Supertonic 3','available':any(installed.values()),'offline':True,'device':'cpu','streaming':'sentence','license':'OpenRAIL-M weights; MIT inference code','voices':[{'id':key,'name':'Mannenstem '+key,'available':value} for key,value in installed.items()], 'parameters':['speed','steps','pause_ms','volume']},
            {'id':'piper','name':'Piper','available':any(caps['voices'].values()),'offline':True,'device':'cpu','streaming':'sentence','license':'GPL-3.0 runtime; voice-specific dataset license','voices':[{'id':key,'name':key,'available':value} for key,value in caps['voices'].items()], 'parameters':['speed','speaker','volume']}],
            'profiles':PROFILES,'configuration_profiles_not_trained_voices':True,'online_text_transmission':False,
            'unavailable':[{'id':'edge','reason':'Onofficieel online; niet geactiveerd. Geen gegarandeerde dienst.'},{'id':'xtts','reason':'Experimenteel; niet geïnstalleerd, zwaarder en afzonderlijke modellicentie.'}]}

    @staticmethod
    def select(config,caps):
        voice=config['voice'];mode=voice['mode'];provider=voice['tts_provider']
        if mode=='manual' and provider!='auto':return provider
        if (mode=='fast' or (mode in ('automatic','offline') and config['ai']['performance']=='saving')) and any(caps['voices'].values()):return 'piper'
        return 'supertonic' if caps.get('supertonic_voices',{}).get(voice['supertonic_voice'],False) else 'piper'

    async def synthesize(self,request,text,config,utterance=None):
        from server.mobile import audio_preferences,inference_call
        principal=request.state.principal;now=time.monotonic()
        self.pins={key:value for key,value in self.pins.items() if now-value['at']<180}
        key=(principal.session_id,principal.device_id,utterance) if utterance else None
        pin=self.pins.get(key) if key else None
        voice=dict(config['voice']) if not pin else pin['voice']
        provider=self.select(config,voice_capabilities()) if not pin else pin['provider']
        if not pin:
            pin={'voice':voice,'provider':provider,'success':False,'at':now}
            if key:
                if len(self.pins)>=100:self.pins.pop(next(iter(self.pins)))
                self.pins[key]=pin
        payload={**await audio_preferences(request),'provider':provider,'voice':voice['voice'],'supertonic_voice':voice['supertonic_voice'],'steps':voice['steps'],'pause_ms':voice['pause_ms'],'speed':voice['speed'],'text':text}
        cache_key=None
        context=getattr(getattr(getattr(request,'app',None),'state',None),'natural',None)
        if voice['cache'] and context:
            version=await asyncio.to_thread(context.context.memory_version,principal)
            cache_key=(principal.session_id,principal.device_id,version,hashlib.sha256(json.dumps({**voice,'provider':provider,'text':text},sort_keys=True).encode()).hexdigest())
            for expired in [key for key,value in self.cache.items() if now-value[0]>120]:self.cache_bytes-=len(self.cache.pop(expired)[1]['audio'])
            if cache_key in self.cache:
                result=self.cache[cache_key][1];self.cache.move_to_end(cache_key);pin['success']=True;pin['at']=now
                return {**result,'cache_hit':True}
        try:result=await inference_call(request,'tts',payload)
        except AuthError as error:
            if error.code!='speech_unavailable' or pin['success'] or provider=='piper' or not voice['fallback']:raise
            # No audio was delivered. Retry once in the same private inference helper.
            result=await inference_call(request,'tts',{**payload,'provider':'piper'})
            provider='piper';pin['provider']=provider
        pin['success']=True;pin['at']=time.monotonic()
        result={**result,'selected_provider':provider,'selected_voice':result.get('voice',voice['voice'])}
        if cache_key and context is not None and provider==payload['provider'] and len(result['audio'])<=8_000_000 and version==await asyncio.to_thread(context.context.memory_version,principal):
            while self.cache and self.cache_bytes+len(result['audio'])>8_000_000:self.cache_bytes-=len(self.cache.popitem(last=False)[1][1]['audio'])
            self.cache[cache_key]=(time.monotonic(),result);self.cache_bytes+=len(result['audio'])
        return result
