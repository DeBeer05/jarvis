# JARVIS Master Upgrade — 28 november 2026

De nieuwe eigenaaropdracht plaatst backend, database, geheugen en Life Engine op
de bestaande Oracle-VM. De mini-pc blijft een optionele lokale gateway; hij is nog
niet beschikbaar. Dit vervangt de vorige lokale-hubkeuze, zonder bestaande
apparaatrechten of privacykeuzes stilzwijgend te verruimen. Geen betaalde resources.

Werkbranch `feature/master-upgrade` bouwt noodzakelijk voort op de bestaande
hybride implementatie/PR33. Twee bestaande maildigest-eigenaarsdiffs blijven intact.

## Uitvoervolgorde en bewijs

1. [x] Analyse/nulmeting: bestaande routes, spraak, telemetry, infrastructuur.
   Oracle ARM64 2 CPU/12 GB, 32 GB vrij; inference/Caddy actief, backend ontbreekt.
   Gaming-pc RTX 4060/8 GB VRAM bevestigd. Bestaande centrale managers behouden.
   Drie HTTP/mockproeven: bevestiging mediaan 286,87 ms, weer 133,95 ms,
   nul modelcalls voor weer. Geen claim over microfoon/eerste hoorbare audio.
2. [x] Snelheid: stage-timings, p50/p95/p99, pooling en begrensde concurrency.
   Bestaande stage-timings uitgebreid met database-start/relevante geheugenlookup.
   Afzonderlijke voortgangs-/inhoudelijke-/finale audiometingen; ontbrekende samples
   blijven ontbrekend. ElevenLabs hergebruikt nu begrensde TLS-connecties en sluit
   ze bij shutdown. Twintig gerichte latency/diagnostiek/premium-regressies groen.
   Audiostreaming/clientinstrumentatie volgen in fase 3; doelwaarden niet geclaimd.
3. [ ] Realtime/tussenzinnen: 100 unieke Nederlandse zinnen, vooraf genereren,
   stemgebonden cache, clients, prioriteit/annulering, afzonderlijke audiometingen.
   Techniek geïmplementeerd: beschermde PCM-streaming, herbruikbare STT-WebSocket,
   begrensde buffers, stop/revocation, stemgebonden cache en honderd unieke zinnen.
   Windows/Android spelen inhoudelijke PCM vóór voltooiing van de synthese af;
   voortgangsaudio krijgt afzonderlijke timings en wijkt voor inhoudelijk antwoord.
   De geselecteerde premiumstem vraagt 2.630 tekens versus bestaande daglimiet
   2.000: vraag over eenmalig maximaal 3.000 bestaande credits staat nog open.
   Geen premiumbatch uitgevoerd of limiet verhoogd. Technische mocks zijn geen
   bewijs voor honderd werkelijk opgenomen bestanden of fysieke luisterlatency.
   Controles tot nu: 48 gerichte servertests, 155 clienttests; Android unit/lint/
   debug/release gebouwd. Laatste kleine cachewijzigingen worden opnieuw getest.
   Eén noodzakelijke kleine dependency: websockets 17.4, uitsluitend geïsoleerd.
4. [x] Persoonlijkheid: bestaande gedeelde Nederlandse stijl behouden; vaste
   functie-/taakantwoorden gebruiken nu u/uw en onthullen geen toolnaam of taak-ID.
   Werkelijke bevoegdheden blijven leidend; geen universele bevestigingsplicht
   in de functie-uitleg. Configuratie en stem blijven per eigenaar synchroniseren.
5. [ ] Infrastructuur: Oracle-backend, back-up/restore/rollback, systemd, TLS;
   mini-pc-gatewaypakket, optionele beschikbare Windows-compute.
6. [ ] Geheugen/Life Engine: bestaande CRUD/FTS/items/scheduler uitbreiden voor
   verplichtingen, deadlines en herleidbare prioriteiten, zonder modelpolling.
7. [ ] Agenda/communicatie: bestaande bewijs-/approvalroutes; officiële koppelingen.
8. [ ] Proactiviteit: bestaande briefings/events/stille uren/deduplicatie.
9. [ ] Home Assistant/externe informatie: lokale uitvoer en configuratiegrenzen.
10. [ ] Instellingen/dashboard: schema en beide native clients.
11. [ ] Betrouwbaarheid: authenticatie, budgetten, herstel en uitvaltests.
12. [ ] Finale tests, artifacts, Nederlandse handleiding, Git/CI en deployment.

Elke fase wordt pas afgerond na gerichte controles. Fysieke luisteracceptatie,
mini-pc en ontbrekende externe accounts gelden niet als bewezen door mocks.
Ontvangstaudio verbergt nooit de tijd tot de eerste inhoudelijke/finale audio.
100 premium-opnames mogen bestaande kostenlimieten niet ongemerkt overschrijden.
