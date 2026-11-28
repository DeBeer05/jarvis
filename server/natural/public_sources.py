"""Bounded, cached reads from explicit official public sources; no model calls."""
import asyncio
import json
import math
import time
from collections import OrderedDict
from contextlib import asynccontextmanager
from xml.etree import ElementTree

import httpx


class PublicSources:
    def __init__(self,*,transport=None,clock=time.time):
        self.http:httpx.AsyncClient|None=None;self.transport=transport
        self.clock=clock;self.cache=OrderedDict();self.lock=asyncio.Lock();self.loads:dict[tuple,list]={}

    async def close(self):
        if self.http is not None:await self.http.aclose();self.http=None

    async def read(self,url,params=None,limit=131072):
        if self.http is None:self.http=httpx.AsyncClient(timeout=6,follow_redirects=False,trust_env=False,transport=self.transport)
        async with self.http.stream('GET',url,params=params) as response:
            response.raise_for_status();parts=[];size=0
            async for chunk in response.aiter_bytes():
                size+=len(chunk)
                if size>limit:raise ValueError('Bronantwoord is te groot')
                parts.append(chunk)
            return b''.join(parts)

    @asynccontextmanager
    async def key_lock(self,key):
        async with self.lock:
            entry=self.loads.setdefault(key,[asyncio.Lock(),0]);entry[1]+=1
        try:
            async with entry[0]:yield
        finally:
            async with self.lock:
                entry[1]-=1
                if not entry[1]:self.loads.pop(key,None)

    async def cached(self,key,load,seconds):
        async with self.key_lock(key):
            now=self.clock();old=self.cache.get(key)
            if old and now-old['fetched_at']<seconds:return {**old,'cached':True}
            try:
                data=await load();result={**data,'fetched_at':self.clock(),'cached':False,'stale':False}
            except (httpx.HTTPError,ValueError,KeyError,TypeError,ElementTree.ParseError):
                if old and now-old['fetched_at']<3600:return {**old,'cached':True,'stale':True}
                raise ValueError('De openbare bron is tijdelijk niet beschikbaar') from None
            self.cache[key]=result;self.cache.move_to_end(key)
            while len(self.cache)>16:self.cache.popitem(last=False)
            return result

    async def resolve_place(self,location):
        places=json.loads(await self.read('https://geocoding-api.open-meteo.com/v1/search',
            {'name':location,'count':5,'language':'nl','format':'json'})).get('results',[])
        matches=[place for place in places if str(place.get('name','')).casefold()==location.casefold()]
        if len(matches)!=1:raise ValueError('De plaatsnaam is niet eenduidig; kies een specifiekere plaats')
        place=matches[0];latitude=float(place['latitude']);longitude=float(place['longitude'])
        if not math.isfinite(latitude) or not math.isfinite(longitude) or not -90<=latitude<=90 or not -180<=longitude<=180:raise ValueError('Ongeldige plaatscoördinaten')
        return {'name':str(place['name'])[:100],'latitude':latitude,'longitude':longitude}

    async def location(self,name):return await self.cached(('location',name.casefold()),lambda:self.resolve_place(name),3600)

    async def weather(self,location,timezone,offset=0):
        if not location.strip():raise ValueError('Kies eerst een plaats voor het weer')
        if type(offset) is not int or not 0<=offset<=7:raise ValueError('Kies maximaal zeven dagen vooruit')
        async def load():
            place=await self.resolve_place(location);latitude=place['latitude'];longitude=place['longitude']
            if offset:
                raw=json.loads(await self.read('https://api.open-meteo.com/v1/forecast',{'latitude':latitude,'longitude':longitude,'daily':'temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max','timezone':timezone,'forecast_days':offset+1}))
                daily=raw['daily'];values={key:float(daily[source][offset]) for key,source in (('temperature_2m','temperature_2m_max'),('minimum','temperature_2m_min'),('precipitation','precipitation_sum'),('wind_speed_10m','wind_speed_10m_max'))}
                if not all(math.isfinite(value) for value in values.values()):raise ValueError('Ongeldige weersverwachting')
                return {'source':'Open-Meteo','location':place['name'],'observed_at':daily['time'][offset],'timezone':timezone,'values':values,'units':{'temperature_2m':'°C','precipitation':'mm','wind_speed_10m':'km/h'},'forecast':True}
            raw=json.loads(await self.read('https://api.open-meteo.com/v1/forecast',
                {'latitude':latitude,'longitude':longitude,'current':'temperature_2m,precipitation,wind_speed_10m','timezone':timezone,'forecast_days':1}))
            current=raw['current'];units=raw['current_units']
            values={name:float(current[name]) for name in ('temperature_2m','precipitation','wind_speed_10m')}
            if not all(math.isfinite(value) for value in values.values()):raise ValueError('Ongeldige weerswaarneming')
            return {'source':'Open-Meteo','location':place['name'],'observed_at':current['time'],'timezone':timezone,'values':values,'units':{name:str(units[name])[:20] for name in values}}
        return await self.cached(('weather',location.casefold(),timezone,offset) if offset else ('weather',location.casefold(),timezone),load,600)

    async def news(self):
        async def load():
            body=await self.read('https://feeds.nos.nl/nosnieuwsalgemeen')
            if b'<!DOCTYPE' in body.upper() or b'<!ENTITY' in body.upper():raise ValueError('Onveilig feedformaat')
            root=ElementTree.fromstring(body);items=[]
            for item in root.findall('./channel/item')[:5]:
                title=(item.findtext('title') or '').strip()[:240]
                link=(item.findtext('link') or '').strip()
                if not title or not link.startswith('https://nos.nl/'):continue
                items.append({'title':title,'url':link,'published':(item.findtext('pubDate') or '')[:100]})
            if not items:raise ValueError('Geen verifieerbare nieuwskoppen ontvangen')
            return {'source':'NOS RSS','items':items}
        return await self.cached(('news',),load,900)

    async def traffic(self,location):
        from server.natural.traffic import records,nearby
        place=await self.location(location)
        async def load():
            return records(await self.read('https://opendata.ndw.nu/actueel_beeld.xml.gz',limit=1_000_000),self.clock())
        data=await self.cached(('traffic',),load,120)
        return nearby(data,place)
