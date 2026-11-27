# Hervatpunt — agenda en Nederlands STT, 27 november 2026

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
