# Agendagesprek en Nederlands STT — 27 november 2026

## Herstel

De agenda volgt expliciete gebruikersgegevens: datum, begintijd en titel; één uur
en de standaardagenda worden ingevuld. Activiteit, locatie, beschrijving en einde
zijn optioneel. Titels worden afgeschermd van intentie-/tijdherkenning; bestaande
uitjesplanning en expliciete agendaselectie blijven aparte routes.

CalendarDialogue gebruikt bestaande TaskMemory, AutomationEngine en
ApprovalManager. Persoonlijke CalendarCreate/Update-opdrachten kunnen na actuele
read/write/approve-rechten direct lopen; expliciet ask/block-beleid blijft gelden.
Uitnodigingen/series en andere hoogrisicoacties houden hun volledige preview.
Een gewijzigde payload kan de oorspronkelijke opdracht niet als autorisatie
overnemen. Google-event-ID, actuele etag en PATCH bewaren dezelfde afspraak en
overige velden. Onderbroken externe acties worden onzeker, niet blind herhaald.

De fout over de ‘laatste vraag’ kwam van berichtpositie/historiehashes. Pending
acties bewaren nu hun binding en vervaltijd in SQLite. Na volledige finalisatie
wordt een display-hash vastgelegd, zodat ook privémodus zonder chattekst werkt.
Een nonce wordt nooit opgeslagen; de bestaande manager controleert de payload
nogmaals transactioneel. Relatieve datums gebruiken de serverklok/Amsterdam.

## Verificatie

- Gerichte tussenronde: 203 tests geslaagd. Actuele gesprekscontracten: 21 tests
  plus één expliciete named-calendar-lookup geslaagd.
- Privacy/ervaringronde na herstel: 46 tests geslaagd.
- Windows-client: 130 tests geslaagd, portable build en verpakte helper-rooktest
  geslaagd. Acht pagina's; geen netwerk, microfoon of helper tijdens startupcheck.
- Ruff/mypy (38 serverbestanden), pip check, repository- en settingscontractcheck
  geslaagd. Laatste volledige lokale reeks: 598 passed/1 POSIX-skip, 246,40 s;
  extra agendaselectietest geslaagd. Actuele CI wordt in de PR bevestigd.
- Alle Calendar-tests gebruiken synthetische API's; ElevenLabs-regressies gebruiken
  bestaande mocks. Geen echte agenda-mutatie, accountkoppeling of betaalde stemtest.

## STT-proef en grenzen

Whisper Small blijft behouden; geen training/download. Nederlands en transcribe
zijn expliciet, met neutrale woordcontext, temperatuur 0, beam 5 (light 3), VAD
threshold 0,4 en 500 ms randcontext. Recorder/VAD onderzocht: Windows/Android
bewaren ook audio vóór de spraakdrempel; geen extra opname-/microfoonrechten.

Vier lokale Piper-uitingen zijn op CPU herkend vóór/na de decoderinstellingen.
Morgen/vanmorgen/overmorgen bleven onderscheiden; nieuwe uitvoer had onder meer
‘om half, drie’ en ‘titel, teamoverleg’. Generieke parsernormalisatie verwerkt
zulke leestekens/woordgrenzen. ‘Kort over vier’ blijft werkelijk onduidelijk en
vraagt een exact tijdstip; er wordt geen kwartier gegokt. Gemeten nieuwe STT-tijd:
3,558 s eerste uiting, daarna 2,648 / 2,408 / 2,306 s. Dit is synthetische spraak,
geen WER-benchmark of bewijs voor de echte microfoon/naamherkenning.

De eerder bekende incidentele offscreen-Qt-abort trad één keer lokaal op; de
volledige clientreeks met zichtbare native diagnostiek slaagde daarna. De oorzaak
is niet bewezen weggenomen. Oracle-installatie/migratie blijft buiten deze taak.

API-keuzes gecontroleerd aan primaire bronnen:
[Google Calendar PATCH](https://developers.google.com/workspace/calendar/api/v3/reference/events/patch),
[faster-whisper decoder](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py),
[VAD-opties](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/vad.py).
