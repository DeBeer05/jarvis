"""Small, source-labelled activity drafts. No credential or approval authority."""
from typing import Literal
from pydantic import Field,model_validator,field_validator
from server.natural.models import StrictModel

FIELDS=frozenset({'goal','activity','extra_activities','date','date_end','clock','daypart','participants','origin','destination','transport','budget','budget_scope','duration_minutes','flexible','environment','meal','pickup','maximum_distance_km','maximum_travel_minutes','preference','distance_km','travel_minutes','fuel_consumption','fuel_price'})


class Fact(StrictModel):
    value:str|float|int|bool|list[str]|None=None
    origin:Literal['user','preference','proposal','assumption','verified','unknown']='unknown'
    evidence:str=Field(default='',max_length=400)
    reference:str=Field(default='',max_length=100)
    source_turn:str=Field(default='',max_length=40)
    @field_validator('value')
    @classmethod
    def bounded(cls,value):
        if isinstance(value,str) and len(value)>600:raise ValueError('Planningswaarde te lang')
        if isinstance(value,list) and (len(value)>12 or any(len(item)>120 for item in value)):raise ValueError('Te veel deelnemers/onderdelen')
        return value


ActivityKind=Literal['dierentuin','pretpark','museum','bioscoop','restaurant','stedentrip','wandeling','escape room','bowlen','sport','date']


class Option(StrictModel):
    title:ActivityKind
    reason:str=Field(default='',max_length=350)
    environment:Literal['inside','outside','any']='any'
    @field_validator('title',mode='before')
    @classmethod
    def normalize(cls,value):return value.casefold() if isinstance(value,str) else value
    @field_validator('reason')
    @classmethod
    def no_unverified_numbers(cls,value):
        import re
        if re.search(r'https?://|www\.|€|\d+\s*(?:euro|km|kilometer|minuten)|\b(?:geopend van|entreeprijs|kost slechts)\b',value,re.I):
            return 'Praktische gegevens moeten nog worden gecontroleerd.'
        return value
    # Model suggestions have no prices, sources, reservations or availability.


class Cost(StrictModel):
    name:str=Field(min_length=1,max_length=80)
    amount:float=Field(ge=0,le=100000)
    quantity:int=Field(default=1,ge=1,le=100)
    basis:Literal['total','person']='total'
    origin:Literal['user','estimate']='user'
    quantity_known:bool=True


class PlanningState(StrictModel):
    status:Literal['brainstorm','draft','waiting','proposal','cancelled']='brainstorm'
    mode:Literal['together','automatic','surprise','budget','relaxed','detailed']='together'
    facts:dict[str,Fact]=Field(default_factory=dict,max_length=25)
    alternatives:list[Option]=Field(default_factory=list,max_length=4)
    costs:list[Cost]=Field(default_factory=list,max_length=12)
    excluded:list[str]=Field(default_factory=list,max_length=20)
    calendar:dict=Field(default_factory=dict)
    timeline:list[dict]=Field(default_factory=list,max_length=20)
    route:list[str]=Field(default_factory=list,max_length=12)
    warnings:list[str]=Field(default_factory=list,max_length=15)
    pending:list[str]=Field(default_factory=list,max_length=10)
    booking_status:Literal['not_booked']='not_booked'
    request_id:str=Field(default='',max_length=40)
    proposal_job_id:str=Field(default='',max_length=36)
    proposal_fingerprint:str=Field(default='',max_length=64)
    message_job_id:str=Field(default='',max_length=36)
    message_fingerprint:str=Field(default='',max_length=64)
    model_status:Literal['not_requested','valid','invalid','unavailable']='not_requested'
    @model_validator(mode='after')
    def known_fields(self):
        if not self.facts.keys()<=FIELDS:raise ValueError('Onbekend planningsveld')
        return self


class ProposedData(StrictModel):
    activity:ActivityKind|None=None
    meal:Literal['eten','restaurant','lunch','diner']|None=None


class PlanningReply(StrictModel):
    spoken:str=Field(min_length=1,max_length=300)
    options:list[Option]=Field(max_length=4)
    # A model may suggest descriptive fields only. They always remain proposals.
    proposals:ProposedData=Field(default_factory=ProposedData)
