# Instellingen gebruiken — fase 7.5 in uitvoering

Gebruik deze handleiding bij de nieuwe fase-7.5-clientbuild en bijbehorende server.
De bestaande geïnstalleerde apps zijn tijdens de implementatie niet automatisch vervangen.

## Openen

Windows: **Instellingen → Gesprekken en geheugen → Gespreksinstellingen**.
Kies links een categorie of zoek een instelling. Het andere tabblad beheert geheugen
en samenvattingen. Het tabblad **Deze Windows-app** behoudt de lokale verbinding,
vormgeving, systeemvak en opstartinstellingen.

Android: **Instellingen**, daarna **Gesprekken en geheugen** onder de bestaande
apparaatvoorkeuren. Kies Instellingen of Geheugen en selecteer een categorie.
De globale voorkeuren komen van dezelfde server als op Windows.

## Opslaan en synchroniseren

Pas velden aan en kies **Opslaan**. **Annuleren** verwijdert alleen je lokale,
niet-opgeslagen invoer. Standaardwaarden en import vereisen eerst opslaan of
annuleren, zodat andere invoer niet stilzwijgend verloren gaat.

Bij wijzigingen op een ander apparaat geeft de server een conflict. Vernieuw
en vergelijk opnieuw; er wordt niet blind opnieuw opgeslagen. Globale voorkeuren
worden bij inloggen en periodiek opgehaald. Microfoon-/luidsprekerkeuze en echte
OS-toestemming blijven per apparaat apart.

**Exporteren** bewaart niet-geheime instellingen via een bestandsdialoog.
**Importeren** valideert dezelfde versie en vraagt bevestiging. Het bestand kan
persoonlijke aanspreeknamen of eigen instructies bevatten; deel het bewust.
Sla er nooit sleutels, wachtwoorden of OAuth-tokens in op.

## Gesprekken en stem

Op Windows en Android kun je doorlopende gesprekken inschakelen in Gesprekken. Dit is geen
toestemming om bij opstart te gaan opnemen. Geef lokaal microfoontoestemming en
activeer met de spreekknop of de bewust ingeschakelde wakefrase. Een actief gesprek
kan vervolgens meerdere beurten behouden en stopt bij afscheid, Stop alles of timeout.

Wakefraseherkenning gebruikt nu transcriptie van een hele uitspraak. Het is geen
afzonderlijk altijd-aan wakewordmodel. Stem-/microfoontests open je met de knop naar
Spraak. Ontbrekende modellen staan uitgeschakeld; er wordt niets stilzwijgend gedownload.

Persoonlijkheidsprofielen sturen de gesproken antwoordstijl. Ze veranderen geen
apparaatrechten of verplichte goedkeuringen. Offline forceert Ollama voor AI,
ook bij interne planners/samenvattingen. Zonder beschikbaar lokaal model wordt
een fout gemeld en geen cloudfallback gestart.

Android stopt bij verlaten van de app en hervat de microfoon niet vanzelf. Beide
clients gebruiken bij Natural Conversation Mode de servermodellen; hardwarekeuze
en microfoontoestemming blijven lokaal. Android gebruikt beschikbare platform-
echo-/ruisonderdrukking; de kwaliteit vereist een echte audioproef.
Optionele spraakonderbreking is aangesloten; echte hardwareacceptatie en overige
instellingen worden nog afgerond. Raadpleeg de actuele
voortgang; fase 7.5 is nog niet voltooid.

Een ander persoonlijkheidsprofiel past bij opslaan de bijbehorende standaardwaarden
toe. Sliders die je in dezelfde wijziging expliciet anders hebt ingesteld blijven
behouden. Je kunt de opgeslagen waarden daarna verder aanpassen.

Bij Geheugen kun je automatisch verzamelen, geschiedenis en bewaartermijnen instellen.
Nieuwe privébeurten blijven bij geschiedenis uit alleen tijdelijk in server-RAM;
Android schakelt dan de offline cache uit. Openstaande taken houden noodzakelijke
gegevens apart. De opruiming verwerkt begrensde aantallen oude gegevens per minuut.
Oorspronkelijke gesprekken verwijderen en geheugen wissen zijn aparte keuzes.

De extra tab **Diagnostiek** toont echte beschikbare metingen. Ververs of exporteer
de cijfers zonder gespreksinhoud. Niet beschikbare GPU-/audiometingen blijven als
onbekend zichtbaar. Een responstijd van 1–3 seconden is een doel, geen garantie.

Een prestatieprofiel past bij opslaan het contextbudget, de maximale antwoordlengte
en de AI-time-out toe. Energiebesparend gebruikt 2048/512 tokens en 60 seconden;
Gebalanceerd 6000/1024 en 60 seconden; Lage latency 4000/512 en 45 seconden;
Hoge kwaliteit 10000/2048 en 90 seconden. Aangepast behoudt je eigen waarden.
Waarden die je tegelijk expliciet wijzigt blijven behouden. Een kleiner budget
beperkt context/antwoordlengte, maar garandeert geen bepaalde snelheid. Er wordt
geen model gedownload of automatisch door een groter model vervangen.

Bij Agenda beïnvloeden werkdagen, werktijden en buffertijd de voorgestelde
alternatieve tijden voor een verplaatsing. Alternatieven en naburige afspraken
kunnen afzonderlijk worden getoond/uitgeschakeld. Een alternatief is een voorstel,
geen automatisch uitgevoerde wijziging. De bestaande controle op overlappende
afspraken vóór uitvoering blijft actief, evenals de exacte goedkeuring.

Bij Meldingen sturen aan/uit, rustige uren en tijdzone het aanmaken/inplannen
van nieuwe automatiseringsmeldingen. Proactiviteit uit en nul suggesties per uur
onderdrukken automatische agenda-/mail-/follow-upmeldingen. Expliciet gevraagde
herinneringen staan daar los van; de algemene meldingenschakelaar geldt wel.
Eerder opgeslagen meldingen blijven in de bestaande inbox staan. Deze instelling
verwijdert geen geschiedenis en verandert geen systeembeveiligingsmeldingen.
