"""Personal settings and memory over the existing authenticated API."""
from uuid import UUID

from fastapi import APIRouter, Request, HTTPException
from pydantic import Field, ValidationError

from server.natural.models import StrictModel, MemoryInput
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
