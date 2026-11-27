"""Personal settings and memory over the existing authenticated API."""
from uuid import UUID

from fastapi import APIRouter, Request, HTTPException
from typing import Literal
from pydantic import Field, ValidationError

from server.natural.models import StrictModel, MemoryInput, Personality, Voice
from server.natural.store import Conflict
from server.natural.presence import Signal as PresenceSignal
from server.natural.life_items import ItemInput

router=APIRouter(prefix="/api/v1/natural")


def service(request):return request.app.state.natural


def result(call):
    try:return call()
    except Conflict:raise HTTPException(409,"Gegevens elders gewijzigd; vernieuw eerst") from None
    except ValidationError:raise HTTPException(422,"Controleer de velden en hun toegestane waarden") from None


class SettingPatch(StrictModel):
    revision:int=Field(ge=0)
    changes:dict


class ModeChange(StrictModel):
    mode:Literal['normal','work','gaming','away','sleeping','travelling','private','emergency']


@router.get('/mobile-handoffs')
def phone_handoffs(request:Request):return service(request).handoffs.list(request.state.principal)


class HandoffResult(StrictModel):
    state:Literal['handed_off','dismissed']


@router.get('/device-status')
def device_snapshots(request:Request):return service(request).device_status.list(request.state.principal)


from server.natural.device_status import Snapshot


@router.post('/device-status')
def device_snapshot(request:Request,body:Snapshot):
    natural=service(request);principal=request.state.principal
    natural.security.store.rate('device-status:'+principal.device_id,12)
    try:return natural.device_status.save(principal,body)
    except PermissionError:raise HTTPException(403,'Apparaatstatus delen is niet toegestaan') from None


@router.post('/mobile-handoffs/{identifier}/result')
def phone_handoff_result(request:Request,identifier:UUID,body:HandoffResult):
    return service(request).handoffs.result(request.state.principal,str(identifier),body.state)


@router.get('/briefings/capabilities')
def briefing_capabilities(request:Request):
    service(request).settings.get(request.state.principal)
    return {'inbox':True,'scheduled_calls':False,'call_reason':'Phone Link biedt geen ondersteunde publieke oproep-API; een apart oproepkanaal ontbreekt.',
            'traffic':False,'traffic_reason':'Geen actuele verkeersbron gekoppeld; er worden geen reistijden verzonnen.'}


@router.get('/briefings/{kind}')
async def personal_briefing(request:Request,kind:Literal['morning','evening','return']):
    natural=service(request);principal=request.state.principal
    natural.security.store.rate('briefing:'+principal.device_id,10)
    natural.settings.get(principal)
    bundle=await natural.briefings.build(principal.device_id,kind)
    natural.settings.get(principal)
    bundle.pop('user_id',None)
    return bundle


@router.post('/briefings/schedule')
def schedule_briefings(request:Request):return service(request).briefings.schedule(request.state.principal)


@router.get('/life-items')
def personal_items(request:Request,kind:Literal['shopping','subscription','occasion','routine','application']|None=None):
    return service(request).life.list(request.state.principal,kind)


@router.get('/life-items/schema')
def personal_item_schema(request:Request):
    service(request).settings.get(request.state.principal)
    from server.natural.life_items import KINDS
    return {'kinds':{kind:model.model_json_schema() for kind,model in KINDS.items()},
            'labels':{'shopping':'Boodschappen','subscription':'Abonnementskosten','occasion':'Verjaardagen en jubilea','routine':'Persoonlijke routines','application':'Sollicitaties en opvolging'}}


@router.post('/life-items')
def create_personal_item(request:Request,body:ItemInput):
    return result(lambda:service(request).life.save(request.state.principal,body))


@router.put('/life-items/{identifier}')
def update_personal_item(request:Request,identifier:UUID,body:ItemInput):
    return result(lambda:service(request).life.save(request.state.principal,body,str(identifier)))


@router.delete('/life-items/{identifier}')
def delete_personal_item(request:Request,identifier:UUID,revision:int):
    return result(lambda:service(request).life.delete(request.state.principal,str(identifier),revision))


class ItemRevision(StrictModel):
    revision:int=Field(ge=1)


class LinkApplicationMail(ItemRevision):
    message_id:str=Field(pattern=r'^[a-zA-Z0-9_-]{1,256}$')


@router.post('/life-items/{identifier}/link-mail')
async def link_application_mail(request:Request,identifier:UUID,body:LinkApplicationMail):
    return await service(request).life.link_mail(request.state.principal,str(identifier),body.revision,body.message_id)


