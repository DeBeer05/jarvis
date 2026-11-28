"""Supported external adapters, closed actions and encrypted backend credentials."""
import asyncio
import json
import math
from decimal import Decimal,ROUND_HALF_UP
from urllib.parse import urlsplit,quote

import httpx
from pydantic import Field,model_validator
from server.automation.models import Input
from server.automation.store import fingerprint


class HomePolicy(Input):
    enabled:bool=False
    endpoint:str=Field(default='',max_length=500)
    entities:list[str]=Field(default_factory=list,max_length=100)
    aliases:dict[str,str]=Field(default_factory=dict,max_length=100)
    @model_validator(mode='after')
    def valid(self):
        import re
        if self.endpoint:
            url=urlsplit(self.endpoint)
            if url.port is not None and not 1<=url.port<=65535:raise ValueError('Ongeldige poort')
            if url.scheme!='https' or not url.hostname or url.username or url.password or url.query or url.fragment or '%' in url.path or '..' in url.path:raise ValueError('Gebruik de HTTPS-basis-URL van uw Home Assistant zonder inloggegevens')
            self.endpoint=self.endpoint.rstrip('/')
        if self.enabled and not self.endpoint:raise ValueError('Home Assistant-adres ontbreekt')
        if any(not re.fullmatch(r'(?:light|switch|climate|sensor|binary_sensor|scene|automation)\.[a-z0-9_]{1,100}',entity) for entity in self.entities):raise ValueError('Niet-ondersteunde entiteit')
        if any(not 1<=len(alias)<=80 or target not in self.entities for alias,target in self.aliases.items()):raise ValueError('Een naam moet naar een toegestane entiteit verwijzen')
        if len({alias.casefold() for alias in self.aliases})!=len(self.aliases):raise ValueError('Gebruik unieke namen')
        return self


class TripCost(Input):
    distance_km:Decimal=Field(ge=0,le=10000,max_digits=9,decimal_places=3)
    liters_per_100km:Decimal=Field(gt=0,le=100,max_digits=6,decimal_places=3)
    price_per_liter:Decimal=Field(gt=0,le=100,max_digits=6,decimal_places=3)


