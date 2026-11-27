"""Revisioned, synchronized personal preferences, never a credential store."""
from copy import deepcopy

from server.natural.models import UserSettings, DeviceSettings
from server.natural.store import Conflict, encode

SCHEMA_VERSION=1
CATEGORIES={
    "planning":"Uitjes en planning",
    "responses":"Antwoordgedrag",
    "general":"Algemeen", "conversations":"Gesprekken", "listening":"Luisteren",
    "voice":"Spraak en stem", "personality":"Persoonlijkheid", "ai":"AI en prestaties",
    "memory":"Geheugen", "calendar":"Agenda", "tasks":"Taken en automatiseringen",
    "autonomy":"Zelfstandigheid en machtigingen", "notifications":"Meldingen",
    "privacy":"Privacy", "diagnostics":"Diagnostiek",
}


class SettingsManager:
    def __init__(self, store):self.store=store

    @staticmethod
    def model(scope):
        if scope=="user":return UserSettings
        if scope=="device":return DeviceSettings
        raise ValueError("Onbekende instellingencontext")

    def get(self, principal, scope="user"):
        model=self.model(scope);device=principal.device_id if scope=="device" else ""
        with self.store.transaction(principal) as (db,user):
            row=db.execute("SELECT * FROM natural_settings WHERE user_id=? AND scope=? AND device_id=?",(user,scope,device)).fetchone()
            data=model.model_validate_json(row["payload"]).model_dump(mode="json") if row else model().model_dump(mode="json")
        return {"schema_version":SCHEMA_VERSION,"scope":scope,"revision":row["revision"] if row else 0,"updated_at":row["updated"] if row else None,"settings":data}

    def replace(self, principal, data, revision, scope="user"):
        model=self.model(scope);validated=model.model_validate(data).model_dump(mode="json")
        if scope=="user":
            from server.natural.capabilities import voice_capabilities
            from server.natural.personality import PROFILES
            previous=self.get(principal)["settings"]
            from server.natural.responses import RESPONSE_PROFILES
            response=validated['responses']
            if response['profile']!=previous['responses']['profile']:
                for key,value in RESPONSE_PROFILES[response['profile']].items():
                    if response[key]==previous['responses'][key]:response[key]=value
            notification=validated["notifications"];old_notification=previous["notifications"]
            levels={"off":3,"minimal":1,"normal":3,"proactive":5,"very_proactive":10}
            if notification["proactivity"]!=old_notification["proactivity"] and notification["suggestions_per_hour"]==old_notification["suggestions_per_hour"]==levels[old_notification["proactivity"]]:
                notification["suggestions_per_hour"]=levels[notification["proactivity"]]
            from server.natural.performance import PROFILES as PERFORMANCE
            ai=validated["ai"]
            if ai["performance"]!=previous["ai"]["performance"]:
                for key,value in PERFORMANCE[ai["performance"]].items():
                    if ai[key]==previous["ai"][key]:ai[key]=value
            personality=validated["personality"]
            if personality["profile"]!=previous["personality"]["profile"]:
                for key,value in PROFILES[personality["profile"]][1].items():
                    if personality[key]==previous["personality"][key]:personality[key]=value
            before=previous["voice"];voice=validated["voice"];available=voice_capabilities()
            premium=voice['mode'] not in ('local','offline') and (voice['mode'] in ('premium','budget') or voice['tts_provider']=='elevenlabs')
            if premium and voice['elevenlabs_model'] in ('eleven_flash_v2_5','eleven_multilingual_v2'):voice['speed']=min(1.2,voice['speed'])
            if premium and voice['elevenlabs_model'].startswith('eleven_v3'):voice['elevenlabs_stability']=min((0.,.5,1.),key=lambda value:abs(value-voice['elevenlabs_stability']))
            from server.natural.tts import PROFILES as VOICE_PROFILES
            if voice["profile"]!=before["profile"]:
                for key,value in VOICE_PROFILES[voice["profile"]].items():
                    if voice[key]==before[key]:voice[key]=value
            if voice["mode"]=="manual" and voice["tts_provider"]!='elevenlabs' and voice["tts_provider"] not in available.get("tts_providers",["piper"]):raise ValueError("Spraakprovider niet geïnstalleerd")
            for key,choices in (("whisper_model",available["whisper_models"]),("voice",available["voices"])):
                if voice[key]!=before[key] and not choices.get(voice[key],False):raise ValueError("Kies een geïnstalleerd spraakmodel of stemprofiel")
        payload=self.store.safe_content(encode(validated));device=principal.device_id if scope=="device" else ""
        with self.store.transaction(principal,write=True) as (db,user):
            row=db.execute("SELECT revision FROM natural_settings WHERE user_id=? AND scope=? AND device_id=?",(user,scope,device)).fetchone()
            actual=row["revision"] if row else 0
            if revision!=actual:raise Conflict("Instellingen elders gewijzigd; ververs eerst")
            db.execute("INSERT INTO natural_settings VALUES (?,?,?,?,?,?) ON CONFLICT(user_id,scope,device_id) DO UPDATE SET revision=excluded.revision,payload=excluded.payload,updated=excluded.updated",(user,scope,device,actual+1,payload,self.store.clock()))
            self.store.audit(db,user,principal.device_id,"settings_updated",scope)
        return self.get(principal,scope)

    def patch(self,principal,category,changes,revision,scope="user"):
        current=self.get(principal,scope);data=deepcopy(current["settings"])
        if scope=="user":
            if category not in CATEGORIES or not isinstance(changes,dict):raise ValueError("Onbekende categorie")
            data[category]={**data[category],**changes}
        else:
            if category!="device":raise ValueError("Onbekende apparaatcategorie")
            data.update(changes)
        return self.replace(principal,data,revision,scope)

    def reset(self,principal,revision,category=None,scope="user"):
        defaults=self.model(scope)().model_dump(mode="json")
        if category is not None:
            if scope!="user" or category not in CATEGORIES:raise ValueError("Onbekende categorie")
            return self.patch(principal,category,defaults[category],revision,scope)
        return self.replace(principal,defaults,revision,scope)

    def export(self,principal,scope="user"):
        result=self.get(principal,scope)
        return {"schema_version":SCHEMA_VERSION,"scope":scope,"settings":result["settings"]}

    def import_data(self,principal,data,revision):
        if set(data)!={"schema_version","scope","settings"} or data["schema_version"]!=SCHEMA_VERSION:raise ValueError("Onbekende exportversie")
        return self.replace(principal,data["settings"],revision,data["scope"])

    @staticmethod
    def schema():
        from server.automation.models import REGISTRY
        from server.natural.labels import LABELS,VALUES
        from server.natural.capabilities import voice_capabilities
        capabilities=voice_capabilities();user=UserSettings.model_json_schema()
        from server.natural.elevenlabs import CONTROLS,MODELS
        fields=user['$defs']['Voice']['properties']
        for name,field in fields.items():
            field['title']=LABELS.get(name,field.get('title',name))
            if name.startswith('elevenlabs_'):field['x-voice-visible']={'premium':True}
            if name in ('voice','speaker','supertonic_voice','steps','pause_ms'):field['x-voice-visible']={'premium':False}
        for name in ('elevenlabs_stability','elevenlabs_similarity','elevenlabs_style','elevenlabs_speaker_boost'):
            fields[name]['x-voice-visible']['models']=[model for model in MODELS if name in CONTROLS[model]]
        fields['speed']['x-voice-visible']={'speed_models':[model for model in MODELS if 'speed' in CONTROLS[model]]}
        fields['elevenlabs_model']['x-voice-visible']['exclude_modes']=['budget']
        for key,field in user['$defs']['ActivityPlanning']['properties'].items():
            field['title']=LABELS.get(key,field.get('title',key))
        for key,choices in (("whisper_model",capabilities["whisper_models"]),("voice",capabilities["voices"])):
            user["$defs"]["Voice"]["properties"][key]["x-unavailable"]=[name for name,present in choices.items() if not present]
        user["$defs"]["Voice"]["properties"]["tts_provider"]["x-unavailable"]=[key for key in ("piper","supertonic") if key not in capabilities.get("tts_providers",["piper"])]
        user["$defs"]["Voice"]["properties"]["supertonic_voice"]["x-unavailable"]=[key for key in ("M1","M2","M3","M4","M5") if not capabilities.get("supertonic_voices",{}).get(key,False)]
        return {"schema_version":SCHEMA_VERSION,"categories":CATEGORIES,"labels":LABELS,"values":VALUES,"voice_capabilities":capabilities,"user":user,"device":DeviceSettings.model_json_schema(),"actions":[*sorted(REGISTRY),"MemorySave","MemoryUpdate"],"mandatory_approval":[name for name,(_,required) in REGISTRY.items() if required]}
