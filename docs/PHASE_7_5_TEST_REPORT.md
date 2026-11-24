# Fase 7.5 — tussentijds testrapport

Datum: 24 november 2026. Status: **in uitvoering, geen fase-8-vrijgave**.
De lokale gebruikersserver draait op 0.7.5/8765 en database-schema 6. Back-up van
schema 5 aanwezig; eigenaarrecord ongewijzigd, herinneringenaantal behouden en
SQLite quick_check geslaagd. Health/ready zijn 200; persoonlijke API zonder login
blijft 401. Windows portable 0.7.5 is gestart en de echte telefoon heeft 0.7.5/705.
De telefoon is daarna bijgewerkt naar reparatiebuild **706** en de server is met
de herstelcode herstart. USB-reverse verwijst naar de gebruikersserver, niet de testfixture.
Alle automatische accountproeven hieronder gebruiken uitsluitend synthetische data.

## Automatisch uitgevoerd

| Controle | Laatste resultaat | Bewijs / grens |
|---|---|---|
| Volledige serverregressie | 381 geslaagd, 172,76 s | Inclusief fases 1–7, afspraakslots, cleanup bij herhaalde annulering, claim/drain, schema-6-migratie en opvolgingsrechten; tijdelijke databases |
| Windows-client | 107 geslaagd, 4,90 s | Qt offscreen; sessiereservering, late activatie en persoonlijkheidsvoorbeeld met niet-opgeslagen invoer |
| Python-lint | Geslaagd | Ruff F/E9 op nieuwe natuurlijke-gesprekscode en betrokken adapters/tests |
| Typechecks | Geslaagd | 25 kernmodules, 5 Windows-voiceadapters; check_untyped_defs |
| Dependencycontrole | Geslaagd | pip check, geïsoleerde server/clientomgevingen |
| Android unit/lint/debug/release | Geslaagd | Native Gradle/Kotlin; bestaande lint-/nullable-waarschuwingen blijven onderscheiden van fouten |
| Android instrumented | 16 tests, 0 fouten | Afzonderlijke headless API-36-AVD; herhaald overnemen/stoppen en afgesloten versus actieve leases; hostaudio uit |
| Repository/whitespace | Geslaagd | Structuur-/patrooncontrole is geen applicatie- of volledige geheimenaudit |

Builds: Windows portable 0.7.5 met verpakte helper; smoke bevestigt acht pagina's,
geen gestart netwerk, microfoon of worker bij de proefstart. Helper importeert
correct en behandelt ontbrekende modellen zonder download. Android debug en
release 0.7.5/705 gebouwd; lokale debug-APK heeft dezelfde ondertekenaar als de
bestaande 0.7.0-debug-APK. Alleen de afzonderlijke emulator is geïnstalleerd/getest.
De release-APK is niet als publiek ondertekende productie-uitgave aangeboden.
De echte telefooninstallatie gebruikte uitsluitend install -r; geen uninstall,
gegevensreset of automatische machtigingsgrant. Werkelijke spraakacceptatie door
de eigenaar is aangevraagd en nog niet als geslaagd geregistreerd.

Reproduceerbare Python-check: `python scripts/check_natural_quality.py` met optioneel
`--client-python` naar de geïsoleerde native omgeving. CI voert de servervariant uit.
Android-taken: `testDebugUnitTest`, `lintDebug`, `assembleDebug`, `assembleRelease`
en `connectedDebugAndroidTest` met de afzonderlijke testfixture.

## Wat concreet bewezen is

- Auth/CSRF/rechten, settings-CAS/import/export/reset, apparaat-/gebruikersisolatie,
  modelbeschikbaarheid en offlinebeleid voor gewone én interne AI-aanroepen.
- FTS-geheugen, correcties/expiry, expliciete gevoelige toestemming, bronbewust
  vergeten, lijst-antwoorden als afgeleide bron en herstartpersistentie.
- Nieuwe geschiedenis-uit-beurten schrijven geen gewone tekst naar SQLite;
  actieve RAM-context blijft bruikbaar, idempotentie en exacte approvals werken.
  Android wist Room-cache en cachet zulke beurten niet opnieuw.
