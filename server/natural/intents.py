"""Closed, source-bound decomposition; this planner never executes a tool."""
import json
import re
from typing import Literal

from pydantic import Field,model_validator

from server.natural.models import StrictModel

KINDS={
    "calendar_read":frozenset({"CalendarList","CalendarRead"}),
    "calendar_create":frozenset({"CalendarList","CalendarRead","CalendarCreate"}),
    "calendar_update":frozenset({"CalendarList","CalendarRead","CalendarUpdate"}),
    "calendar_delete":frozenset({"CalendarList","CalendarRead","CalendarDelete"}),
    "email_search":frozenset({"EmailSearch","EmailRead"}),
    "email_read":frozenset({"EmailSearch","EmailRead"}),
    "email_draft":frozenset({"EmailSearch","EmailRead","EmailDraft","EmailSend"}),
    "email_send":frozenset({"EmailSearch","EmailRead","EmailDraft","EmailSend"}),
    "reminder_create":frozenset({"ReminderList","ReminderCreate"}),
    "reminder_cancel":frozenset({"ReminderList","ReminderCancel"}),
    "workflow_status":frozenset({"WorkflowStatus"}),
}
WRITE_KIND={"calendar_create":"CalendarCreate","calendar_update":"CalendarUpdate","calendar_delete":"CalendarDelete",
            "email_draft":"EmailDraft","email_send":"EmailSend","reminder_create":"ReminderCreate","reminder_cancel":"ReminderCancel"}


class Intent(StrictModel):
    kind:Literal["calendar_read","calendar_create","calendar_update","calendar_delete","email_search","email_read","email_draft","email_send","reminder_create","reminder_cancel","workflow_status"]
    text:str=Field(min_length=1,max_length=8000)
    depends_on:list[int]=Field(default_factory=list,max_length=7)


class IntentPlan(StrictModel):
    steps:list[Intent]=Field(min_length=1,max_length=8)
    @model_validator(mode="after")
    def acyclic(self):
        for index,step in enumerate(self.steps):
            if len(set(step.depends_on))!=len(step.depends_on) or any(type(value)!=int or not 0<=value<index for value in step.depends_on):raise ValueError("Ongeldige taakafhankelijkheid")
        return self

    def validate_source(self,instruction,maximum,write_intent):
        if len(self.steps)>maximum:raise ValueError("Te veel opdrachten")
        cursor=0
        for step in self.steps:
            position=instruction.find(step.text,cursor)
            if position<0:raise ValueError("Opdracht is geen letterlijk deel van de gebruikerzin")
            cursor=position+len(step.text)
            tool=WRITE_KIND.get(step.kind)
            if tool and (not write_intent(tool,instruction) or not write_intent(tool,step.text)):raise ValueError("Geen expliciete schrijfopdracht")
        return self


def compound_candidate(message):
    message=re.sub(r'"[^"\n]*"|“[^”\n]*”|```[\s\S]*?```',"",message)
    # A mail body is content, not an extra instruction just because it contains
    # verbs. A separate task should precede the body or be a separate utterance.
    message=re.split(r"\b(?:tekst|berichttekst)\s*:?\s+",message,maxsplit=1,flags=re.I)[0]
    if not re.search(r"[,;]|\ben\b",message,re.I):return False
    commands=re.findall(r"\b(?:bekijk|toon|vertel|lees|maak|plan|verzet|verplaats|herinner|verstuur|verzend|schrijf|verwijder)\b",message,re.I)
    # A reminder relative to an appointment is one CalendarChange slot.
    if re.search(r"\b(?:tevoren|vooraf|ervoor)\b",message,re.I):
        commands=[value for value in commands if value.casefold()!="herinner"]
    return len(commands)>1


async def interpret(router,run,maximum,write_intent):
    schema=IntentPlan.model_json_schema()
    system=("Splits uitsluitend de huidige gebruikerszin in afzonderlijke opdrachten. Geef JSON volgens dit schema: "+json.dumps(schema)+
        " Neem text letterlijk en ongewijzigd over als opeenvolgende niet-overlappende stukken van de oorspronkelijke zin. "
        "Voeg geen gegevens, rechten, toestemming of nieuwe opdrachten toe. depends_on bevat alleen eerdere nulgebaseerde stapnummers als een stap werkelijk afhangt van het resultaat daarvan. "
        "Een afspraak met herinnering vooraf is één kalenderopdracht; splits die herinnering niet af. Bij één taak: één stap. Geen tools uitvoeren.")
    raw,provider=await router.bounded_result([{"role":"system","content":system},{"role":"user","content":run.message}],run.mode)
    plan=IntentPlan.model_validate_json(raw).validate_source(run.message,maximum,write_intent)
    return plan,provider
