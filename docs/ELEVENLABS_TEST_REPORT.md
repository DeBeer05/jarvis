# Premium stem: testverslag

25 november 2026, ontwikkeldesktop. Echte proef in een geïsoleerde tijdelijke
database, zonder Google-accounttest, echte berichten of migratie.

## Werkelijk uitgevoerd

Hervat op 27 november: bewaarde volledige ronde **559 geslaagd in 225,03 s**;
clientreeks **128 geslaagd in 6,85 s**. Eerdere resultaten hieronder behouden.

- DPAPI-sleutelopslag buiten het project en backendconfiguratie geslaagd.
- Werkelijke accountauthenticatie, Nederlandse modelmetadata, stemlijst en
  tegoedcontrole geslaagd; account meldde Free met aanvankelijk 10000 credits.
- Eén Nederlandse proef via de bestaande geauthenticeerde synthese-API:
  ElevenLabs Flash v2.5, 73 tekens, mono PCM16 WAV/24000 Hz, niet-stille audio
  van 3,854 s; complete ontvangst na 4,247 s. Fallback stond uit.
- Eigenaar heeft beluisterd en ‘Deze stem gebruiken’ bevestigd. Nieuwe native
  app-/headsetacceptatie blijft daarvan onderscheiden.
- 33 gerichte servertests, daarna 63 bredere regressies geslaagd. 128 clienttests.
- Android unit tests/lint/debug-/releasebuild en Windows portable build geslaagd.
  Ruff/mypy geslaagd. Definitieve brede test- en CI-resultaten staan bij de PR.

De eerste brede ronde telde 558 geslaagde tests plus één oude verwachting die
alleen de drie oude TTS-providers toeliet. Deze is aangepast aan de gevraagde
vierde provider; de relevante instellingenregressies slagen daarna.

Mocks testen 401/403/429/503, veilige fouten, Nederlandse modelselectie, WAV,
ondersteunde parameters, begrensde previews, cache zonder nieuwe kosten,
annulering/gesloten stream met behouden reservering, lokaal/offline, privacy
vóór opmaak, DPAPI roundtrip, bestaande TTS-pins en migratiebackup.
Normale pytest/CI doet geen echte ElevenLabs-aanvragen. De aparte
`scripts/test_elevenlabs_live.py --run --voice-id ...` kan credits kosten.

## Grenzen

4,247 s is tijd tot compleet ontvangen audio, geen eerste hoorbare audio of
model-latency alleen. Geen Oracle-prestatieclaim op basis van desktop. Streaming
naar clients blijft per zinssegment. Kosten zijn gereserveerde schattingen en
accountcijfers momentopnamen. Geen abonnement/credits gekocht of stem gekloond.

Oracle alleen-lezen geïnspecteerd: aarch64, Ubuntu 24.04.5, Python 3.12.3,
2 OCPU/12 GB volgens IMDSv2, circa 49 GB vrij, geen swap. Hostfirewall laat
alleen SSH toe; 8765/11434 niet publiek open. Geen installatie, firewallwijziging
of dataoverdracht uitgevoerd. Cloudinstallatie/productiemigratie vereist de
afzonderlijke goedkeuring uit de eigenaarsopdracht §15/§16.
