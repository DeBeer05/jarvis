"""Opt-in device snapshots. Metadata is data, never an instruction or a grant."""
import json

from pydantic import Field
from server.natural.models import StrictModel,DeviceSettings
from server.natural.store import encode


def migrate(db):
    db.execute('''CREATE TABLE IF NOT EXISTS natural_device_status(
        device_id TEXT PRIMARY KEY REFERENCES auth_devices(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
        payload TEXT NOT NULL,updated REAL NOT NULL)''')


class NotificationCount(StrictModel):
    package:str=Field(pattern=r'^[a-z][a-z0-9_.]{2,100}$')
    count:int=Field(ge=0,le=1000)


class Location(StrictModel):
    latitude:float=Field(ge=-90,le=90,allow_inf_nan=False)
    longitude:float=Field(ge=-180,le=180,allow_inf_nan=False)
    accuracy_m:float=Field(ge=0,le=100000,allow_inf_nan=False)
    sampled_at:float=Field(ge=0,allow_inf_nan=False)


class Snapshot(StrictModel):
    battery:int|None=Field(default=None,ge=0,le=100)
    charging:bool|None=None
    notifications:list[NotificationCount]|None=Field(default=None,max_length=20)
    location:Location|None=None


class DeviceStatus:
    def __init__(self,natural):self.natural=natural

    @staticmethod
    def visible(data,consent,now):
        result={}
        for key,flag in (('battery','status_allowed'),('charging','status_allowed'),('notifications','notification_allowed'),('location','location_allowed')):
            entry=data.get(key)
            if not entry or entry['received_at']<now-86400 or not getattr(consent,flag):continue
            if key=='notifications':entry={**entry,'value':[value for value in entry['value'] if value['package'] in consent.notification_packages]}
            result[key]=entry
        return result

    def prune(self,db,user,now):
        rows=db.execute("SELECT x.device_id,x.payload,s.payload AS consent FROM natural_device_status x LEFT JOIN natural_settings s ON s.user_id=x.user_id AND s.device_id=x.device_id AND s.scope='device' WHERE x.user_id=? LIMIT 200",(user,)).fetchall()
        for row in rows:
            consent=DeviceSettings.model_validate_json(row['consent']) if row['consent'] else DeviceSettings()
            clean=self.visible(json.loads(row['payload']),consent,now)
            if clean:db.execute('UPDATE natural_device_status SET payload=? WHERE device_id=?',(encode(clean),row['device_id']))
            else:db.execute('DELETE FROM natural_device_status WHERE device_id=?',(row['device_id'],))

    def save(self,principal,snapshot):
        n=self.natural
        if n.presence.snapshot(principal)['mode']=='private':raise PermissionError('Apparaatsignalen zijn in privémodus gepauzeerd')
        data=snapshot.model_dump(mode='json',exclude_none=True)
        if not data:raise ValueError('Geen apparaatstatus ontvangen')
        with n.store.transaction(principal,write=True) as (db,user):
            saved=db.execute("SELECT payload FROM natural_settings WHERE user_id=? AND device_id=? AND scope='device'",(user,principal.device_id)).fetchone()
            consent=DeviceSettings.model_validate_json(saved['payload']) if saved else DeviceSettings()
            if any(key in data for key in ('battery','charging')) and not consent.status_allowed:raise PermissionError('Apparaatstatus delen is uitgeschakeld')
            if 'notifications' in data and (not consent.notification_allowed or any(item['package'] not in consent.notification_packages for item in data['notifications'])):raise PermissionError('Deze meldingsmetadata is niet toegestaan')
            if 'location' in data:
                if not consent.location_allowed:raise PermissionError('Locatie delen is uitgeschakeld')
                if data['location']['sampled_at']>n.store.clock()+300:raise ValueError('Locatietijd ligt in de toekomst')
            row=db.execute('SELECT payload FROM natural_device_status WHERE device_id=?',(principal.device_id,)).fetchone()
            now=n.store.clock()
            previous=self.visible(json.loads(row['payload']),consent,now) if row else {}
            for key,value in data.items():previous[key]={'value':value,'received_at':now}
            db.execute('INSERT INTO natural_device_status VALUES (?,?,?,?) ON CONFLICT(device_id) DO UPDATE SET payload=excluded.payload,updated=excluded.updated',(principal.device_id,user,encode(previous),now))
            db.execute('DELETE FROM natural_device_status WHERE updated<?',(now-86400,))
        return {'stored':True,'contents_collected':False}

    def list(self,principal):
        n=self.natural;now=n.store.clock();items=[]
        with n.store.transaction(principal) as (db,user):
            rows=db.execute("SELECT x.device_id,x.payload,d.name,s.payload AS consent FROM natural_device_status x JOIN auth_devices d ON d.id=x.device_id LEFT JOIN natural_settings s ON s.user_id=x.user_id AND s.device_id=x.device_id AND s.scope='device' WHERE x.user_id=? AND x.updated>=? AND d.trusted=1 AND d.revoked_at IS NULL",(user,now-86400)).fetchall()
        for row in rows:
            consent=DeviceSettings.model_validate_json(row['consent']) if row['consent'] else DeviceSettings()
            data=self.visible(json.loads(row['payload']),consent,now);visible={}
            for key,entry in data.items():
                age=now-entry['received_at']
                if key=='location':age=max(age,now-entry['value']['sampled_at'])
                visible[key]={**entry,'stale':age>120,'age_seconds':max(0,round(age))}
            if visible:items.append({'device_id':row['device_id'],'name':row['name'],'status':visible})
        return {'items':items}