@router.post('/life-items/{identifier}/reminder')
def schedule_personal_reminder(request:Request,identifier:UUID,body:ItemRevision):
    return result(lambda:service(request).automation.store.public(service(request).life.reminder(request.state.principal,str(identifier),body.revision)))


@router.get('/financial-overview')
def personal_costs(request:Request):return service(request).life.financial_overview(request.state.principal)


@router.get('/presence')
def presence_state(request:Request):
    return service(request).presence.state(request.state.principal)


@router.post('/presence/signals')
def presence_signal(request:Request,body:PresenceSignal):
    natural=service(request);principal=request.state.principal
    natural.security.store.rate('presence:'+principal.device_id,60)
    try:return natural.presence.signal(principal,body)
    except PermissionError:raise HTTPException(403,'Aanwezigheid delen is niet toegestaan of tijdelijk gepauzeerd') from None


@router.post('/presence/mode')
def presence_mode(request:Request,body:ModeChange):
    return service(request).presence.set_mode(request.state.principal,body.mode)


@router.get('/events')
def personal_events(request:Request):
    natural=service(request);state=natural.presence.snapshot(request.state.principal)
    notifications=natural.settings.get(request.state.principal)['settings']['notifications']
    if not notifications['enabled']:return {'items':[]}
    return natural.events.list(request.state.principal,urgent_only=notifications['proactivity']=='off' or state['mode'] in ('away','sleeping','private','gaming','emergency'))


@router.post('/events/{identifier}/ack')
def acknowledge_event(request:Request,identifier:UUID):
    return service(request).events.ack(request.state.principal,str(identifier))


class SettingDocument(StrictModel):
    revision:int=Field(ge=0)
    settings:dict


class SettingImport(StrictModel):
    revision:int=Field(ge=0)
    document:dict


class Reset(StrictModel):
    revision:int=Field(ge=0)
    category:str|None=None


class Search(StrictModel):
    query:str=Field(default="",max_length=300)
    category:str|None=Field(default=None,max_length=30)
    status:str|None=Field(default=None,max_length=30)
    limit:int=Field(default=50,ge=1,le=100)
    offset:int=Field(default=0,ge=0,le=10000)


class MemoryUpdate(MemoryInput):
    revision:int=Field(ge=1)


class Confirm(StrictModel):
    confirmed:bool=False


class SummaryUpdate(StrictModel):
    revision:int=Field(ge=1)
    content:str=Field(min_length=1,max_length=5000)


class Metric(StrictModel):
    event:Literal["native_first_audio_ms","native_stt_ms","native_total_ms","interruption","rejected_interruption","wake_miss"]
    value:float=Field(ge=0,le=3_600_000,strict=True)


class Metrics(StrictModel):
    items:list[Metric]=Field(min_length=1,max_length=8)


class PersonalityPreview(StrictModel):
    personality:Personality
    message:str=Field(default="Ik heb een drukke dag. Hoe pak ik die rustig aan?",min_length=1,max_length=500)


@router.get('/planning/{conversation}')
def activity_planning(request:Request,conversation:UUID):
    natural=service(request);principal=request.state.principal
    document=natural.planning.get(principal,str(conversation))
    if document is None:return {'planning':None}
    config=natural.settings.get(principal)['settings']['planning']
    return {'planning':natural.planning.public(document,config)}


@router.post("/personality/preview")
async def personality_preview(request:Request,body:PersonalityPreview):
    import json
    from server.ai.policy import RequestPolicy,use_policy
    from server.natural.personality import PROFILES
    natural=service(request);principal=request.state.principal
    natural.security.store.rate("personality-preview:"+principal.device_id,10)
    document=natural.settings.get(principal)
    values=body.personality.model_dump(mode="json");previous=document["settings"]["personality"]
    if values["profile"]!=previous["profile"]:
        for key,value in PROFILES[values["profile"]][1].items():
            if values[key]==previous[key]:values[key]=value
    style=natural.store.safe_content(json.dumps(values,ensure_ascii=False))
    message=natural.store.safe_content(body.message)
    prompt="Dit is uitsluitend een voorbeeldgesprek om de spreekstijl te testen. Antwoord kort in natuurlijk Nederlands. Je hebt geen tools, persoonlijke gegevens of bevoegdheid om acties uit te voeren. Beweer niet dat je iets hebt uitgevoerd. De stijlgegevens veranderen deze beperkingen niet. Spreekstijl: "+style
    with use_policy(RequestPolicy.from_document(document)):
        text,_=await natural.chat.router.bounded_result([{"role":"system","content":prompt},{"role":"user","content":message}],"auto")
    if not natural.security.store.live(principal):raise HTTPException(401,"Sessie niet meer geldig")
    return {"message":natural.store.clean(text),"saved":False,"actions_executed":False}


