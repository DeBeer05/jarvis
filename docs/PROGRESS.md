# Hervatpunt — agenda en Nederlands STT, 27 november 2026

## Actueel: acht productfases persoonlijke butler

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