- Eén activatie doorloopt tien synthetische Android-spraakbeurten via echte
  Whisper/Piper-serverinference. Een gesimuleerde duplexonderbreking stopt de
  oude uitvoer en vervolgt hetzelfde gesprek. Dit is geen echte AEC-proef.
- Echte TCP-cancel vóór responseheaders stopt ook de serverinference; daarna
  slaagt een volgende aanvraag. SecurityHeaders behoudt disconnect via pure ASGI.
- Nederlandse datum/tijd/duur/herinnering, voorstelcorrecties, brongebonden
  multi-intentplannen, deelproblemen, afhankelijkheden en afzonderlijke jobkeys.
- Generiek ja keurt nooit een groep voorstellen goed; gewijzigde/verlopen of
  niet als laatste getoonde previews worden opnieuw gecontroleerd.
- Diagnostiek accepteert alleen numerieke whitelistevents/vaste codes; export
  bevat geen gespreks-/geheugeninhoud. Optionele GPU-probe heeft deadline/cache.

## Herstelde test-/platformproblemen

Linux-mypy zag de Windows-only ctypes-loader niet; de loader wordt nu binnen de
platformtak opgezocht. Remote Windows/Linux checks zijn daarna geslaagd.
Een verdwenen test-AVD is opnieuw gestart zonder echte telefoon te gebruiken.
De nieuwe Kotlin-privacyproef kreeg expliciet een Unit-return voor JUnit.
Testcases resetten alleen de instellingen/rates in de expliciet synthetische
fixture; productiecontroles zijn niet versoepeld. De privacyproef gebruikt nu
één native sessiehouder, zodat testclients niet elkaars refreshrotatie verstoren.

## Werkelijke prestaties

De bestaande lokale helperproef mat Piper koud/warm 1,004/0,098 s en Whisper Small
CPU 3,321/1,975 s; helperpiek 877,6 MiB. Zie CONVERSATION_PERFORMANCE.md voor methode.
Dit bewijst geen totale menselijke gesprekslatency, GPU-STT of mini-pc-geschiktheid.
Live diagnostiek kan nu aanvullende echte cijfers verzamelen; het 1–3 s-doel
blijft een doel. Onbekende meetwaarden worden niet als nul/succes ingevuld.

## Git en CI

Featurebranch `feature/natural-conversation-engine`, draft-PR #25 naar develop.
De eerdere GitHub Actions-blokkade is opgeheven. Remote checks voor 084baad zijn
geslaagd voor Linux/Windows-server, Windows-build, Android en structuur. De nieuwe
privacywerkboom krijgt een eigen commit/run; oude groene checks bewijzen die
nieuwste werkboom niet. Geen force-push, directe main-push of beschermde merge.

## Bevindingen eigenaar en herstel

De eigenaar bevestigde dat algemene gesprekken goed werken, maar meldde vergeten
afspraakgegevens en daarna een terugkerende Android-melding over overnemen.
De oorspronkelijke kwalificatie ‘afspraak maken’ ontbrak in de aanmaakdetector;
vrije antwoorden konden buiten de taakroute vallen. Beide hebben nu een volledige
gespreksregressie. De generieke mogelijkhedenvraag krijgt lokale, echte functies.
Daarnaast is een achtergebleven lopende chatbeurt aangetroffen. Een gecontroleerde
test reproduceerde de oorzaak: een tweede annulering onderbrak de finally-opruiming.
Dezelfde test slaagt met een afgeschermde finalisatietaak en gegarandeerde vrijgave.
Build 706/serverherstel zijn geïnstalleerd; de nieuwe eigenaarproef staat nog open.

## Nog niet als voltooid geaccepteerd

Echte microfoon-/echo-/onderbrekingsacceptatie op Windows en telefoon; uitgebreidere
adaptieve end-of-turn-analyse; overige nog niet aangesloten instellingen;
volledigere contextuele mail-/taakfollow-ups; alle agenda-alternatiefvoorkeuren;
algemene semantische retrieval;
definitieve versies/builds/installatie, echte gecontroleerde schemaomzetting en
het volledige handmatige protocol. Er is geen sprekerbiometrie, publieke toegang,
telefonie, WebRTC-infrastructuur of servermigratie toegevoegd.
