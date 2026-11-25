# Agenda en uitjes presenteren

## Agenda: alleen ontbrekende gegevens vragen

Een eenvoudige persoonlijke opdracht zoals ‘Ik wil een uitje met Sam toevoegen
voor 26 november 2030 om 2 uur smiddags tot 5 uur smiddags’ gaat rechtstreeks
naar de bestaande CalendarCreate-validatie en volledige serverpreview. De
toolplanner is voor deze beperkte vorm niet nodig. Dit is een voorstel, geen
uitgevoerde afspraak; alleen de eigenaar kan het ongewijzigde voorstel daarna
met één ja goedkeuren. De bestaande sessie-, apparaat-, fingerprint-, expiry-
en actuele rechtencontroles blijven gelden.

Bekende transcriptvormen zoals smiddags, Schmiddags en Schmiddag worden als
dagdeel verwerkt. Een aan de laatste taakvraag gebonden aanvulling wordt vóór
het opnieuw interpreteren van de oorspronkelijke tijd toegepast. Begin- en
eindtijd behouden elk hun eigen dagdeel. Onzekere woorden worden niet als
goedkeuring of tijdstip geraden. Named calendars, uitnodigingen en uitgebreidere
agendaopdrachten blijven via de bestaande planner lopen.

## Uitjes: korte spraak, volledige lijst in de app

Een expliciete vraag naar uitjesideeën gebruikt dezelfde chatgeneratie. Bij
spraak verschijnt eerst het bestaande speech-event met ‘Ik zet een aantal
uitjes voor u klaar. De lijst verschijnt hier in de app.’ De tekstgeneratie
maakt vervolgens een compacte genummerde lijst voor het scherm. Dezelfde
tekst blijft in de gespreksgeschiedenis; Windows en Android gebruiken hun
bestaande delta-/speechprotocol. De Windows-spraakpagina is ook aangepast: het
antwoordvak toont de volledige geschreven lijst, ook als alleen de aankondiging
wordt uitgesproken. Hiervoor is een nieuwe Windows-build gemaakt. Android
scheidt geschreven tekst en audio al en hoeft niet opnieuw geïnstalleerd te worden.

De lijst bevat activiteiten, waarom ze passen en praktische afwegingen. De
modelinstructie vraagt onzekerheden te benoemen: prijzen, openingstijden en
beschikbaarheid zijn niet automatisch gecontroleerd. Dit voegt geen zoekdienst,
boekingsfunctie, willekeurige plugin of code-uitvoering toe. Er wordt geen Word-
of Kladblokproces geopend. De aankondiging betekent dat het overzicht wordt
voorbereid, niet dat de lijst of een externe actie al gereed is.

Toolvoorstellen en expliciet volledig voorlezen behouden volledige spraak.
Annulering sluit de bovenliggende generator; de normale generatie-/spraakepochs
blijven gelden. Er is geen extra classificatie- of samenvattingsmodelcall, geen
extra audioqueue en geen modeldownload. Fase 7.5 / desktop-development blijft
de grens; geen mini-pc-migratie of publieke servertoegang.

## Validatie en menselijke acceptatie

- Synthetische tests controleren begin/einde, een dagdeelvervolg, één voorstel,
  één ja/nee, actuele schrijf-/goedkeuringsrechten en ontbrekende plannercalls.
- Presentatietests controleren vroege spraak vóór de modelwachttijd, volledige
  geschreven inhoud, annulering, gewone gesprekken en volledige toolspraak.
- De gebruiker test op Windows en Android: een duidelijke agendaopdracht geeft
  één volledig voorstel, de uitjesvraag geeft een korte gesproken aankondiging
  en een leesbare lijst in de app, en Stop breekt een lopende generatie af.
- Geen echte Calendar-/Gmail-accounttest of externe wijziging uitgevoerd.
  Technische tests bewijzen de route; kwaliteit en hoorbare snelheid vragen
  afzonderlijke menselijke acceptatie.

Lokale bewijzen: de volledige serverreeks vóór de laatste hardening gaf 493
geslaagde tests (258,98 s, inclusief tien bestaande mailtests van de eigenaar).
Daarna slaagden 50 gerichte tests voor de taak-/presentatieroutes en bestaande
gesprekservaring. Ruff/mypy, afhankelijkheden, repositorystructuur, diff- en
settingscontractcontroles slaagden. De uiteindelijke collectie bevat 503 lokale
tests; de gepubliceerde tree sluit de tien eigenaarmailtests uit.
De volledige Windows-clientreeks slaagde met 124 tests, inclusief de controle
dat latere korte speech-events de geschreven lijst niet overschrijven.

Een echte begrensde CPU-only Qwen2.5:3B-proef met 8192 contexttokens gaf eerste
tekst na 13,64 s en 240 tokens na 30,10 s. Dit is geen hoorbare eind-tot-eindmeting.
De lijst bevatte slecht Nederlands en ongefundeerde prijsindicaties: geen
kwaliteitsacceptatie. De schermprompt is daarop aangescherpt met gewone
Nederlandse activiteitvoorbeelden en zonder bedragen/openingstijden. Eén eerdere
automatische GPU-proef had een leestimeout; de oorzaak is niet vastgesteld.
Geen ander model of productie-instelling gekozen. Ruwe synthetische proeftekst
blijft alleen onder `.local/experience-outings/`.
