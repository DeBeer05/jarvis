"""Official ElevenLabs HTTP API, only TTS and read-only account metadata."""
import asyncio
import base64
from contextlib import aclosing
import io
import json
import math
import time
import wave

import httpx

from server.security.types import AuthError

MODELS=('eleven_flash_v2_5','eleven_multilingual_v2','eleven_v3','eleven_v4','eleven_v4_turbo','eleven_v3_conversational')
LEGACY=('eleven_flash_v2_5','eleven_multilingual_v2')
CONTROLS={model:(['elevenlabs_stability','elevenlabs_similarity','elevenlabs_style','elevenlabs_speaker_boost','speed'] if model in LEGACY else ['elevenlabs_stability'] if model.startswith('eleven_v3') else []) for model in MODELS}
CONTROLS['eleven_flash_v2_5']=['elevenlabs_stability','elevenlabs_similarity','speed']


class ElevenLabs:
    def __init__(self,settings,usage,*,client_factory=None):
        self.settings,self.usage=settings,usage;self.client_factory=client_factory or httpx.AsyncClient
        self.metadata=None;self.checked=0.;self.lock=asyncio.Lock();self.slot=asyncio.Lock()

    def client(self):
        if not self.settings.elevenlabs_api_key:raise AuthError('tts_not_configured','ElevenLabs-sleutel ontbreekt op de backend.',503)
        return self.client_factory(base_url='https://api.elevenlabs.io',headers={'xi-api-key':self.settings.elevenlabs_api_key},verify=True,trust_env=False,follow_redirects=False,timeout=httpx.Timeout(20,connect=4))

    @staticmethod
    def check(response):
        if response.status_code in (401,403):raise AuthError('tts_authentication','ElevenLabs weigert de sleutel of deze stem/modeltoegang.',503)
        if response.status_code in (402,429):raise AuthError('tts_quota','ElevenLabs-tegoed of aanvraaglimiet is bereikt.',429)
        if response.status_code!=200:raise AuthError('speech_unavailable','ElevenLabs is niet beschikbaar voor deze aanvraag.',503)

    async def read(self,client,path,params=None):
        async with client.stream('GET',path,params=params) as response:
            self.check(response);raw=bytearray()
            async for part in response.aiter_bytes():
                if len(raw)+len(part)>400000:raise ValueError('Providerantwoord te groot')
                raw.extend(part)
        return json.loads(raw)

    async def inspect(self,*,refresh=False):
        async with self.lock:
            if not refresh and self.metadata and time.monotonic()-self.checked<60:return self.metadata
            try:
                async with self.client() as client:
                    models=await self.read(client,'/v1/models')
                    voices=await self.read(client,'/v2/voices',{'page_size':100,'include_custom_rates':'false'})
                    subscription=await self.read(client,'/v1/user/subscription')
                supported=[]
                for item in models:
                    if item.get('model_id') not in MODELS or not item.get('can_do_text_to_speech') or not any(language.get('language_id')=='nl' for language in item.get('languages',[])):continue
                    controls=list(CONTROLS[item['model_id']])
                    if not item.get('can_use_style'):controls=[key for key in controls if key!='elevenlabs_style']
                    if not item.get('can_use_speaker_boost'):controls=[key for key in controls if key!='elevenlabs_speaker_boost']
                    rate=item.get('model_rates',{}).get('character_cost_multiplier',item.get('token_cost_factor',1))
                    if not isinstance(rate,(int,float)) or not math.isfinite(rate) or not 0<rate<=100:continue
                    supported.append({'id':item['model_id'],'name':item.get('name',item['model_id']),'controls':controls,'reserve_multiplier':max(1,rate)})
                selected=[{'id':item['voice_id'],'name':str(item.get('name','Stem'))[:100],'category':str(item.get('category','existing'))[:40]} for item in voices.get('voices',[])[:100] if isinstance(item.get('voice_id'),str)]
                count,limit=subscription['character_count'],subscription['character_limit']
                if not isinstance(count,int) or not isinstance(limit,int) or min(count,limit)<0:raise ValueError('Ongeldig tegoed')
                self.metadata={'models':supported,'voices':selected,'remaining_credits':max(0,limit-count),'credits_used':count,'credit_limit':limit,'checked_at':time.time(),'tier':str(subscription.get('tier','unknown'))[:30]}
                self.checked=time.monotonic();return self.metadata
            except (httpx.HTTPError,ValueError,KeyError,TypeError,AttributeError):raise AuthError('speech_unavailable','ElevenLabs-accountgegevens konden niet veilig worden gecontroleerd.',503) from None

    @staticmethod
    def body(text,voice,model):
        body={'text':text,'model_id':model['id']}
        if model['id']!='eleven_multilingual_v2':body['language_code']='nl'
        fields={'elevenlabs_stability':'stability','elevenlabs_similarity':'similarity_boost','elevenlabs_style':'style','elevenlabs_speaker_boost':'use_speaker_boost','speed':'speed'}
        parameters={fields[name]:voice[name] for name in model['controls']}
        if 'speed' in parameters:parameters['speed']=min(1.2,max(.7,parameters['speed']))
        if model['id'].startswith('eleven_v3'):parameters['stability']=min((0.,.5,1.),key=lambda value:abs(value-voice['elevenlabs_stability']))
        if parameters:body['voice_settings']=parameters
        return body

    async def stream_pcm(self,request,text,voice,config):
        if self.slot.locked():raise AuthError('speech_busy','De premium stem is bezet.',429)
        async with self.slot:
            metadata=await self.inspect()
            model=next((item for item in metadata['models'] if item['id']==voice['elevenlabs_model']),None)
            identifier=voice['elevenlabs_voice_id'] or self.settings.elevenlabs_voice_id
            if not model or identifier not in {item['id'] for item in metadata['voices']}:raise AuthError('tts_not_configured','Kies een toegankelijke Nederlandse ElevenLabs-stem en model.',503)
            credits=math.ceil(len(text)*model['reserve_multiplier'])
            reservation=await asyncio.to_thread(self.usage.reserve,request.state.principal,config,len(text),credits)
            attempted=False;size=0;status='released'
            try:
                async with self.client() as client:
                    balance=await self.read(client,'/v1/user/subscription')
                    count,limit=(balance.get('character_count'),balance.get('character_limit')) if isinstance(balance,dict) else (None,None)
                    if not isinstance(count,int) or not isinstance(limit,int) or min(count,limit)<0:raise AuthError('speech_unavailable','Het actuele tegoed kon niet veilig worden gecontroleerd.',503)
                    metadata.update(remaining_credits=max(0,limit-count),credits_used=count,credit_limit=limit,checked_at=time.time())
                    if credits>metadata['remaining_credits']:raise AuthError('tts_quota','ElevenLabs heeft onvoldoende gecontroleerd tegoed.',429)
                    attempted=True;await asyncio.to_thread(self.usage.finish,reservation,'attempted')
                    async with client.stream('POST',f'/v1/text-to-speech/{identifier}/stream',params={'output_format':'pcm_24000'},json=self.body(text,voice,model)) as response:
                        self.check(response)
                        async for part in response.aiter_bytes():
                            size+=len(part)
                            if size>5_760_000:raise AuthError('speech_unavailable','Premium audio overschrijdt de begrensde duur.',503)
                            if part:yield part
                if not size or size%2:raise AuthError('speech_unavailable','Onvolledige premium audio ontvangen.',503)
                status='completed'
            except asyncio.CancelledError:
                status='cancelled' if attempted else 'released';raise
            except httpx.HTTPError:
                status='failed' if attempted else 'released'
                raise AuthError('speech_unavailable','De verbinding met ElevenLabs is onderbroken.',503) from None
            finally:
                if attempted and status=='released':status='failed'
                await asyncio.shield(asyncio.to_thread(self.usage.finish,reservation,status))

    async def synthesize(self,request,text,voice,config):
        raw=bytearray();started=time.perf_counter()
        async with aclosing(self.stream_pcm(request,text,voice,config)) as stream:
            async for part in stream:raw.extend(part)
        output=io.BytesIO()
        with wave.open(output,'wb') as target:
            target.setnchannels(1);target.setsampwidth(2);target.setframerate(24000);target.writeframes(raw)
        return {'audio':base64.b64encode(output.getvalue()).decode(),'seconds':time.perf_counter()-started,'voice':voice['elevenlabs_voice_id'] or self.settings.elevenlabs_voice_id}
