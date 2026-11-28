"""Bounded DATEX II v3 incident parsing from NDW's documented public feed."""
import gzip
import io
import math
from datetime import datetime,UTC
from xml.etree import ElementTree as E

LABELS={'Accident':'Ongeval','AbnormalTraffic':'Langzaam of stilstaand verkeer','RoadOrCarriagewayOrLaneManagement':'Afgesloten rijbaan of rijstrook','ConstructionWorks':'Wegwerkzaamheden','MaintenanceWorks':'Onderhoud','VehicleObstruction':'Voertuig op de weg','GeneralObstruction':'Obstakel op de weg','EnvironmentalObstruction':'Hinder door de omgeving'}

def named(element,name):return next((item.text for item in element.iter() if item.tag.rsplit('}',1)[-1]==name and item.text),'')

def records(compressed,now):
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:body=stream.read(12_000_001)
    except (OSError,EOFError):raise ValueError('Ongeldig gecomprimeerd verkeersbericht') from None
    if len(body)>12_000_000 or b'<!DOCTYPE' in body.upper() or b'<!ENTITY' in body.upper():raise ValueError('Onveilig verkeersformaat')
    root=E.fromstring(body);published=named(root,'publicationTime')
    stamp=datetime.fromisoformat(published.replace('Z','+00:00')).timestamp()
    if not now-1800<=stamp<=now+300:raise ValueError('Verkeersbron is niet actueel')
    result=[]
    for index,item in enumerate(root.iter()):
        if index>150000:raise ValueError('Verkeersbron te uitgebreid')
        if item.tag.rsplit('}',1)[-1]!='situationRecord':continue
        start=named(item,'overallStartTime');end=named(item,'overallEndTime')
        if start and datetime.fromisoformat(start.replace('Z','+00:00')).timestamp()>now:continue
        if end and datetime.fromisoformat(end.replace('Z','+00:00')).timestamp()<=now:continue
        if named(item,'validityStatus')=='suspended':continue
        latitude=named(item,'latitude');longitude=named(item,'longitude')
        if not latitude or not longitude:
            positions=named(item,'posList').split()
            if len(positions)<2:continue
            latitude,longitude=positions[:2]
        lat,lon=float(latitude),float(longitude)
        if not math.isfinite(lat+lon) or not -90<=lat<=90 or not -180<=lon<=180:continue
        kind=item.attrib.get('{http://www.w3.org/2001/XMLSchema-instance}type','').rsplit(':',1)[-1]
        label=LABELS.get(kind,'Verkeershinder');road=named(item,'roadNumber')
        result.append({'latitude':lat,'longitude':lon,'text':label+(' op '+road[:20] if road else '')})
        if len(result)>4000:raise ValueError('Te veel verkeersmeldingen')
    return {'source':'NDW','observed_at':datetime.fromtimestamp(stamp,UTC).isoformat(),'items':result}

def nearby(data,place,radius=25):
    lat,lon=place['latitude'],place['longitude'];items=[]
    for entry in data['items']:
        a,b,c,d=map(math.radians,(lat,lon,entry['latitude'],entry['longitude']))
        term=math.sin((c-a)/2)**2+math.cos(a)*math.cos(c)*math.sin((d-b)/2)**2
        distance=6371*2*math.asin(min(1,math.sqrt(term)))
        if distance<=radius:items.append({'text':entry['text'],'distance_km':round(distance,1)})
    items.sort(key=lambda item:item['distance_km'])
    return {key:value for key,value in data.items() if key!='items'}|{'location':place['name'],'radius_km':radius,'items':items[:5],'matching_count':len(items),'route_delay_verified':False}
