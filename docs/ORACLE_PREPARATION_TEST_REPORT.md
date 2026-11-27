# Oracle-voorbereiding — 27 november 2026

- Volledige serverregressie na cloudcompatibiliteit: 572 passed, 257,13 s.
- Aanvullende Oracle-ronde: 16 passed, 1 skipped. De drie deploymenttests zijn
  na de laatste scriptwijziging nogmaals geslaagd. Eén POSIX-eigendomscontrole
  kan op Windows niet draaien; Linux/ARM64 CI controleert die afzonderlijk.
- Tests gebruiken synthetische accounts/SQLite en nagebootste servicebesturing;
  geen echte OAuth-acties, ElevenLabs-aanvragen of remote installatie.
- Getest: verplichte HTTPS-origin, auth/CSRF/cookies achter proxy, afwijzen
  spoofing/dubbele headers, interne routegrens, lokale compatibiliteit,
  vault roundtrip/verkeerde sleutel, exacte Web OAuth-callback en CPU/modelpad.
- Backup: live WAL-snapshot, integriteit, encryptie, weigeren bestaand herstelpad,
  verkeerde sleutel zonder output, portable OAuth/Windows-DPAPI uitsluitend in
  een kopie. Deployment: onderhoudsfence, succesvolle omschakeling en echte
  synthetische database-/release-rollback na nagebootste readiness-fout.
- ARM64 Python 3.12: server- en inferencehelperafhankelijkheden volledig via
  binaire wheels resolveerbaar; geen modellen gedownload. Native ARM64 CI
  toegevoegd; daadwerkelijke resultaten worden in de PR gecontroleerd.
- Ruff, bestaande mypycontrole, pip check, contract- en repositorycheck geslaagd.
  Android unit/lint/debug/release opnieuw geslaagd. Windows portable build en
  128 clienttests eerder geslaagd; native app verbonden en premium ingesteld.
- Read-only SSH herhaald: bestaande A1 ARM64, 2 OCPU/12 GB, Ubuntu 24.04.5;
  geen eerdere software-installatie aangetroffen. Gratis IP-afgeleide DNS-naam
  resolveert; niets aan DNS/firewall/services gewijzigd.

Nog geen bewijs van echte Oracle-inferencelatentie, publiek TLS/renewal,
systemd/Caddy-configvalidatie of persoonlijke restore/cutover. Daarvoor is eerst
de afzonderlijke installatietoestemming vereist. Plan: deploy/oracle/README.md.

CI-review: workflow-YAML gecorrigeerd; onderhoudsfence expliciet tegen echte
backendconfiguratie en het deploymenttemplate getest. 14 gerichte tests passed,
1 POSIX-skip. Windows-runner had eerder vijf subprocess-start-timeouts;
opstartdeadline verruimd zonder assertions te veranderen.

Laatste volledige lokale reeks: **577 passed, 1 POSIX-skip**, 252,44 s.
Functioneel checkpoint **afd9586** heeft geslaagde PR-controles voor Windows-,
Linux- en ARM64-server, Windows-client, Android en repositorystructuur:
[PR 31](https://github.com/DeBeer05/jarvis/pull/31),
[server-CI](https://github.com/DeBeer05/jarvis/actions/runs/46016459643).
Een dubbele push-run had nog een Windows-job lopen bij de laatste snapshot.
De afsluitende wijziging betreft uitsluitend voortgangsdocumentatie.
