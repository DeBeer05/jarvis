# Uitjesplanning binnen fase 7.5

Een uitje begint als een gesprek, ook als datum, vervoer of bestemming nog
onbekend zijn. `ActivityPlanningManager` bewaart één bron-gelabeld concept per
eigenaar en gesprek. Windows, Android, tekst, spraak en providerwisselingen
gebruiken hetzelfde concept via de bestaande chatroute op poort 8765.

De oude agenda-toolplanner moest eerst een uitvoerbaar CalendarCreate-object
maken. De validatie daarvan vroeg om ontbrekende verplichte tijden en titels;
brainstormen had geen apart gedeeld concept. Een ruimere prompt alleen lost
die koppeling niet op. De nieuwe laag bewaart onvolledige plannen vóór het
aanroepen van een uitvoerende tool. Bestaande expliciete agendaopdrachten en
exacte goedkeuringsantwoorden behouden hun bestaande route.

## Componenten

| Component | Verantwoordelijkheid |
|---|---|
| `planning_models.py` | Begrensde feiten, alternatieven, kosten en conceptstatus |
| `planning_extract.py` | Meerdere Nederlandse gegevens en wijzigingen uit één beurt |
| `planning_math.py` | Decimal-kosten, vrije blokken, marges en voorlopig tijdschema |
| `planning.py` | Context, opslag, huidige rechten, één generatie en gesloten toolbruggen |
| Context/Settings/ApprovalManager | Bestaand geheugen, persoonlijkheid, voorkeuren en autorisatie |
| Native clients | Overzicht en wijzigingen via dezelfde centrale chat |

`natural_pending(kind=activity_plan)` gebruikt de bestaande SQLite-database,
gesprekseigenaar, revisievergelijking en request-id. Geen tweede database of
backend. Zonder geschiedenis blijft het concept alleen in de begrensde
RAM-context en verloopt het. Bronnen die worden vergeten maken afgeleide
planning onbruikbaar; retentie verwijdert oude concepten. Het concept bevat
geen toegangstokens, volledige Google-afspraken of nieuwe actierechten.

Feiten onderscheiden `user`, `preference`, `proposal`, `assumption`,
`verified` en `unknown`. Een model mag alleen beschrijvende activiteit-/eet-
voorstellen en alternatieven produceren. Het kan geen ontvanger, prijs,
goedkeuring, externe status of toolopdracht toevoegen. Datum-/tijdcorrecties,
personen, kosten en externe payloads worden buiten het model gevalideerd.

## Beschikbare koppelingen

De eigen Google-agenda kan met bestaande apparaat- en toolrechten worden
gelezen. Onvolledige pagina's, ontbrekende tijdzones en leesfouten betekenen
geen bevestigde vrije tijd. Een gecachte controle blijft maximaal 120 seconden
bruikbaar na een nieuwe rechtencontrole; vóór een schrijfvoorstel wordt opnieuw
gelezen. Vrije tijd betreft uitsluitend de gecontroleerde eigenaaragenda.

CalendarCreate maakt één gecombineerd item van het voorlopige tijdschema,
inclusief besproken eten/extra activiteiten en bekende reistijd. De volledige
preview toont het exacte bereik. Er worden geen deelnemers uitgenodigd op basis
van alleen een naam. Een nieuwe expliciete opdracht is nodig om een bestaande
uitgevoerde afspraak te wijzigen. Meerdere losse agenda-items, automatische
reserveringen en betalingen zijn niet toegevoegd.

Contact Manager en Gmail kunnen op expliciet verzoek een bericht voorbereiden.
De huidige voorkeur bepaalt alleen concept bewaren of een verzendvoorstel
voorbereiden. De bestaande Gmail-draftverificatie en exacte eenmalige approval
blijven gelden. Herhaald voorbereiden van hetzelfde bericht/agenda-item gebruikt
de bestaande taak. Positieve belangstelling zoals ‘dat klinkt leuk’ geeft geen
toestemming voor een externe wijziging.

Er zijn in de headless gesloten registry geen zoek-, weer-, route-, ticket-,
restaurant-, WhatsApp- of Signal-adapters. Het overzicht benoemt die gegevens
als ongecontroleerd. Een door de gebruiker genoemd regenbericht kan een
binnenalternatief sturen, maar geldt niet als live weerscontrole. Voorwaardelijk
‘na zijn bevestiging in de agenda’ wordt als handmatig op te volgen stap bewaard;
er wordt geen nieuwe automatische bevestigingskoppeling gesimuleerd.

## Model en middelen

Qwen2.5:3B blijft het lokale uitgangspunt. Eén bestaande routergeneratie per
planningsbeurt, compacte planning, maximaal vier alternatieven en begrensde
geschiedenis. Native Ollama krijgt uitsluitend voor deze aanvraag een JSON-schema;
andere desktopcallers veranderen niet. Rekenen, bronlabels en korte weergave
komen uit de daadwerkelijke planning, zonder tweede samenvattingsgeneratie.
De bestaande persoonlijkheidscontext en speech/TTS-router blijven in gebruik.
Een ongeldig modelobject bewaart de gebruikersfeiten en meldt het ontbrekende
bruikbare voorstel. Geen impliciete modeldownload of modelvervanging.

Kosten rekenen alleen met opgegeven bedragen en aantallen. Brandstof kan worden
afgeleid uit opgegeven totale afstand, liter/100 km en euro/liter. Een bekende
deelsom is geen volledig totaal. Onbekende entrees, tussenritten en openingstijden
blijven open; het schema is voorlopig en bevat pauzemarges. Een volledig
realistisch, geverifieerd reisplan vereist de ontbrekende gegevens/koppelingen.

Zie [gespreksgedrag](CONVERSATIONAL_PLANNING.md),
[instellingen](PLANNING_SETTINGS.md) en [testresultaten](PLANNING_TEST_REPORT.md).