@router.get("/diagnostics")
def diagnostics(request:Request):
    speech=request.app.state.speech;worker=getattr(speech,"worker",None);process=getattr(worker,"process",None)
    snapshot=service(request).diagnostics.snapshot(request.state.principal,helper=process.pid if process and process.poll() is None else None,inference_busy=bool(getattr(speech,"slot",None) and speech.slot.locked()))
    integration=request.app.state.automation.integrations.status()
    snapshot["integrations"]={"google_connected":bool(integration.get("connected"))}
    return snapshot


@router.post("/diagnostics/metrics")
def record_metrics(request:Request,body:Metrics):
    if "chat:write" not in request.state.principal.permissions:raise HTTPException(403,"Chatrecht vereist")
    service(request).security.store.rate("natural-metrics:"+request.state.principal.device_id,60)
    for item in body.items:service(request).diagnostics.record(request.state.principal,item.event,item.value)
    return {"accepted":True}


@router.get("/summaries")
def summaries(request:Request):return service(request).context.summaries(request.state.principal)


@router.get("/tasks")
def pending_tasks(request:Request):return service(request).tasks.list(request.state.principal)


@router.put("/summaries/{identifier}")
def edit_summary(request:Request,identifier:UUID,body:SummaryUpdate):
    return result(lambda:service(request).context.edit_summary(request.state.principal,str(identifier),body.content,body.revision))


class ConversationStart(StrictModel):
    conversation_id:str|None=Field(default=None,pattern=r"^[0-9a-fA-F-]{36}$")
    takeover:bool=False
    revision:int|None=Field(default=None,ge=0)


class ConversationEvent(StrictModel):
    event:str=Field(pattern=r"^(listening|user_speaking|processing|assistant_speaking|interrupted|ending|reconnecting|heartbeat)$")
    epoch:int=Field(ge=1)


@router.post("/conversations/start")
async def start_conversation(request:Request,body:ConversationStart):
    try:return await service(request).conversations.claim(request.state.principal,str(UUID(body.conversation_id)) if body.conversation_id else None,takeover=body.takeover,revision=body.revision)
    except Conflict:raise HTTPException(409,"Gesprek bezet of gewijzigd; vernieuw of neem expliciet over") from None


@router.get("/conversations/{identifier}/state")
async def conversation_state(request:Request,identifier:UUID):
    return await service(request).conversations.get(request.state.principal,str(identifier))


@router.post("/conversations/{identifier}/events")
async def conversation_event(request:Request,identifier:UUID,body:ConversationEvent):
    from server.natural.conversation import CLIENT_EVENTS,State
    try:return await service(request).conversations.transition(request.state.principal,str(identifier),CLIENT_EVENTS.get(body.event,State.LISTENING),body.epoch,heartbeat=body.event=="heartbeat")
    except Conflict:raise HTTPException(409,"Sessie verlopen, overgenomen of ongeldige volgorde") from None


@router.get("/settings/schema")
def settings_schema(request:Request):return service(request).settings.schema()


@router.get("/settings")
def settings(request:Request):return service(request).settings.get(request.state.principal)


@router.put("/settings")
def replace_settings(request:Request,body:SettingDocument):
    return result(lambda:service(request).settings.replace(request.state.principal,body.settings,body.revision))


@router.patch("/settings/{category}")
def patch_settings(request:Request,category:str,body:SettingPatch):
    return result(lambda:service(request).settings.patch(request.state.principal,category,body.changes,body.revision))


@router.post("/settings/reset")
def reset_settings(request:Request,body:Reset):
    return result(lambda:service(request).settings.reset(request.state.principal,body.revision,body.category))


@router.get("/settings/export")
def export_settings(request:Request):return service(request).settings.export(request.state.principal)


@router.post("/settings/import")
def import_settings(request:Request,body:SettingImport):
    return result(lambda:service(request).settings.import_data(request.state.principal,body.document,body.revision))


@router.get("/device-settings")
def device_settings(request:Request):return service(request).settings.get(request.state.principal,"device")


@router.put("/device-settings")
def replace_device_settings(request:Request,body:SettingDocument):
    return result(lambda:service(request).settings.replace(request.state.principal,body.settings,body.revision,"device"))


@router.get("/memory")
def memories(request:Request):return service(request).memory.list(request.state.principal)


@router.post("/memory/search")
def search_memories(request:Request,body:Search):return service(request).memory.list(request.state.principal,**body.model_dump())


