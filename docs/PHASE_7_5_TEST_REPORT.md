# Fase 7.5 — tussentijds testrapport

Datum: 24 november 2026. Status: **in uitvoering, geen fase-8-vrijgave**.
De echte gebruikersserver/database en geïnstalleerde apps zijn nog niet naar
de nieuwe versie omgezet. Alle onderstaande nieuwe accountproeven zijn synthetisch.

## Automatisch uitgevoerd

| Controle | Laatste resultaat | Bewijs / grens |
|---|---|---|
| Volledige serverregressie | 355 geslaagd, 141,84 s | Inclusief fases 1–7 en nieuwe context/privacy/taak-/settingsproeven; tijdelijke databases |
| Windows-client | 99 geslaagd | Qt offscreen, audiowerkers, instellingen, cancel/TCP en synthetische duplex |
| Python-lint | Geslaagd | Ruff F/E9 op nieuwe natuurlijke-gesprekscode en betrokken adapters/tests |
| Typechecks | Geslaagd | 23 kernmodules, 5 Windows-voiceadapters; check_untyped_defs en beide platformprofielen |
| Dependencycontrole | Geslaagd | pip check, geïsoleerde server/clientomgevingen |
| Android unit/lint/debug/release | Geslaagd | Native Gradle/Kotlin; bestaande lint-/nullable-waarschuwingen blijven onderscheiden van fouten |
| Android instrumented | 14 tests, 0 fouten | Afzonderlijke headless API-36-AVD, hostmicrofoon/luidspreker uit |
| Repository/whitespace | Geslaagd | Structuur-/patrooncontrole is geen applicatie- of volledige geheimenaudit |

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

## Nog niet als voltooid geaccepteerd

Echte microfoon-/echo-/onderbrekingsacceptatie op Windows en telefoon; uitgebreidere
adaptieve end-of-turn-analyse; overige nog niet aangesloten instellingen;
volledigere contextuele mail-/taakfollow-ups; alle agenda-alternatiefvoorkeuren;
algemene semantische retrieval;
definitieve versies/builds/installatie, echte gecontroleerde schemaomzetting en
het volledige handmatige protocol. Er is geen sprekerbiometrie, publieke toegang,
telefonie, WebRTC-infrastructuur of servermigratie toegevoegd.
