# Antwoord en stem — test-/acceptatierapport

## Herstel: samenvatting niet beschikbaar

Gevoelige mailinhoud gebruikt nu expliciet Ollama, zonder cloudretry; de eerdere
implementatie sloeg de AI daarbij helemaal over. JSON-bronpakketten houden Unicode
compact. De lokale terugval meldt nu de reden in plaats van algemene onbeschikbaarheid.
Mocktests controleren privacyrouting, lokale uitval en emoji-/accentrijke bronpakketten.
Een echte proef met uitsluitend synthetische inhoud en het bestaande lokale model
liep koud tegen de bestaande providerdeadline; de warme herhaling gaf in **3,49 s**
een niet-lege samenvatting met behoud van ‘vrijdag’. Geen echte mailbox gelezen.
Dit bewijst geen gegarandeerde koude-starttijd of verwerking van privéberichten.
Volledige serverregressie op deze correctie: **429 geslaagd**, 180,77 s;
Ruff/mypy, repository-/diffcheck en server-pip-check geslaagd.

## Herstel: spraak na vensterwissel en recente mailinhoud

Windows negeert oude heartbeatreacties van een eerdere gespreksepoch. Intrekking/
autorisatiefouten blijven de microfoon stoppen; Stop blokkeert late vervolgtimers.
Synthetische window-deactivation en tien doorlopende beurten blijven slagen.
De daadwerkelijke microfoon in een ander programma moet nog door de gebruiker
worden beoordeeld; de oorspronkelijke focusfout is niet fysiek gereproduceerd.

Recente inboxvragen lezen rechtstreeks maximaal twintig geverifieerde mails en
maken één inhoudelijke samenvatting. Filterverzoeken blijven op de bestaande
zoekroute. Tests bewijzen tien body-reads, deadlinebehoud, de tiende vervolgmail,
begrenzing, uitgeschakelde leestools en geen cloudcall bij gevoelige inhoud.
Geen echte mailbox gelezen, geen berichten verzonden of apparaatrechten gewijzigd.

Volledige serverregressie: **426 geslaagd**, 178,13 s. Extra mailprivacyproef daarna
toegevoegd: alle **10 mailtests geslaagd**. Windows: **114 geslaagd**, 5,38 s.
Ruff/mypy, repository-/diffcheck en beide relevante pip checks geslaagd.
Nieuwe portable Windows-build: acht pagina's, microfoon/netwerk/helper uit bij
smoke-test; zichtbaar aangemeld en verbonden gestart. Dubbelstart exit 0 met één
proces. Android-bron/APK niet gewijzigd: gedeelde backendfix geldt ook voor Android.
De eerder gemeten TTS-prestaties hieronder zijn niet opnieuw gemeten.

De bestaande fase-7.5-acceptatie is hiermee niet automatisch afgerond. Deze uitbreiding
is gebouwd voor lokale beoordeling; subjectieve stemkwaliteit blijft een menselijke proef.

## Geïmplementeerd en hergebruikt

- Centrale antwoordmodi/-profielen, aparte geschreven/gesproken uitvoer, progressive
  disclosure en geverifieerde mailverwijzingen. Context, geheugen en oorspronkelijke
  geschreven resultaten blijven behouden; algemene korte vervolgvragen zijn aan het
  daadwerkelijk laatst getoonde mailantwoord gebonden.
- Classic Butler, configureerbare aanspreekvorm en gesloten gesproken instellingen.
  Permanente wijzigingen gebruiken SettingsManager/CAS/audit, tijdelijke blijven
  sessie-/apparaat-/chatgebonden en vervallen. Geen nieuwe bevoegdheden.
- Gedeelde SpeechFormatter en TTSRouter, lokale Supertonic M1–M5 plus Piper,
  providerbinding per antwoord, veilige eenmalige fallback, begrensde private cache.
- Voice Studio Windows/Android met voorbeeldtekst, seriële vergelijking, snelheid,
  volume, echte provider-/RAM-/tijdweergave en opslaan van favoriete stem.
