# Hervatpunt — agenda en Nederlands STT, 27 november 2026

## Actueel: acht productfases persoonlijke butler

- Fase 5 technisch afgerond: Windows-hostadapter (gesloten acties,
  specifieke programma-/documentrechten, policyfingerprint, workerthreads),
  Android-apphandoff met doelapparaatconsent/eenmalige approval en aparte
  ready/handed-off-status. Geen oproep of verzending geclaimd. Lokale Windows-
  en automationreeks 28 passed; laatste SDK/handoff/privacyreeks 13 passed.
- Nieuw: opt-in WorkManager-achtergrondophalen (15 min, OS mag uitstellen), geen
  permanente microfoon/LLM/service. Server-inbox blijft ongelezen tot voorgrond;
  aparte opaque notificationreceipt voorkomt herhaling. Android 11 tests, lint en
  debug/release geslaagd. Meldingsmetadata/batterij/optionele locatie: SQLite v12,
  actuele grants, ouderdomslabel en bestaande 24-uursmaintenance.
- Volledige serverreeks 642 passed/1 POSIX-skip; na laatste SDK/expiry/parent-stop-
  wijzigingen 13 gerichte tests passed. Logs .local/butler-phase5-*.log. Geen
  nieuwe functies live of echte telefoonacceptatie. Formulieren volgen fase 8.
- Volgende fase: 6, ondersteunde externe adapters en schermcontext. Geen Oracle-
  installatie/cutover, geen betaalde diensten of nieuwe werkelijke apparaatgrant.
- Fase-4-head 096b87a heeft alle 12 echte CI-checks groen. Eigenaarmaildiffs apart.

- Fase 4 technisch gereed: opt-in incrementele STT op Windows/Android, 500 ms
  overlap, restaudio en achtsecondenlimiet voor voorlopige herkenning. Alleen
  afgeronde uitspraak naar tools. 140 clienttests, 28 server/ElevenLabs-tests,
  Android unit/lint/debug/release en kwaliteit groen; nog niet live geactiveerd.
  Logs .local/butler-phase4-*.log. Eerstvolgend: fase 5 OS-/Android-integratie.

- Fase 3 technisch: brongebonden briefings, Open-Meteo/NOS-cache, lijsten/routines/
  gelegenheden/sollicitaties, bestaande reminders en reply-watches; SQLite v11.
  Brede reeks 629 passed/1 skip, finale 37 automation/briefingtests en 60 kalender-
  briefingtests geslaagd. Kwaliteit/contract/dependencies groen. Nog niet live.
- Eigenaar kiest ochtendbriefing voorlopig in app; geen oproepkanaal. Live verkeer,
  bankkoppeling en locatiegrant ontbreken. Geen fictieve ETA of externe mutatie.
- Fase-2-head 98fcc29 had alle 12 echte CI-checks groen. Fase 4 volgt; eigenaars-
  maildiffs nog steeds apart, geen reset/stash/ongewenste stage.

- Fase 1 checkpoint 25410ad. Fase 2 technisch gereed: acht modi, opt-in Windows
  WTS/idle/lokale procesclassificatie en Android foreground lock/idle. SQLite v10
  bevat persistente status en een begrensde, apparaatgebonden event-inbox.
- Privé: nieuwe chattekst niet opslaan, lokale AI/TTS, geen impliciete cloudfallback;
  ruwe voorkeuren blijven behouden. Meldingen volgen modus/opt-in, geen grantwijziging.
- Fase-2-checks: 617 servertests passed/1 skip, 15 finale gerichte tests, 136 client-
  tests; Android 8 tests + lint + debug/release-build geslaagd. Geen echte apparaat-
  of microfoonacceptatie. Logs .local/butler-phase2-*.log. Volgende: fase 3.
- Gevraagde locatie/tijden/koppelingen ontvangen in chat; niet als persoonlijke
  gegevens in Git vastleggen. Scheduled bellen vereist aantoonbare echte route.
- PR 33 is gestapeld op PR 32. Fase-1-CI 11 groen/1 bekende Qt-testabort;
  laatste clientreeks lokaal groen, nieuwe head volgen na push. Geen CI-bypass.

- Nieuwe expliciete opdracht staat acht productfases toe; plan in
  IMPLEMENTATION_PLAN.md. Branch feature/personal-butler vanaf ea09cb6/PR 32;
  develop mist nog deze basis. Nieuwe branch zonder stash/reset; eigenaarmail
  blijft apart. Oracle/productie en echte externe proefacties niet geautoriseerd.
- Fase 1 delta: opt-in episodische FTS5-retrieval in bestaande SQLite-database,
  migratie v9 met backup, alleen gebruikersuitspraken, maximaal 3 x 480 tekens.
  History/cloud/sensitive/sync/expiry en bronvergeten blijven leidend; afgeleide
  episodecontext wordt transitief uitgesloten bij vergeten. Geen extra LLM-call.
- 28 gerichte geheugen/spraak/instellingentests en 12 migratie/episodetests
  geslaagd; eerdere brede 76 tests geslaagd na twee herstelde testfixturepaden.
  Ruff/mypy (39 modules), dependency-, contract- en structuurcheck geslaagd.
  Brede regressie: 608 passed/1 skip plus één oude backupbestandsnaamtest,
  hersteld en afzonderlijk geslaagd; finale gerichte reeks 24 passed. Logs .local/butler-phase1-*.log.
