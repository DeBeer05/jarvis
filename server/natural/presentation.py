"""Presentation choice only; it never grants tools or creates external files."""
import re


def outing_overview(message):
    text=message.casefold()
    topic=bool(re.search(r"\b(?:uitjes?|dagjes? uit|dagje weg|bezienswaardigheden|dagtrips?|dagtochten?|uitstapjes?|activiteiten)\b",text))
    # Recognize the activity question as well as its noun. STT may turn
    # 'uitjes om te doen' into 'uiten soms te doen'; this changes presentation
    # only and never rewrites user text or authorizes an action.
    activity_question=bool(re.search(r"\b(?:leuk\w*|gezellig\w*)\b.{0,70}\b(?:te\s+)?doen\b",text))
    if not (topic or activity_question):return False
    if re.match(r"\s*(?:wat (?:is|betekent)|hoe werkt|leg\b)",text):return False
    if re.search(r"\b(?:agenda|afspraak|toevoeg\w*|inplan\w*|boek\w*|annuleer\w*|verzet\w*)\b",text):return False
    return bool(re.match(r"\s*(?:jarvis[, ]+)?(?:zoek\w*|bedenk\w*|geef|toon|welke|wat|kan|kun|wil|zou|ik (?:wil|zoek|zou))\b",text))


OVERVIEW_PROMPT=(
    " Maak het gevraagde uitjesoverzicht voor het scherm: een compacte genummerde lijst "
    "met per uitje de activiteit, waarom die past en een praktische afweging. "
    "Gebruik de genoemde plaats, gezelschap, beschikbare tijd en budget. "
    "Vul ontbrekende voorkeuren niet in als feiten; geef bruikbare ideeën met duidelijke aannames. "
    "Er is hier geen live zoekresultaat: noem geen bedragen, prijsklassen, openingstijden "
    "of gegarandeerde beschikbaarheid. Vermeld eenmaal dat actuele praktische gegevens "
    "nog gecontroleerd moeten worden. Geef geen verzonnen bronnen. "
    "Gebruik gewone Nederlandse activiteitnamen, bijvoorbeeld een wandeling in een park, "
    "een museumbezoek of samen bowlen. Per nummer: activiteit; waarom passend; praktische afweging. "
    "De app toont deze lijst; spreek hem niet volledig uit. Claim geen reservering, "
    "agendawijziging, webonderzoek of geopend Word-/Kladblokdocument. "
)

ANNOUNCEMENT="Ik zet een aantal uitjes voor u klaar. De lijst verschijnt hier in de app. "