- Windows heropening gebruikt een user-scoped lokaal activatiekanaal: tweede start
  haalt hetzelfde venster naar voren. Geen tweede backend of serverstart vanuit client.

Nieuwe kernbestanden: server/natural/responses.py, server/natural/tts.py,
providers/speech_format.py, vendored MIT-helper met licentie, expliciet installatiescript
en synthetisch benchmarkscript. Bestaande ChatService, AutomationChat, ContextManager,
SettingsManager, mobiele routes en beide native clients uitgebreid. Geen nieuwe SQL-tabellen;
SQLite-schema 7 blijft behouden. Alle instellingen blijven in bestaande versieerde JSON-rijen.

## Automatische controles

- Volledige serverregressie: **417 geslaagd**, 221,34 s; geen echte accountmutaties.
- Windows: **112 geslaagd**, inclusief tweede proces/activatie, typed settings,
  cancellable Studio-transport en het wissen van privévoorbeeldtekst bij logout.
- Android: unit/lint/debug/release-build geslaagd. Eerste native proef: **18 geslaagd**;
  definitieve herhaling met bijgewerkt instellingencontract eveneens geslaagd.
- Ruff/mypy: 29 server/shared en 5 Windows-spraakadapters geslaagd.
- pip check: server-, client- en inference-omgeving zonder gebroken requirements.
- Portable startup-smoke: 8 pagina's, geen netwerk/microfoon/helper bij start.
  Verpakte Piper/Whisper ontbrekende-modellenproef zonder downloads geslaagd;
  verpakte Supertonic M1 maakt geldig PCM-WAV.
- Echte benchmark: 42 synthetische zinnen/varianten, mediaan warm 1,467 s Supertonic
  en 0,213 s Piper; maximale Supertonic-helperpiek 518,6 MiB. Generatieannulering
  circa 0,051 s en daarna verse inference geslaagd. Zie TTS_BENCHMARKS.md.

## Gebruik en activering

Open Instellingen → Gesprekken en geheugen → Antwoordgedrag voor antwoordmodi/profielen.
Kies Persoonlijkheid → Classic Butler en stel aanspreekvorm naar wens in. Stem en audio
bevat lokale provider/Voice Mode/profiel; Voice Studio laat de vaste stemmen vergelijken.
Nieuwe standaardvelden worden additief geladen; oude persoonlijke instellingen worden
behouden. Selecteer bewust het nieuwe profiel om bestaande voorkeuren te veranderen.

Supertonic M1 is de voorlopige kwaliteitskandidaat, Piper Ronnie de snelste fallback.
Geen stem is als subjectief beste beoordeeld. Alle daadwerkelijk gebruikte TTS is lokaal;
geen TTS-API-kosten, online TTS, betaalde Voice Builder of ongeautoriseerde cloning.
Edge en XTTS zijn onderzocht en expliciet niet als werkende providers aangeboden.

## Git en uitrol

Featurebranch feature/intelligent-response-butler-voice gebruikt de bestaande fase-7.5-
branch als noodzakelijke basis; develop bevat die implementatie nog niet. PR naar develop
moet deze afhankelijkheid vermelden. Geen main/force-push, merge of protection-omzeiling.
Definitieve commit/CI- en uitrolgegevens worden na controle hieronder aangevuld.

## Handmatige acceptatie (Windows én Android)

1. Vraag 'Heb ik belangrijke mail?': kort overzicht, geen ongefundeerde volledige
   telling/urgentieclaim. Vraag naar een uniek onderwerp, daarna 'Lees alles voor'.
2. Vraag 'Hoe ziet mijn dag eruit?': geverifieerde afspraken, geen verzonnen vrije tijd.
3. Vergelijk de zes benchmarkzinnen met M1–M5 en Piper via Voice Studio. Beoordeel warmte,
   natuurlijkheid, diepte, uitspraak, stilte/intonatie en snelheid. Sla een favoriet op.
