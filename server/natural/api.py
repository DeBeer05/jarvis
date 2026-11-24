"""Personal settings and memory over the existing authenticated API."""
from uuid import UUID

from fastapi import APIRouter, Request, HTTPException
from typing import Literal
from pydantic import Field, ValidationError

from server.natural.models import StrictModel, MemoryInput, Personality, Voice
from server.natural.store import Conflict

router=APIRouter(prefix="/api/v1/natural")


def service(request):return request.app.state.natural


def result(call):
    try:return call()
    except Conflict:raise HTTPException(409,"Gegevens elders gewijzigd; vernieuw eerst") from None
    except ValidationError:raise HTTPException(422,"Controleer de velden en hun toegestane waarden") from None


class SettingPatch(StrictModel):
    revision:int=Field(ge=0)
    changes:dict


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
def voice_studio(request:Request):return service(request).tts.catalogue()


@router.post("/voice-studio/preview")
async def voice_preview(request:Request,body:VoicePreview):
    import asyncio,base64,time
    from copy import deepcopy
    from providers.speech_format import format_speech
    natural=service(request);principal=request.state.principal
    await asyncio.to_thread(natural.security.store.rate,"voice-preview:"+principal.device_id,20)
    voice=body.voice
    config=deepcopy((await asyncio.to_thread(natural.settings.get,principal))["settings"])
    config["voice"]=voice.model_dump(mode="json")
    config["voice"]["cache"]=False
    text=natural.store.safe_content(body.text);started=time.perf_counter()
    audio=await natural.tts.synthesize(request,format_speech(text,config["general"]["timezone"]),config)
    if not natural.security.store.live(principal):raise HTTPException(401,"Sessie niet meer geldig")
    raw=base64.b64decode(audio["audio"],validate=True)
    if len(raw)>5_000_000:raise HTTPException(413,"Stemvoorbeeld te groot; gebruik een kortere tekst")
    return {"audio":audio["audio"],"provider":audio["selected_provider"],"voice":audio["selected_voice"],"seconds":time.perf_counter()-started,"runtime_stats":audio.get("runtime_stats",{}),"saved":False,"microphone_used":False}
