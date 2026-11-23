# Testverslag fase 5

Status: implementatie en lokale verificatie op
feature/dutch-voice-assistant, vanaf develop d6e1b83 (fase-4-PR #15, echte CI groen).
Geen wijzigingen naar main of fase 6. De eigenaar heeft de echte audioproef
bevestigd met 'Alles werkt, inclusief stoppen'. Statusfeedback, onthouden
toestemming en modelkeuze zijn op verzoek verbeterd. Integratie loopt via
[PR #16 naar develop](https://github.com/DeBeer05/jarvis/pull/16), uitsluitend na
geslaagde checks op de exacte laatste head en inhoudelijke beoordeling.

Volledig geïmplementeerd: nieuw spraakpaneel in bestaande app, expliciete
onthoudbare expliciete microfoontoestemming, hardwarekeuze, PTT/appshortcut/expliciete globale shortcut,
begrensde capture met energiepoort, lokale Nederlandse Whisper/Silero,
Piper-Ronnie/MLS en stemvoorbeeld, snelheids-/geheugenprofielen, bestaande
geauthenticeerde SSE/context, zinsgewijze TTS, stop/generatiecontrole en RAM-cache.
Geen nieuwe backend of audio-API, geen persoonlijke data gewijzigd.

Gedeeltelijk: experimentele lokale Hé JARVIS-frasefilter na de hele uiting;
geen bewezen detectiekwaliteit in een echte kamer. STT is per uiting, niet live
per woord. De basis-audioketen is door de eigenaar bevestigd. GPU wordt
gedetecteerd maar gebruikt CPU-fallback wegens ontbrekende CUDA-bibliotheken.
Licht profiel is voorbereid, niet op de toekomstige 8-GB-machine gemeten.

Niet beschikbaar: XTTS v2 (licentie/referentiestem/extra runtime ontbreekt),
bewezen hybride TTS, getraind Nederlands wake-wordmodel, gesproken barge-in/AEC,
Android, agenda/andere integraties en autonome acties.

Echte engines getest zonder fysieke microfoon of luidspreker: in-memory Piper
naar Whisper. De oude MLS-stem gaf slechte korte-uitingresultaten. De aanvullend
goedgekeurde Ronnie-stem leest begroeting en langere Nederlandse zin goed terug;
naamspelling/nummers kunnen verschillen. Geen menselijke luisterkwaliteit of
microfoonnauwkeurigheid uit deze synthetische rondreis afleiden.

Herhaalbaar: `.local/client-venv/Scripts/python.exe scripts/benchmark-voice.py`.
Benchmarks blijven lokaal onder .local; geen ruwe audio opgeslagen. Zie definitieve
metingen hieronder. First-audio in de UI betekent het
eerste schrijfblok naar de driver; fysieke hoorbare latency vereist onderstaande test.

## Uitgevoerde automatische en engineproeven

- 74 clienttests geslaagd: capture/geen toestemming, missing/busy/denied/unplugged
  drivers, VAD/stilte, PCM-geheugenbuffer, outputstop/fout, apparaten, settings,
  wakefilter, zinsqueue/cache, late TTS-annulering, PTT/auth/UI, netwerkfout zonder
  resend, drie chatbeurten met dezelfde gesprek-ID en CUDA→CPU-fallback.
  Ook: toestemming/apparaatkeuze na herstart, live niveaumeter, inline foutmelding
  en herstel van ontbrekend Tiny naar daadwerkelijk geïnstalleerd Small.
- 165 servertests geslaagd, inclusief echte tijdelijke TCP-auth/chat/refresh/
  context/intrekking; één bestaande Starlette/httpx-adapterwaarschuwing.
- Pip check op server/client/voice goed; volledige client-/voice-constraints met
  pip-audit: 0 bekende kwetsbaarheden. Bandit: 4 lage signalen, 0 middel/hoge,
  0 scanfouten en geen suppressies. Inhoudelijk beoordeeld: B404 subprocessimport,
  twee B603-aanroepen met vaste eigen helper/taskkill-argumenten zonder shell of
  AI-invoer, en B110 bij best-effort PortAudio-abort nadat generatieannulering al
  uitvoer uitsluit. Dit zijn beoordeelde grenzen, geen claim van nul meldingen.
- Repository-/whitespacecheck, definitieve index en nieuwe commitrange met
  Gitleaks geslaagd. Oude upstream-historie met eerder vastgestelde verwijderde
  historische sleutel wordt niet herschreven; geen nieuwe sleutel/data gecommit.
- Portable GUI 0.5.0 gestart: zeven pagina's, geen netwerk, geen mic en geen
  helper bij start. Ook de ingepakte helper importeert engines en weigert een
  ontbrekend model zonder download. Drie echte ingepakte TTS→STT-proeven geslaagd.
- Eigen neutraal testvenster visueel gecontroleerd met Windows-Qt; geen login,
  persoonlijke inhoud of microfoon gebruikt.

Twaalf opeenvolgende synthetische enginebeurten op deze ontwikkeldesktop:

| Meting | Werkelijk resultaat |
|---|---|
| Whisper Small CPU int8 | mediaan 1,983 s; eerste 2,763 s inclusief laden |
| Piper Ronnie | mediaan 0,137 s warm; eerste 0,614 s inclusief laden |
| Synthetische audio | circa 3,2–5,6 s per beurt |
| Totale lokale TTS→STT-rondreis | circa 2,0–3,9 s; geen netwerk/AI/playback |
| Helpergeheugen | piek 869 MiB; circa 568 MiB aan einde 12 beurten |
| Gemiddeld CPU, hele machine genormaliseerd | circa 27,1%; gedeeld systeem, geen geïsoleerde labmeting |
| GPU | RTX 4060 8 GB gedetecteerd; inference CPU wegens ontbrekende CUDA-libraries |
| GPU-snapshot systeem | 13% belasting, 5223/8188 MiB; omvat andere apps en is geen voice-VRAM-meting |
| Wakefilter | 3/4 synthetische activaties; één ASR-spelling 'Jarfis' niet geactiveerd |
| Eerste AI-token / hoorbare audio / complete fysieke beurt | niet live gemeten; UI-timing voorbereid, handmatige proef vereist |

De twaalf beurten testen enginehergebruik en begrensd geheugen, geen twaalfbeurts
live AI-gesprek. De driebeurts UI-regressie verifieert contexttransport; de
bestaande servertests verifiëren echte authenticated HTTP/SSE. Geen live
cloudlatency of volledig offline hardwaregebruik uit mocks afleiden.
De portable helper geeft dezelfde Nederlandse inhoud; eerste STT 2,516 s,
eerste TTS 0,633 s, piek 877 MiB. Er zijn geen audiobestanden bewaard.

Laatste lokale Windows-artefact bij implementatiehead 63826ee:
`JARVIS-Windows-0.5.0-x64.zip`, circa 192 MB. Native GUI- en ontbrekend-model-
rookproeven opnieuw geslaagd. SHA256 executable:
`2c1205ef50dedd25fd3f97b930dbb234508d9cbaae7d475ea588b543e3119e59`;
zip: `6380ab3090d2e3a15fb1cd965f89d43365c48be10b125bc1e665ca4ce6f22aef`.
De exacte automatische GitHub-checks en merge-uitkomst staan bij PR #16;
bescherming wordt niet omzeild. De oorspronkelijke implementatiehead e9c9d7e
had al groene repository-/server-/client-CI; de laatste head moet opnieuw groen zijn.

## Handmatige acceptatie op jouw hardware

1. Start server en nieuwe app volgens VOICE_SETUP; bestaande login blijft geldig.
2. Kies de echte input/output, speel Ronnie-stemvoorbeeld. Controleer Nederlands,
   volume en verstaanbaarheid. Er wordt hierbij niets opgenomen.
3. Sta de gekozen microfoon eenmalig toe als dat nog niet is ingesteld. PTT: vraag 'Hoe heet je?', daarna in hetzelfde
   gesprek 'Hoeveel is zeven plus vijf?' en een langere opdracht van 20–30 s.
   Controleer transcript, antwoord, context en responsieve UI.
4. Stop midden in een lang antwoord: stilte moet direct intreden en oude audio
   mag niet later terugkomen. Herhaal via shortcut en geef een nieuwe opdracht.
5. Test stilte, ventilatorruis, zachte spraak; stem gevoeligheid/timeout af.
   Experimentele wakefunctie: 10 positieve en 10 negatieve zinnen. Houd false
   positives/rejects bij; gebruik PTT als die betrouwbaarder blijkt.
6. Trek toestemming in, wissel/unplug apparaten, bezet microfoon met andere app,
   weiger Windows-microfoontoegang: melding en geen crash. Herstel en probeer opnieuw.
7. Stop server tijdens stream; geen automatische herverzending. Start server,
   laat reconnect werken en stuur een nieuwe vraag. Kies Ollama en verbreek
   internet voor de gedeeltelijke offlineproef; cloud kan dan niet antwoorden.
8. Sluit volledig af tijdens opname/uitvoer en controleer dat mic/audio stopt.
   Heropen: mic uit, sessie hersteld, audio-instellingen behouden.

De eigenaar heeft de basisaudioproef zelf geslaagd bevestigd. De agent heeft geen
persoonlijke microfoonaudio opgenomen. De uitgebreide ruis-, unplug-, offline-
en wakekwaliteitsproeven hierboven blijven aanvullende handmatige controles.
Een latere foutmelding is herleid tot geselecteerd maar niet geïnstalleerd Whisper
Tiny. Small is hersteld met behoud van gekozen input/output, ontbrekende modellen
zijn niet meer selecteerbaar en concrete fouten staan direct bovenaan.
