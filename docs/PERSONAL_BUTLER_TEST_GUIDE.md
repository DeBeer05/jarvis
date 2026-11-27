# Persoonlijke butler — praktische acceptatie

## Eerst proberen na de update

Start via uw bestaande JARVIS-snelkoppeling. De ontwikkelbronclient is apart
startbaar met `scripts/Start-WindowsClient.ps1`; de backend start daardoor niet.
Portable Windows-builds staan na een geslaagde workflow bij het gelijknamige
GitHub Actions-artifact en bevatten geen modellen of persoonlijke configuratie.
Een lokale exe-packagerblokkade verandert geen Windows-beveiligingsinstellingen.
Android-installatie vereist een werkelijk aangesloten en geautoriseerde telefoon;
een geslaagde APK-build geldt niet als installatie of luisteracceptatie.

1. Windows: Instellingen → Gesprekken en geheugen → Persoonlijke butler.
   Android: Gesprekken en geheugen → Butler. Open uw ochtend-/avondbriefing en
   de meldingengeschiedenis. Ontbrekende bronnen moeten eerlijk ontbreken.
2. Kies Persoonlijke lijsten/Lijsten. Maak een herkenbaar testboodschapje, wijzig
   het, vink het af en verwijder het zelf. Kies daarna een routine/gelegenheid;
   stel datum en tijd met de kiezer in en maak bewust een herinnering.
3. Voer een synthetisch abonnement in. Kostenoverzicht toont uitsluitend uw
   eigen bedragen per valuta; geen bankgegevens of geschatte wisselkoers.
4. Instellingen → Zelfstandigheid: kies expliciet Alleen adviseren voor een
   onschuldige functie. Een voorstel mag dan niet worden uitgevoerd. Profielregels
   erven en expliciet Eerst vragen zijn verschillende keuzes.
5. Bij Taken/Automatiseringen: controleer prioriteit, optionele deadline, approval,
   pauzeren en herstelvoorstel. Gebruik de noodstop met een onschuldige taak;
   hef hem zelf op in eigenaarbeheer en hervat taken afzonderlijk.
6. Windows: Beeldcontext. Android: Beeldcontext. Schakel globale beeldanalyse en
   de afzonderlijke apparaattoestemming zelf in. Selecteer uitsluitend een eigen
   onschuldig testbeeld, controleer preview/provider en verzend bewust. Cloud heeft
   een aparte toestemming nodig. Geen beeld wordt automatisch verzameld/opgeslagen.
7. Android → Butler → Apparaat: bepaal zelf welke status gedeeld mag worden.
   Meldingen zijn aantallen van geselecteerde apps, geen berichteninhoud. Android-
   toegang en locatie zijn aparte OS-toestemmingen. Achtergrondophalen is optioneel
   en Android mag het uitstellen; zonder push wordt geen exact tijdstip beloofd.
8. Eigenaarkoppelingen: open vanuit Taken/Accounts het bestaande eigenaarbeheer.
   Haal eerst de huidige vrijgave op. Wijzig uitsluitend uw bedoelde programma’s,
   documentmappen of HA-entiteiten. Sleutels voert u lokaal beveiligd in, nooit in
   clientvelden, Git of deze chat. Zie EXTERNAL_INTEGRATIONS.md.

## Praktische grenzen

- Telefonie ontbreekt; briefings blijven in JARVIS. Phone Link is geen openbare
  oproep-/berichten-API. Telefoonapps ontvangen gecontroleerde handoffs; werkelijk
  bellen/verzenden bevestigt u in de betreffende app. Geen WhatsApp-/Signal-inhoud
  via ongedocumenteerde interfaces of toegankelijkheidsautomatisering.
- Creality Hi/Cloud: geen publieke status-API geverifieerd; officieel dashboard.
  Geen live verkeer, pompprijzen, bank-/voertuigkoppeling of geofence-triggers.
  Routes gebruiken een echte geconfigureerde bron zonder verkeersdrukte; ritkosten
  zijn handmatig. Tijdgebonden routines blijven bruikbaar zonder die koppelingen.
- HA, route- en beeldprovider vereisen werkende credentials/configuratie. Het
  gekozen tekstmodel wordt niet vervangen of als beeldmodel voorgesteld.
- Windows-bediening geldt voor de backendhost, niet voor een verzonnen remote
  Windows-agent na Oracle-migratie. Sensordekking hangt van aanwezige drivers af.
