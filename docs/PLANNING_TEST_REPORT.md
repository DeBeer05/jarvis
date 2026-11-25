# Testverslag natuurlijke uitjesplanning

25 november 2026. Fase 7.5, ontwikkeldesktop, localhost 8765.
Technische verificatie en menselijke gespreks-/luisteracceptatie staan los van
elkaar. Geen echte Google-accounttest, verzending, boeking of betaling gedaan.

## Oorzaken en herstel

De oude uitvoering probeerde een uitje direct als CalendarCreate te verwerken.
Verplichte toolvelden en ontbrekende brainstormstatus veroorzaakten het
formuliergesprek. Eerdere dagdeelproblemen zijn bovendien vóór de toolvalidatie
opgelost. Nu bewaart een aparte laag een onvolledig concept met bronlabels;
alleen een expliciete uitvoeringsopdracht gaat naar de bestaande tool/approval.
Een herkende datum of een enthousiaste reactie geeft geen nieuwe actierechten.

Een eerste echte Qwen-proef kopieerde schemas of gaf vrije tekst. Daarom heeft
de planning een aanvraaggebonden native JSON-schema gekregen. Een volgende
proef vond verkeerde tijden en verzonnen actuele gegevens in gesproken tekst.
De gesproken planningsfeiten worden daarom uit het daadwerkelijke concept
weergegeven; modelvoorstellen blijven als zodanig herkenbaar. Er is geen tweede
samenvattingscall en geen hardcoded antwoord op een van de testgesprekken.

## Technische controles

- Volledige serverreeks: 544 geslaagd in 256,14 s, inclusief de 10 al aanwezige
  eigenaarmailtests. Na de laatste kleine spraakweergavewijziging zijn de 88
  relevante regressies nogmaals geslaagd; remote CI controleert de commit apart.
  Gerichte nieuwe suite daarvoor: 33 geslaagd in 66,26 s,
  inclusief tien volledige gesprekken, gecombineerde activiteiten, contacten,
  geen dubbele berichten, instellingen, bronvergeten en retentie.
- Eerdere gerichte regressieronde: 80 geslaagd voor planning, bestaande
  agendagesprekken en providertransport; standaard desktoptransport verandert
  niet zonder expliciete schema-opt-in. Schema-context wordt ook na annulering
  teruggezet.
- Na de laatste brainstormweergave: alle 88 gerichte planning-, agenda- en
  providerregressies geslaagd (45,76 s).
- Windows: 126 tests geslaagd; portable build geslaagd. Rooktest: acht pagina's,
  echt Qt-venster, geen netwerkstart, microfoon of spraakhelper.
- Android: unit tests, lint, debug- en releasebuild ook na de leesbare
  deelnemersvoorkeuren geslaagd (2m 44s). Geen instrumentatie
  op een echte telefoon of nieuwe installatie als acceptatie geclaimd.
- Ruff, server-/client-mypy, pip check, repositorycheck, contractcheck en diffcheck
  geslaagd. Structurele checks zijn geen gespreksacceptatie.

Relevante veiligheidsproeven: enthousiasme zonder write; nieuwe exacte preview
na tijdwijziging; herhaald voorstel zonder dubbele taak; één expliciet ja;
onbekende beschikbaarheid bij leesfout/rechtenverlies; geen modelautorisatie;
eigenaargebonden GET; geschiedenis uit betekent geen duurzaam concept;
vergeten bronnen en verouderde concepten worden uitgesloten/verwijderd.

## Tien echte modelgesprekken

`scripts/benchmark_activity_planning.py --run` gebruikt een tijdelijke database,
synthetische personen/gegevens, de werkelijke provider en een gemockte lege
eigenaaragenda. De scheduler is uit. Voorstellen worden niet goedgekeurd.
Geen spraakmicrofoon, echte accounts, echte beschikbaarheid of live reisgegevens.

De eerste volledige verbeterde Qwen2.5:3B-proef bevatte 10 gesprekken × 3 beurten.
Alle planningobjecten waren geldig. Mediane gehele chatduur 2,274 s, maximum
5,733 s, zonder werkende CPU-begrenzing. Dit is geen CPU-/8GB-belofte.
Een kostenvervolg bleek nog als normale chat te worden gerouteerd; de actieve
vervolgroutering is daarna uitgebreid en opnieuw met de kosten-/budgettests
gecontroleerd. De onafhankelijke databasevraag bleef gewone chat.

