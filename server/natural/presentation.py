"""Presentation choice only; it never grants tools or creates external files."""
import re


def outing_overview(message):
    text=message.casefold()
    if not re.search(r"\b(?:uitjes?|dagjes? uit|dagje weg|bezienswaardigheden|dagtrips?|dagtochten?|uitstapjes?)\b",text):return False
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