- Streaming STT is opt-in incrementele herkenning; bestaande LLM-/zins-TTS-stream
  blijft behouden. Echte Nederlandse herkenning, stemkwaliteit en barge-in moet u
  beluisteren; technische mocks gelden niet als menselijke acceptatie.
- Geen Oracle-/mini-pc-migratie, publieke poort, telefonieabonnement of training.
  Poort 8765 blijft gelijk. Geheugen/aanwezigheid/beeld/status hebben eigen opt-ins.

## Fase 7: veiligheid en herstel

1. Plan een onschuldige toekomstige herinnering. Activeer Noodstop: de taak blijft
   gepauzeerd, ook na een serverherstart. Een eerder gegeven approval is ongeldig.
2. Hef de stop op als eigenaar. Taken hervatten nooit vanzelf; kies een taak
   afzonderlijk en controleer een eventueel nieuw voorstel.
3. Zet een functie op Alleen adviseren. Een verzoek krijgt adviesstatus zonder
   uitvoering. Verander een reeds ingeplande functie naar adviseren: ook die stopt.
4. Laat een taakdeadline verlopen: de status wordt verlopen, geen late uitvoering.
   Een onzekere externe mutatie wordt nooit blind herhaald.
5. Maak uitsluitend op uw eigen expliciete verzoek een synthetische afspraak.
   Herstel stelt verwijdering voor met hetzelfde event-ID/etag; controleer en
   keur afzonderlijk goed. Wijzig de afspraak intussen: herstel moet weigeren.
6. Stop tijdens een lang antwoord. De eigen client stopt meteen; verbonden andere
   clients verwerken het stop-event bij hun eerstvolgende foregroundsync. Reeds
   verzonden provider-/OS-opdrachten kunnen niet worden teruggehaald.

Media-/programma-autonomie vereist zowel eigenaarvrijgave voor de host als de
functieregel. De standaard blijft uit/vragen. Afsluiten, mail, agenda-uitnodigingen
en externe apparaatmutaties behouden eenmalige goedkeuring. Verzonden mail kent
geen veilige undo; bestaande agenda-updates worden niet zonder oude snapshot
teruggedraaid. Geen test voert deze echte acties namens u uit.

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

## Fase 4: spraak in delen

1. Laat de nieuwe luisterinstelling eerst uit en controleer normale PTT en de
   reeds beschikbare vervolgmodus. Microfoontoestemming wordt niet automatisch gegeven.
2. Activeer adaptieve spreekbeurten en ‘Spraakherkenning tijdens het spreken’.
   Spreek een lange Nederlandse zin met een denkpauze en een vervolg. Het hele
   bericht mag eenmaal naar chat gaan, met behoud van het laatste zinsdeel.
3. Begin opnieuw te spreken terwijl een voorlopige herkenning bezig is. Een
   oude ‘ja’ mag geen voorstel goedkeuren. Stop: late resultaten blijven weg.
4. Test een aangesloten headset en vervolgens onderbreken met spraak, alleen als
   u dat zelf hebt ingeschakeld. JARVIS mag zijn eigen antwoord niet uitvoeren.
5. Vergelijk STT/first-audio in de bestaande diagnostiek; resultaten hangen af van
   CPU, modellen, microfoon en netwerk. Bij slechte woordovergangen kunt u de
   segmentoptie uitzetten; de bestaande volledige herkenning blijft beschikbaar.
6. ElevenLabs uitval/privacy wordt technisch met mocks getest. Een echte test
   verbruikt eventueel het bestaande ingestelde budget; geen automatische proef.

