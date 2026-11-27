# Persoonlijke butler — praktische acceptatie

Test op een ontwikkelinstallatie. Externe acties alleen met een eigen expliciet
testvoorstel en actuele rechten; technische transportmocks zijn geen accounttest.

## Fase 1: persoonlijkheid en geheugen

1. Kies Classic Butler, meneer en Ieder antwoord. Stel humor/formaliteit naar wens
   in; spreek over een drukke of vermoeiende dag. Beoordeel tact en lengte apart
   van technische tests. Een stemming is een vermoeden, geen opgeslagen diagnose.
2. Sla via ‘Onthoud …’ een onschuldig projectfeit of voorkeur op. Controleer het
   onder Geheugen; wijzig het en controleer dat de oude versie niet terugkomt.
3. Schakel onder Geheugen ‘Eerdere gesprekken gericht terugvinden’ in. Bespreek
   een fictief project, begin een nieuw gesprek en vraag naar dat project. Dit
   gebruikt alleen relevante opgeslagen gebruikersuitspraken, geen modelwaarheid.
4. Herstart backend/client en herhaal stap 3. Probeer ook een tweede gekoppeld
   apparaat. Zet synchronisatie uit: alleen bronnen met bekende eigen
   apparaatbinding mogen dan worden teruggevonden.
5. Verwijder het expliciete projectgeheugen en vraag opnieuw, ook in een gesprek
   dat dit eerder als context gebruikte. Bronvergeten blokkeert afgeleide context.
6. Zet geschiedenis uit en noem een nieuw fictief feit. Het mag later niet via
   deze zoekfunctie terugkomen. Verwijder een oud gesprek: de FTS-index volgt mee.
7. Test met cloud-AI terwijl cloudgeheugen uit staat: oude uitspraken gaan niet
   mee. Gevoelig geheugen blijft bij cloud altijd uitgesloten. Geen echte
   wachtwoorden, medische gegevens of sleutels gebruiken voor acceptatietests.

Technisch: migratie v9 gebruikt dezelfde SQLite-database met de bestaande
automatische pre-migratiebackup. FTS5 indexeert uitsluitend bestaande
gebruikersuitspraken; er is geen vectorservice, extra model of periodieke
samenvattingscall. Maximaal drie fragmenten van 480 tekens, binnen het bestaande
contextbudget. De functie is standaard uit en verandert geen cloudtoestemming.

Volgende fasen worden hier pas toegevoegd nadat ze zijn geïmplementeerd.

## Fase 2: aanwezigheid en modi

1. Kies bij globale instellingen Aanwezigheid en modi. Alle acht handmatige modi
   zijn beschikbaar. Werk beperkt lichte meldingen; Gaming/Afwezig/Slapen/Privé/
   Noodgeval tonen alleen urgente events. Onderweg laat belangrijke meldingen toe.
   Geen modus geeft extra actierechten of belt zelfstandig.
2. Zeg ‘Ik ga nu eten’, daarna ‘Ik ben weer terug’. Eén begroeting, passend bij
   de eerdere activiteit; een tweede ‘Ik ben terug’ herhaalt de begroeting niet.
   Herstart tussendoor om de persistente status te controleren.
3. Windows: tab Aanwezigheid op dit apparaat. Zet delen alleen zelf aan als u dat
   wilt. Activeer daarnaast globale automatische modi. Vergrendel/ontgrendel en
   controleer Afwezig → Normaal. De begroeting verschijnt stil in de actieve app.
   Ontvangstbewijs wordt lokaal bewaard; herstart mag haar niet opnieuw tonen.
4. Alleen na apart aanvinken: stel werk-/gameprocesnamen in (bijvoorbeeld
   `Code.exe`). Lokaal vergelijken; geen procesnamen of venstertitels naar backend.
   Trek toestemming in en controleer dat er geen nieuwe signalen worden geaccepteerd.
5. Android: Instellingen → Aanwezigheid. Delen staat uit. Na eigen opt-in worden
   lock/idle alleen in de voorgrond gerapporteerd. Achtergrond is in deze fase
   onbekend en vervalt na 120 seconden; er wordt geen aanwezigheid verzonnen.
6. Zet Privé aan. Nieuwe gesprekstekst ontbreekt in opgeslagen historie en lokale
   AI/spraak vervangt cloud/premium. Bij ontbrekende lokale modellen volgt een
   fout, nooit stilzwijgende cloudfallback. Voorkeuren voor normale modus blijven
   behouden. Oude historie en verplichte actie-/goedkeuringslogs worden niet gewist.
7. Schakel meldingen uit; ook eerder klaargezette terugkomstevents mogen niet
   verschijnen. Urgentie omzeilt geen apparaat- of uitvoeringsrechten.

Primaire API-bronnen: [Windows sessie-events](https://learn.microsoft.com/en-us/windows/win32/termserv/wm-wtssession-change),
[initiële WTS-status](https://learn.microsoft.com/en-us/windows/win32/api/wtsapi32/ns-wtsapi32-wtsinfoex_level1_w),
[idle in eigen sessie](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getlastinputinfo),
[Android systeemintents](https://developer.android.com/reference/android/content/Intent).

## Fase 3: briefings en persoonlijke assistentie

1. Vraag ‘Geef mijn ochtendbriefing’. Alleen bronnen waarvoor het apparaat
   rechten heeft worden gelezen. Ontbrekende bronnen worden herkenbaar gemeld;
   een conflictoplossing wordt voorgesteld en nooit als uitgevoerd gepresenteerd.
2. Stel Briefings in met de gewenste plaats, bronnen en tijden. Activeren van
   de planning vereist bestaande automationrechten. Appmeldingen werken zonder
   telefonie; bij kanaal bellen wordt de ontbrekende koppeling expliciet gemeld.
3. Ga afwezig en kom terug: één briefing met recente bronnen. Herhaald terugkomen
   levert geen dubbele verwerking; ingetrokken bronrechten verhinderen aflevering.
4. Zeg ‘Zet melk op mijn boodschappenlijst’ en vraag de lijst. Herhalen maakt
   geen tweede open regel. ‘Haal melk van mijn boodschappenlijst’ verwijdert die.
5. Lokale abonnementen leveren een overzicht per valuta, zonder wisselkoers of
   bankclaim. Gebruik fictieve bedragen voor een test. Financiële inhoud blijft
   onder bestaande gevoelige-inhoudregels vallen.
6. Verjaardagen/routines en sollicitaties gebruiken de bestaande taakengine.
   Wijzig/verwijder een gekoppelde regel: de oude reminder/watch wordt geannuleerd.
   Alleen geverifieerde Gmail-IDs kunnen aan antwoordopvolging worden gekoppeld.
   Een ontvangen reactie autoriseert nooit zelf verzending of een statusbeslissing.

De typed formulieren volgen fase 8; de beveiligde API is reeds beschikbaar.
Primaire bronnen: [Open-Meteo](https://open-meteo.com/en/docs),
[geocodering](https://open-meteo.com/en/docs/geocoding-api) en
[Phone Link notificatie-integratie](https://learn.microsoft.com/en-us/windows/apps/develop/windows-integration/phone-link-notification-integration).
