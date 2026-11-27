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
- Nog doen: actieve app van handmatige Piper naar bevestigde premiumstem;
  laatste controles/checkpoint/push/PR/CI; Oracle deployment/backups voorbereiden.
- Oracle read-only gemeten: ARM64 Ubuntu 24.04.5, 2 OCPU/12 GB (IMDSv2),
  circa 49 GB vrij, geen swap/Ollama/reverse proxy. Niets remote geïnstalleerd.
- Bekende cloudblokkades: OAuth-vault is Windows-DPAPI-only; persoonlijke routes
  zijn loopback-only; deze moeten veilig opt-in cloudcompatibel worden.
- Streaming is per zinssegment; geen nieuw full-duplex/WSS-protocol geclaimd.
- Bestaande eigenaarwijzigingen niet stage/reset/stash: server/natural/mail_digest.py
  (diffhash 695234ae1147), tests/test_natural_mail_digest.py (1f3b5515efc9).
- Bestanden: server/natural/{elevenlabs,voice_usage,tts,models,settings,api}.py,
  server/{voice_secrets,config,database,mobile,redaction}.py, native instellingen,
  scripts/configure_elevenlabs.py, tests en ELEVENLABS_*.md. Zie git diff.
- Eerstvolgend: bevestig schone eigen diff en bewaar voice-checkpoint; activeer
  geteste lokale build via bestaande app, daarna werk cloudvoorbereiding af.
