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

Op Windows kun je doorlopende gesprekken inschakelen in Gesprekken. Dit is geen
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

Android-doorloop, echo-/barge-infuncties en resterende instellingen worden nog
aangesloten. Raadpleeg de actuele voortgang; fase 7.5 is nog niet voltooid.
