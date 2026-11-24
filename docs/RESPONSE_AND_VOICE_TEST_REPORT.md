# Antwoord en stem — test-/acceptatierapport

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
