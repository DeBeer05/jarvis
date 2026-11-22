# Setupchecklist

## Fase 0

- [x] Bestaande werkmap eerst bekeken en leeg bevonden.
- [x] Windows, Git, GitHub CLI/auth, Python, Java en schijfruimte gecontroleerd.
- [x] Mark-LVII-licentie, standaardbranch, geschiedenis en configuratie bekeken.
- [x] Eigen fork gemaakt en volledige historie behouden.
- [x] Origin/upstream ingericht; upstream push lokaal geblokkeerd.
- [x] Main behouden en develop vanaf de bestaande basis aangemaakt.
- [x] Structuur aangevuld zonder applicatiecode te veranderen.
- [x] Gitignore en veilig configuratievoorbeeld voorbereid.
- [x] Documentatie, AGENTS.md, branchhelpers en basis-CI voorbereid.
- [x] Initiële gevolgde bestanden op bekende geheimpatronen onderzocht.

## Technische afronding

- [x] Lokale structuur-, gitignore-, syntaxis- en whitespacechecks geslaagd.
- [x] Voorbereidingscommit gemaakt met behoud van de oorspronkelijke historie.
- [x] Push naar eigen main en develop bevestigd.
- [x] Echte CI op beide branches geslaagd.
- [x] Branch protection op main en develop via API ingesteld en teruggelezen.
- [x] Historische TLS-sleutel als resterende blootstelling gedocumenteerd.

Exacte resultaten en CI-links staan in `DEVELOPMENT_PROGRESS.md`. De eerste
afrondingsdocumentatie is via PR #1 en #2 met geslaagde CI verwerkt.
De latere hercontrole, veilige reparaties en de resterende historische sleutel
staan per controle in `docs/PHASE_0_AUDIT.md`.

## Voor eventuele fase 1 — nog niet uitvoeren

- [ ] Nieuwe opdracht voor daadwerkelijke ontwikkeling ontvangen.
- [ ] Hergebruik van gui/dashboard/providers en servergrenzen besluiten.
- [ ] Dependency-/licentie- en veiligheidsaudit van bestaande code afronden.
- [ ] Teststrategie en haalbare RAM-/CPU-budgetten meten op de 8-GB-doelmachine.
- [ ] Pas daarna een geïsoleerde ontwikkelomgeving en nodige dependencies kiezen.
- [ ] Android-toolchain pas installeren zodra mobiel werk is opgedragen.
- [ ] OAuth-scopes, toestemmingen en bewaartermijnen per integratie bepalen.
- [ ] Toegang van buiten pas na goedgekeurd beveiligingsontwerp inschakelen.

Een fork is publiek zoals de upstreambron. Bewaar geen persoonsgegevens,
credentials, sessies, opnames of privéconfiguratie in commits of PR's.