4. Onderbreek een lang antwoord. Audio/generatie stopt, context blijft; geen actie herhaald.
5. Verbreek internet (alleen zelf): lokale TTS blijft werken. Test Ollama apart.
6. Simuleer provideruitval alleen met mocks of testprofiel: fallback uitsluitend vóór
   eerste audio, nooit stemwissel midden in een geleverd antwoord.
7. Wijzig profiel, aanspreekvorm en gesproken/geschreven lengte. Herstart en vergelijk.
   Probeer tijdelijke voorkeur en daarna 'voortaan'; controleer dat alleen de laatste blijft.
8. Voer tien spreekbeurten zonder nieuw wakeword, inclusief denkpauze en correctie.
9. Gebruik synthetische urgente melding/deadline: essentiële informatie blijft hoorbaar.
10. Laat een volledig mail-/agendavoorstel tonen en uitspreken; alleen exact ja mag
    die ene versie goedkeuren. Voer geen echte verzending uit als automatische test.

Nog niet bewezen: subjectieve stemkwaliteit op echte luidsprekers, microfoonecho op
beide apparaten, toekomstige mini-pc, GPU-TTS, online Edge en XTTS. Geen productie,
telefonie, publieke toegang of betaalde dienst geactiveerd.

## Werkelijk uitgerold en gecontroleerd

- Windows portable 0.7.5 staat in .local/client-build-butler/dist/JARVIS. De bestaande
  bureaubladsnelkoppeling verwijst daarheen. Oude app gecontroleerd afgesloten,
  nieuwe zichtbaar gestart en verbonden aangetroffen. Een tweede echte start eindigde
  met code 0 en activeerde hetzelfde venster/proces. Aangemelde Voice Studio haalde de
  lokale stemkeuzes op. Geen microfoon of stemvoorbeeld door de agent geactiveerd.
- Echte telefoon: debug 0.7.5/708 met install -r behouden, versie gecontroleerd.
  USB reverse tcp:8765→tcp:8765 opnieuw bevestigd. Geen datareset of nieuwe grants.
- Backend op 8765 opnieuw gecontroleerd gestart zonder actieve chat-/automatiseringstaken.
  Oude instellingen, eigenaar en geheugen behouden; geen nieuwe databaseversie.
- Branch gepusht; draft PR [#26](https://github.com/DeBeer05/jarvis/pull/26) naar develop,
  afhankelijk van PR25. Actuele CI-resultaten staan op de PR; geen merge uitgevoerd.
- Menselijke luister-/onderbrekingsproef is gevraagd en is nog niet als geslaagd geteld.
  Dit is de resterende acceptatiestap voor subjectieve kwaliteit; geen fase-8-vrijgave.

## Bestanden en configuratie

De nieuwe kern staat in server/natural/responses.py, server/natural/tts.py en
providers/speech_format.py. Bestaande ChatService, ContextManager, AutomationChat,
SettingsManager en mobiele spraakroutes zijn uitgebreid. De native wijzigingen
staan in natural_settings.py, voice/manager.py, voice/server_worker.py en window.py
op Windows en NaturalSettingsScreen.kt, JarvisViewModel.kt en JarvisApi.kt op Android.
Het gedeelde Android-contract en de bijbehorende tests zijn bijgewerkt.

De bestaande private inferencehelper kreeg engines.py plus een vastgezette MIT-
supertonic_helper.py met eigen licentiebestand. scripts/install_supertonic.py voert
alleen een expliciet goedgekeurde installatie uit; scripts/benchmark_tts.py maakt
uitsluitend synthetische metingen. Build-WindowsClient.ps1 kan een aparte artifact-
directory voorbereiden terwijl de huidige app openblijft. Er zijn geen nieuwe
verplichte Python-packages of SQL-tabellen. Modelbestanden, audioproeven, lokale
instellingen en gebruikersgeheugen worden niet gecommit.