| Gesprek | Gecontroleerd verloop | Opnieuw gegeven / onnodige vragen |
|---|---|---|
| 1 | Weekend brainstorm → dierentuin → dichterbij | 0 / 0 |
| 2 | Dagdeel, persoon, budget → zondag en uur later → eten | 0 / 0 |
| 3 | Date → verrassing → betaalbaar | 0 / 0 |
| 4 | Binnen met deelnemer → museum → museum verwijderen | 0 / 0 |
| 5 | Idee → klinkt leuk → expliciete agendaopdracht | 0 / 0; één vereiste approvalvraag |
| 6 | Utrecht met deelnemer → trein → iemand ophalen | 0 / 0 |
| 7 | Gemelde regen → museum → goedkoper | 0 / 0; gevonden vervolgrouting hersteld |
| 8 | Weekend → databasevraag → terug naar planning | 0 / 0 |
| 9 | Tickets per persoon → parkeren/budget → trein | 0 / 0; Decimal-herberekening apart getest |
| 10 | Romantisch idee → eten → concept stoppen | 0 / 0 |

De plannen bouwen gegevens op zonder verplichte vragenreeks. Realisme blijft
voorlopig: de lege testagenda bewijst geen echte vrije tijd, en prijzen/routes/
openingstijden zijn expliciet ongecontroleerd. De kwaliteit van vrij gegenereerd
Nederlands wisselde; geldige JSON is geen menselijke goedkeuring. De korte
weergave op basis van echte feiten voorkomt foutieve uitgesproken rekensommen.
Bij de CPU-herhaling vroeg de vrije modeltekst onnodig naar een voorkeur, ondanks
gegenereerde alternatieven. Ook de brainstormaankondiging wordt daarom nu uit de
daadwerkelijke modelopties weergegeven. Een nieuwe echte driebeurtencontrole
zonder CPU-begrenzing voltooide in 5,529 / 1,614 / 1,668 s met geldige planning;
de goedkoper-correctie bleef in budgetmodus en verzonnen vrije tekst werd niet
uitgesproken. Dat is een gerichte hercontrole, geen tweede volledige tientalreeks.

## CPU, geheugen en Gemini

De eerste poging om een CPU-meting te begrenzen bleek de al aangemaakte HTTP-
client niet te vervangen. Die cijfers zijn verworpen als CPU-meting. De helper
geeft de CPU-client nu expliciet aan de provider; iedere native aanvraag zet
`num_gpu=0`, vier CPU-threads en seed 42. In de aparte reeks zijn vier volledige
gesprekken (12 beurten) geldig afgerond: mediaan 24,942 s, minimum 14,660 s,
maximum/eerste beurt 43,264 s, onder ontwikkelbelasting. Vervolgens verliep de
synthetische toegangssessie. De geannuleerde beurt en resterende 401-antwoorden
zijn uit deze cijfers en de acceptatie uitgesloten. De benchmark vernieuwt nu
de sessie via de bestaande refreshroute en stopt bij een mislukte chatrespons.
Het gewijzigde kostenvervolg is apart met het echte CPU-model opnieuw getest:
20,467 / 19,677 / 13,878 s; drie voltooide beurten met geldige planning. De
goedkoper-correctie blijft nu in de gedeelde planning en zet budgetmodus aan.
Ollama rapporteerde 2270 MiB geladen modelruimte, 0 MiB VRAM, context 7168.
Dit is geen totale systeem-RAM- of piekmeting en geen test op de mini-pc.

Gemini is werkelijk geprobeerd met de bestaande configuratie. De gerichte
controle geeft HTTP 402 / RESOURCE_EXHAUSTED op alle drie beurten. Er is geen
bruikbaar Gemini-antwoord en dus geen geslaagde Gemini-kwaliteitsacceptatie.
Geen betaalde dienst, sleutel- of modelwisseling geactiveerd.

## Open acceptatie en grenzen

De eigenaar moet de nieuwe Windows-/Android-builds nog beluisteren en op de
eigen gegevens uitproberen. Test spraakherkenning, natuurlijke formuleringen,
onderbreken, overzicht synchroniseren en de exacte één-ja-preview. De bestaande
HyperX-/Windows-standaardroute is behouden. Geen model-, mini-pc- of productie-
deployment gedaan.

Live reis-/weergegevens, reserveringen, aankopen, deelnemersagenda's, meerdere
losse agenda-items en automatische inhoudelijke bevestigingsopvolging vereisen
nog echte beschikbare adapters of een vervolgimplementatie. De huidige code
claimt deze mogelijkheden niet. Definitieve ervaringsacceptatie staat daarom
open; technische tests alleen verklaren niet alle visiecriteria voltooid.