- Nieuwe handleiding docs/PERSONAL_BUTLER_TEST_GUIDE.md; echte menselijke
  persoonlijkheids-/microfoonacceptatie blijft apart. Volgende fase: modi en
  aanwezigheid; fase 1 technisch afgerond. Locatie/connectorinformatie gevraagd;
  zonder antwoord blijft die specifieke externe configuratie geblokkeerd.

## Vervolg: blijvende butlerpersoonlijkheid

- Opdracht: elegant Nederlands met u/uw en meneer in ieder antwoord; tact,
  rustige zelfverzekerdheid, passende Britse humor en contextueel initiatief.
- Bestaande Classic Butler uitgebreid; aanspreekfrequentie `always` toegevoegd
  naast ongewijzigde off/occasionally. Native clients gebruiken dezelfde schema's.
- Via de aangemelde Windows-app opgeslagen en teruggelezen: profiel Classic
  Butler, meneer, Ieder antwoord en persoonlijke stijlinstructies, revisie 8.
- Vertrek/terugkomst gebruiken beschikbare context; geen fictieve monitoring,
  nieuwe rechten, microfoonactivatie, nieuwsservice of autonome accountacties.
- 39 gerichte response/spraak/ervaring/instellingentests geslaagd; Ruff,
  pip check en structuurcheck geslaagd. Volledige regressie/CI volgt op deze commit.
- Vorige agendacontrole afgerond: 602 passed/1 POSIX-skip en alle 12 CI-checks
  groen op 50cd7f0. Logs/verdere actuele resultaten in .local en PR 32.
- Echte menselijke beoordeling van toon/humor/terugkomst blijft apart nodig.
- Bestaande eigenaarmaildiffs hieronder blijven buiten commits; Oraclegrens gelijk.

- Actuele opdracht: structurele agenda-/context-/STT-reparatie; geen training,
  echte Google-acties of betaalde ElevenLabs-tests. Backend blijft op 8765.
- Branch fix/calendar-dialogue vanaf e6bff7c / feature/elevenlabs-voice (PR 31);
  gestapeld omdat develop deze basis nog mist. Geen merge/main/release.
- Gereed: deterministische persoonlijke agenda-opdrachten uit gebruikerswoorden;
  alleen datum/begintijd/titel verplicht, standaard 60 minuten/standaardagenda.
  Planningtitels zijn inhoud; bronwoorden geven geen nieuwe rechten.
- Direct uitvoeren hergebruikt Automation/ApprovalManager met actuele read/write/
  approve-grants, exact payloadfingerprint en idempotente job. Expliciete ask/block,
  uitnodigingen en series behouden preview; mail/verwijderen blijven ongewijzigd.
- Persistente kalenderdrafts, event-ID/verse etag en last_calendar in TaskMemory.
  Ja/nee bindt aan sessie/apparaat/gesprek, vervaltijd, fingerprint en voltooide
  display-hash; geen berichtpositie/nonce-opslag. Werkt ook zonder chatteksthistorie.
- Updates via PATCH behouden overige velden; bevestiging volgt alleen geverifieerd
  API-resultaat. Onzekere/afgebroken mutaties worden niet blind opnieuw uitgevoerd.
- STT: Nederlands/transcribe, neutrale woordcontext, deterministische decoder,
  beam 5 (light 3), ruimere VAD-randen. Morgen/vanmorgen blijven onderscheiden;
  alleen echte conflicten/vervagende tijdtaal vragen om gerichte verduidelijking.
- Tests: 203 gerichte tussenregressies; 21 actuele gesprekscontracten plus named-
  calendar-lookup; 46 privacy/ervaringtests en 130 clienttests geslaagd. Ruff/mypy,
  pip/contract/structuurchecks OK. Volledige lokale reeks: 598 passed/1 POSIX-skip; extra agendaselectietest passed. Remote CI volgt;
  logs .local/calendar-release-regression.log en .local/calendar-final-quality.log.
- Windows-build/rooktest OK: .local/client-build-calendar-dialogue; 8 pagina's,
  geen netwerk/microfoon/helper bij rooktest. APK 708 eerder geïnstalleerd;
  Android-code blijft gelijk, gebruikt dezelfde backend/speechhelper.
- Lokale Piper-naar-Whisper-proef met 4 fictieve uitingen gedaan, geen downloads.
  Komma's/woordgrenzen worden verwerkt; namen en echte microfoonacceptatie zijn
  niet gegarandeerd. Bestaande incidentele offscreen-Qt-testabort blijft bekend;
  sys-capture bewaart diagnostiek. Volledige clientreeks daarna 130 passed.
- Eigenaarwijzigingen NIET stage/reset/stash: server/natural/mail_digest.py
  (diffhash 695234ae1147), tests/test_natural_mail_digest.py (1f3b5515efc9).
- ElevenLabs blijft premium/DPAPI met geaccepteerde stem; geen nieuwe echte sample.
  Oracle alleen read-only geïnspecteerd; installatie/cutover nog NIET goedgekeurd.
- Lokale backend herstart: health=ok/ready; Windows-snelkoppeling naar de geteste
  nieuwe build gezet. Eerstvolgend: checkpoint/push/PR en CI afronden; geen echte
  accounttest. Nieuwste gegevens staan ook in de PR en .local-testlogs.