Implementatiegrens: incrementele audiosegmenten via de bestaande WAV-route,
geen nieuw model of vendor-WebSocket. [Faster-Whisper documentatie](https://github.com/SYSTRAN/faster-whisper).

## Fase 5: Windows en Android

1. Hostbediening staat uit. Configureer als eigenaar alleen programma’s en
   specifieke documentmappen die u wilt toestaan. Laat commandoverwerkers en
   project-/systeemmappen buiten de lijst. Formulieren volgen fase 8.
2. Vraag ‘Toon mijn systeemstatus’ en ‘Open [uw ingestelde programmanaam]’.
   Status vraagt geen model; openen blijft een volledig te controleren voorstel
   bij Taken → Goedkeuringen. Een oude agenda-‘ja’ mag dit niet goedkeuren.
3. Wijzig de hostconfiguratie na een voorstel: het oude voorstel mag niet meer
   uitvoeren. Zoek een document, probeer daarna een pad buiten de toegestane map:
   dat wordt geweigerd. Sluiten gebruikt een vriendelijk vensterverzoek; een
   opslaanvenster blijft mogelijk. Store-app-launchers kunnen een andere exe hebben.
4. Test media alleen wanneer passend. Energieacties worden technisch gemockt;
   er is geen echte afsluit-/slaaptest uitgevoerd. Afsluiten/herstarten gebruikt
   60 seconden; een afzonderlijke geautoriseerde annuleeropdracht blijft beschikbaar.
5. Downloads-monitoring vereist expliciete selectie van uw Downloads-map en
   ontvangend apparaat. Bestaande bestanden geven geen startspam; een nieuw
   fictief bestand levert een wijzigingsevent, geen claim dat een download klaar is.
6. Android: geef zelf de gewenste app-/status-/meldings-/locatietoestemmingen.
   Meldingsmetadata bevat uitsluitend aantallen per gekozen app. De optionele
   locatie is laatst bekend en kan verouderd zijn; dat blijft zichtbaar.
7. Bereid een telefoonactie voor en keur het exacte voorstel goed. Op de telefoon
   verschijnt ‘Open telefoonapp’. Test met fictieve concepttekst en verzend niet.
   Dialer/WhatsApp/Signal/SMS/mail/navigatie blijven zelf verantwoordelijk voor de
   laatste stap. Een ontbrekende app geeft een fout, nooit ‘verzonden’ of ‘gebeld’.
8. Herstart voor/na openen: dezelfde opdracht mag niet opnieuw openen. Trek bron-
   of doelrechten in, stop de bovenliggende taak of wacht twee minuten: geen
   nieuwe overdracht. Een verlopen onbevestigde overdracht wordt onzeker bewaard.
9. Achtergrondophalen staat uit. Na eigen opt-in haalt WorkManager ongeveer iedere
   15 minuten op; Android/batterij/netwerk mogen uitstellen. Een melding toont geen
   privé-inhoud op het lockscreen. Open JARVIS om de echte briefing te lezen.

Bronnen: [Windows geheugen](https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/nf-sysinfoapi-globalmemorystatusex),
[media-opdrachten](https://learn.microsoft.com/en-us/windows/win32/inputdev/wm-appcommand),
[NVML](https://docs.nvidia.com/deploy/nvml-api/latest/),
[Android notification access](https://developer.android.com/reference/android/service/notification/NotificationListenerService),
[WorkManager intervallen](https://developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work).

## Fase 6: omgeving en beelden

Configuratie en bronbeperkingen staan in [EXTERNAL_INTEGRATIONS.md](EXTERNAL_INTEGRATIONS.md).
De nieuwe formulieren/previewpanelen worden in fase 8 aangesloten.

1. Controleer ontbrekende koppelingen: HA/route/Hi mogen elk afzonderlijk als
   niet ingesteld/niet ondersteund verschijnen. Gewone chat moet blijven werken.
2. Alleen als u HA bezit: configureer HTTPS, een kleine allowlist en eigen namen;
   voer de sleutel verborgen in via de lokale configurator. Vraag een status en
   bereid een wijziging voor. Controleer dat een gewijzigde configuratie een oud
   voorstel ongeldig maakt. Echte licht-/thermostaattests zijn nog niet uitgevoerd.
3. Zonder routekey mag een routevraag geen plaatsnamen naar een geocoder sturen.
   Met uw key: kies twee eenduidige plaatsen. De duur heet uitdrukkelijk een
   schatting zonder live verkeersinformatie. Ritkosten gebruiken uw opgegeven
   verbruik/literprijs; onderhoud op datum gebruikt Routines.
4. Beeldanalyse staat uit. Alleen na eigen globale/apparaattoestemming: maak
   een voorbeeld, controleer de pixels en verstuur bewust. Voor cloud is een
   aparte toestemming nodig. Wissel de provider na het voorbeeld: opnieuw
   controleren is verplicht. Privé/offline mag geen cloudbeeld versturen.
5. Gebruik een fictief beeld zonder persoonsgegevens, bijvoorbeeld een kleurvlak.
   Herhalen met dezelfde request-ID mag geen tweede modelcall veroorzaken; de
   daglimiet blijft na herstart gelden. Een fout rapport mag geen succes worden.
6. Beeldinhoud kan nooit een tool, grant of goedkeuring worden. De analyse toont
   waarnemingen/onzekerheden/suggesties en vermeldt geen uitgevoerde acties.
   Android gebruikt een zelf gekozen afbeelding, geen permanente schermopname.