class ExternalAdapters:
    def __init__(self,engine,*,transport=None):
        self.engine=engine;self.transport=transport;self.client=None;self.cache={};self.lock=asyncio.Lock()

    def home_policy(self):return HomePolicy.model_validate(self.engine.store.preference('home_assistant',{}))

    def signature(self):
        with self.engine.store.db() as db:row=db.execute("SELECT ciphertext FROM integration_secrets WHERE key='external:home_assistant'").fetchone()
        return fingerprint([self.home_policy().model_dump(mode='json'),fingerprint(bytes(row[0]).hex()) if row else None])

    def capabilities(self):
        policy=self.home_policy()
        try:
            saved=self.engine.integrations.vault.get('external:home_assistant')
            home=json.loads(saved) if saved else {}
            home_ready=bool(home.get('token') and home.get('endpoint')==policy.endpoint)
        except (ValueError,OSError):home_ready=False
        try:routes=bool(self.engine.integrations.vault.get('external:openrouteservice'))
        except (ValueError,OSError):routes=False
        return {'home_assistant':{'enabled':policy.enabled,'configured':home_ready,'endpoint':policy.endpoint,'entities':policy.entities,'aliases':policy.aliases,'policy_hash':self.signature()},
                'routes':{'configured':routes,'provider':'openrouteservice','live_traffic':False},
                'creality_hi':{'supported':False,'reason':'Geen gedocumenteerde publieke Creality Hi/Cloud-status-API geverifieerd. Gebruik voorlopig het officiële dashboard.','dashboard':'https://www.crealitycloud.com/'},
                'fuel_prices':{'live':False,'reason':'Geen actuele brandstofprijsdienst gekoppeld; handmatige bedragen blijven mogelijk.'}}

    async def close(self):
        if self.client:await self.client.aclose()

    async def request(self,method,url,headers,body=None,guard=lambda:None):
        if self.client is None:self.client=httpx.AsyncClient(timeout=10,follow_redirects=False,trust_env=False,transport=self.transport,limits=httpx.Limits(max_connections=3,max_keepalive_connections=2))
        guard()
        async with self.client.stream(method,url,headers=headers,**({'json':body} if body is not None else {})) as response:
            response.raise_for_status();raw=bytearray()
            async for part in response.aiter_bytes():
                if len(raw)+len(part)>524288:raise ValueError('Externe gegevens zijn te groot')
                raw.extend(part)
        guard();return json.loads(raw)

    async def home_headers(self,policy):
        if not policy.enabled:raise ValueError('Home Assistant is uitgeschakeld')
        saved=await asyncio.to_thread(self.engine.integrations.vault.get,'external:home_assistant')
        data=json.loads(saved) if saved else {}
        if not policy.enabled or not data.get('token') or data.get('endpoint')!=policy.endpoint:raise ValueError('Home Assistant is niet volledig en veilig ingesteld')
        return {'Authorization':'Bearer '+data['token']}

    async def home_state(self,entity,guard=lambda:None,*,fresh=False):
        policy=self.home_policy()
        if entity not in policy.entities:raise ValueError('Entiteit is niet door de eigenaar toegestaan')
        signature=self.signature();key=(signature,entity);now=self.engine.store.clock()
        if not fresh and key in self.cache and now-self.cache[key][0]<15:
            guard();return self.cache[key][1]
        headers=await self.home_headers(policy)
        data=await self.request('GET',policy.endpoint+'/api/states/'+quote(entity,safe=''),headers,guard=guard)
        if self.signature()!=signature or not isinstance(data,dict) or data.get('entity_id')!=entity or not isinstance(data.get('state'),str):raise ValueError('Geen geverifieerde Home Assistant-status')
        attributes=data.get('attributes',{})
        if not isinstance(attributes,dict):raise ValueError('Ongeldige sensorgegevens')
        safe:dict[str,str|int|float]={}
        for name in ('friendly_name','temperature','current_temperature','brightness','unit_of_measurement','last_triggered'):
            value=attributes.get(name)
            if isinstance(value,str):safe[name]=value[:150]
            elif isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value):safe[name]=value
        result={'entity_id':entity,'state':data['state'][:200],'attributes':safe,'source':'home_assistant','observed_at':now}
        if len(self.cache)>=100:self.cache.pop(next(iter(self.cache)))
        self.cache[key]=(now,result);return result

    async def home_control(self,payload,guard=lambda:None):
        policy=self.home_policy();signature=self.signature();entity=payload['entity_id'];domain=entity.split('.')[0]
        if payload.get('policy_hash')!=signature or entity not in policy.entities:raise ValueError('Home Assistant-voorstel of rechten zijn gewijzigd')
        action=payload['action'];body={'entity_id':entity}
        if action in ('on','off') and domain in ('light','switch'):service='turn_'+action
        elif action=='temperature' and domain=='climate':service='set_temperature';body['temperature']=payload['temperature']
        elif action=='scene' and domain=='scene':service='turn_on'
        elif action=='routine' and domain=='automation':service='trigger';body['skip_condition']=False
        else:raise ValueError('Actie past niet bij de toegestane entiteit')
        if payload.get('brightness') is not None:
            if domain!='light' or action!='on':raise ValueError('Helderheid hoort alleen bij licht aan')
            body['brightness']=payload['brightness']
        headers=await self.home_headers(policy)
        def current():
            guard()
            if self.signature()!=signature:raise ValueError('Home Assistant-configuratie gewijzigd')
        await self.request('POST',policy.endpoint+'/api/services/'+domain+'/'+service,headers,body,current)
        self.cache.pop((signature,entity),None)
        if action in ('scene','routine'):return {'accepted':True,'state':'trigger_requested','execution_verified':False}
        for attempt in range(5):
            state=await self.home_state(entity,current,fresh=True)
            attributes=state['attributes']
            matched=state['state']==action if action in ('on','off') else isinstance(attributes.get('temperature'),(int,float)) and abs(attributes['temperature']-payload['temperature'])<.1
            if payload.get('brightness') is not None:matched=matched and isinstance(attributes.get('brightness'),(int,float)) and abs(attributes['brightness']-payload['brightness'])<=1
            if matched:return {'verified':True,**state}
            if attempt<4:await asyncio.sleep(.25)
        raise ValueError('Home Assistant accepteerde het verzoek, maar de nieuwe toestand is niet bevestigd')

    async def route(self,payload,guard=lambda:None):
        key=await asyncio.to_thread(self.engine.integrations.vault.get,'external:openrouteservice')
        if not key:raise ValueError('Openrouteservice is niet ingesteld')
        cache_key=('route',fingerprint(payload));now=self.engine.store.clock()
        if cache_key in self.cache and now-self.cache[cache_key][0]<600:
            guard();return self.cache[cache_key][1]
        data=await self.request('POST','https://api.openrouteservice.org/v2/directions/driving-car/json',{'Authorization':key},{'coordinates':payload['coordinates'],'instructions':False,'geometry':False},guard)
        route=data.get('routes',[None])[0]
        summary=route.get('summary',{}) if isinstance(route,dict) else {}
        if any(type(summary.get(name)) not in (float,int) or not math.isfinite(summary[name]) or summary[name]<0 for name in ('distance','duration')):raise ValueError('Geen geverifieerde routegegevens')
        result={'distance_km':summary['distance']/1000,'duration_seconds':summary['duration'],'live_traffic':False,'source':'openrouteservice','observed_at':self.engine.store.clock(),'attribution':str(data.get('metadata',{}).get('attribution','openrouteservice | OpenStreetMap contributors'))[:300]}
        if len(self.cache)>=100:self.cache.pop(next(iter(self.cache)))
        self.cache[cache_key]=(now,result);return result

    @staticmethod
    def cost(payload):
        values=TripCost.model_validate(payload)
        liters=values.distance_km*values.liters_per_100km/100
        return {'liters':str(liters.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)),
                'estimated_fuel_cost_eur':str((liters*values.price_per_liter).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)),
                'source':'user_entered_values','live_prices':False,'includes_parking_maintenance_taxes':False}