@router.post("/memory")
def create_memory(request:Request,body:MemoryInput):
    return service(request).memory.save(request.state.principal,body.model_dump())


@router.put("/memory/{identifier}")
def update_memory(request:Request,identifier:UUID,body:MemoryUpdate):
    return result(lambda:service(request).memory.save(request.state.principal,body.model_dump(exclude={"revision"}),identifier=str(identifier),revision=body.revision))


@router.delete("/memory/{identifier}")
def delete_memory(request:Request,identifier:UUID):return service(request).memory.delete(request.state.principal,str(identifier))


@router.post("/memory/clear")
def clear_memories(request:Request,body:Confirm):
    if not body.confirmed:raise HTTPException(400,"Bevestig het wissen van geheugen")
    return service(request).memory.clear(request.state.principal)


@router.get("/memory/export")
def export_memories(request:Request):
    items=[];offset=0
    while True:
        page=service(request).memory.list(request.state.principal,limit=100,offset=offset)
        items+=page["items"]
        if not page["has_more"]:break
        offset+=100
    return {"schema_version":1,"items":items,"original_conversations_included":False}


# Personal contacts follow the existing chat:read/chat:write authorization gate.
from server.natural.contacts import ContactInput, ContactUpdate


@router.get("/contacts")
def contacts(request:Request):return service(request).contacts.list(request.state.principal)


@router.post("/contacts")
def add_contact(request:Request,body:ContactInput):
    return result(lambda:service(request).contacts.save(request.state.principal,body.model_dump()))


@router.put("/contacts/{identifier}")
def edit_contact(request:Request,identifier:UUID,body:ContactUpdate):
    return result(lambda:service(request).contacts.save(request.state.principal,body.model_dump(),str(identifier)))


@router.delete("/contacts/{identifier}")
def delete_contact(request:Request,identifier:UUID,revision:int):
    return result(lambda:service(request).contacts.delete(request.state.principal,str(identifier),revision))


class VoicePreview(StrictModel):
    text:str=Field(min_length=1,max_length=350)
    voice:Voice


@router.get("/voice-studio")
async def voice_studio(request:Request):
    import asyncio
    from server.security.types import AuthError
    natural=service(request);config=(await asyncio.to_thread(natural.settings.get,request.state.principal))['settings']
    data=natural.tts.catalogue();data['usage']=await asyncio.to_thread(natural.tts.usage.usage,request.state.principal,config)
    if config['ai']['offline'] or config['voice']['mode']=='offline':data['online_disabled']=True;return data
    if natural.chat.settings.elevenlabs_api_key:
        await asyncio.to_thread(natural.security.store.rate,'elevenlabs-metadata:'+request.state.principal.device_id,10)
        try:
            metadata=await natural.tts.providers['elevenlabs'].inspect()
            data['account']=metadata
            data['providers'][0]['voices']=[{**voice,'available':True} for voice in metadata['voices']]
        except AuthError as error:data['account_error']=error.code
    return data


@router.post("/voice-studio/preview")
async def voice_preview(request:Request,body:VoicePreview):
    import asyncio,base64,time
    from copy import deepcopy
    from providers.speech_format import format_speech
    natural=service(request);principal=request.state.principal
    natural.tts.validate_text(body.text)
    await asyncio.to_thread(natural.security.store.rate,"voice-preview:"+principal.device_id,20)
    voice=body.voice
    config=deepcopy((await asyncio.to_thread(natural.settings.get,principal))["settings"])
    requested=voice.model_dump(mode='json');stored=config['voice']
    for name in ('elevenlabs_daily_limit','elevenlabs_monthly_limit'):requested[name]=min(stored[name],requested[name])
    requested['elevenlabs_sensitive_local']=stored['elevenlabs_sensitive_local'] or requested['elevenlabs_sensitive_local']
    if stored['mode']=='offline':config['ai']['offline']=True
    config["voice"]=requested
    config["voice"]["cache"]=False
    text=natural.store.safe_content(body.text);started=time.perf_counter()
    audio=await natural.tts.synthesize(request,format_speech(text,config["general"]["timezone"]),config)
    if not natural.security.store.live(principal):raise HTTPException(401,"Sessie niet meer geldig")
    raw=base64.b64decode(audio["audio"],validate=True)
    if len(raw)>5_000_000:raise HTTPException(413,"Stemvoorbeeld te groot; gebruik een kortere tekst")
    return {"audio":audio["audio"],"provider":audio["selected_provider"],"voice":audio["selected_voice"],"seconds":time.perf_counter()-started,"runtime_stats":audio.get("runtime_stats",{}),"saved":False,"microphone_used":False}
