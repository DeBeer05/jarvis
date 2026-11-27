# Hervatpunt — 27 november 2026

- Taak: ElevenLabs afronden, daarna Oracle ARM64 voorbereiden; geen productie-
  installatie/migratie zonder afzonderlijke eigenaargoedkeuring (§15/§16).
- Branch: feature/elevenlabs-voice, basis c320d7a / planning-PR 30.
- Gereed: centrale premium TTS, backend-only DPAPI-sleutel buiten project,
  gekozen ontworpen butlerstem, kostenreserveringen/schema 8, privacy/offline,
  fallback, annulering, Windows/Android-instellingen en Voice Studio.
- Echt getest: 73 tekens, Flash v2.5, 24000 Hz WAV, 3,854 s audio; volledige
  ontvangst 4,247 s. Eigenaar heeft stem beluisterd en bevestigd.
- Laatste tests: 559 servertests; 128 clienttests; Windows portable build;
  Android unit/lint/debug/release; Ruff/mypy en pip/repository/contractchecks.
- Artifacts: .local/client-build-premium-voice en .local/android-build.
- Voice-checkpoint a3bf859 gepusht. Premiumstem via bestaande geauthenticeerde
  API geactiveerd; nieuwe Windows-build geopend/verbonden, snelkoppeling bijgewerkt.
- Oracle voorbereid: opt-in strikt HTTPS-proxyprofiel, Linux OAuth-vault,
  CPU/modelpad, ARM64 CI, systemd/Caddy en backup-/update-timers (niet actief).
  scripts/cloud_backup.py: consistent WAL-snapshot, versleuteld archief, expliciete
  DPAPI-export alleen in kopie; deploy_release.py: exact root-goedgekeurd commit,
  onderhoudsfence, healthcheck en database/release-rollback.
- Laatste ronde: 572 volledige servertests; aanvullend 16 Oracle-tests geslaagd/
  1 POSIX-test overgeslagen op Windows; Android opnieuw unit/lint/debug/release OK.
  Ruff/mypy, pip/repository/contractchecks OK. CI nog controleren.
- Telefoon niet aangesloten; APK klaar onder .local/android-build.
- Oracle read-only gemeten: ARM64 Ubuntu 24.04.5, 2 OCPU/12 GB (IMDSv2),
  circa 49 GB vrij, geen swap/Ollama/reverse proxy. Niets remote geïnstalleerd.
- Cloudcompatibiliteit technisch voorbereid; echte systemd/Caddy-validatie,
  ARM-inferenceprestaties, TLS-renewal en persoonlijke cutover nog niet uitgevoerd.
- Streaming is per zinssegment; geen nieuw full-duplex/WSS-protocol geclaimd.
- Bestaande eigenaarwijzigingen niet stage/reset/stash: server/natural/mail_digest.py
  (diffhash 695234ae1147), tests/test_natural_mail_digest.py (1f3b5515efc9).
- Bestanden: server/natural/{elevenlabs,voice_usage,tts,models,settings,api}.py,
  server/{voice_secrets,config,database,mobile,redaction}.py, native instellingen,
  scripts/configure_elevenlabs.py, tests en ELEVENLABS_*.md. Zie git diff.
- Eerstvolgend: cloud-checkpoint/push/PR/CI afronden. Daarna afzonderlijk akkoord
  vragen op concrete Oracle-installatie (deploy/oracle/README.md); persoonlijke
  gegevensmigratie/cutover vereist apart akkoord. Windows blijft lokaal draaien.
- Cloud-checkpoint 2ecfe39 gepusht; draft PR 31. Bij CI-review YAML-quoting en
  onderhoudsfence gecorrigeerd naar de echte JARVIS_ENABLE_AUTOMATIONS-instelling;
  twee contracttests voorkomen dat alleen een gelijknamige mock wordt getest.
  Gerichte CI-fixronde 14 passed/1 POSIX-skip. Windows process-start-timeouts
  verruimd na echte runner-timeouts; assertions behouden. Nieuwe CI controleren.
