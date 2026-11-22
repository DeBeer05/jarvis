# Ontwikkelvoortgang

## Huidige opdracht

Fase 1 — headless Windows-server, voltooid na de opdracht van 22 november 2026.
Opleverbranch: `develop`. Implementatiebranch `feature/headless-server` is gepusht
en via PR #5 gemerged, vanuit develop-basis `f4b0053`.
Main blijft ongewijzigd. STOP na fase 1; fase 2 is niet toegestaan.
De onderstaande fase-0-secties vormen de bewaarde voorgeschiedenis.

## Uitgangspunt — 22 november 2026 (Europe/Amsterdam)

- Bestaande werkmap `J.A.R.V.I.S` was volledig leeg, inclusief verborgen bestanden.
- Mark-LVII rechtstreeks gecloned; geen extra projectmap aangemaakt.
- Upstream: <https://github.com/FatihMakes/Mark-LVII>, standaardbranch `main`.
- Basiscommit: `752ff618a4e6a4bf2e675866b993071d739cfce2`.
- Alle 56 oorspronkelijke commits behouden; geen shallow clone of herschreven historie.
- Eigen publieke fork: <https://github.com/DeBeer05/jarvis>.
- Licentie: CC BY-NC 4.0; naamsvermelding/licentie behouden, uitsluitend niet-commercieel.
- Upstream-applicatiecode en dependencybestanden blijven ongewijzigd.

## Omgeving

| Onderdeel | Gecontroleerd resultaat |
| --- | --- |
| Windows | Windows 11 Home, 10.0.26300, 64 bits |
| Git | 2.49.0.windows.1 |
| GitHub CLI | 2.105.0, aangemeld als DeBeer05 via Windows keyring |
| Python | 3.13.3; upstream setup noemt 3.11 t/m 3.13 |
| Java | 17.0.12 LTS; Android SDK/Gradle nog niet gecontroleerd of geïnstalleerd |
| Vrije ruimte | Circa 41,23 GB op C: bij aanvang; momentopname |
| Aanvang Git-status | Geen repository, bestanden of gebruikerswijzigingen aanwezig |

GitHub CLI stond al geïnstalleerd en in het permanente PATH. De lopende shell
had een ouder PATH; hiervoor is het bestaande absolute programmapad gebruikt.
Winget bevestigde de bestaande installatie; geen nieuwe dependencies geïnstalleerd.
Commits gebruiken lokaal het GitHub noreply-adres in plaats van een privé-e-mailadres.

## Voorbereidingsresultaat

- `origin` is de eigen fork; `upstream` haalt alleen de oorspronkelijke bron op.
  De lokale push-URL voor upstream is bewust geblokkeerd.
- `main` behouden; `develop` vanaf upstream `main` gemaakt.
- Aanvullende lege mappen met `.gitkeep`; bestaande `config/`, GUI, dashboard,
  providers, acties, geheugen en agents behouden.
- Uitsluitingen aangevuld, veilig `.env.example`, projectdocumentatie,
  blijvende agentinstructies, Git-hulpscripts en minimale structuur-CI toegevoegd.
- Initiële controle van 109 gevolgde upstreambestanden: geen treffers met de
  gebruikte geheimpatronen. Dit is een patrooncontrole, geen volledige securityaudit.

## Controle op gevoelige gegevens

Historische scan: 415 unieke blobs onderzocht (binaire inhoud overgeslagen).
Eén treffer: oude upstream privé-TLS-sleutel `config/certs/jarvis.key`, blobprefix
`b7b1138042e5`, toegevoegd in `067f528` en verwijderd in `8a79f40` op
25 augustus 2026. Niet aanwezig in de huidige tree. De oorspronkelijke historie
blijft volgens opdracht behouden; daarom blijft deze bekende blootstelling in de
forkhistorie bestaan. Sleutel niet hergebruiken; vervangen waar die nog gebruikt wordt.
`--history` blijft dit als fout rapporteren, zonder sleutelinhoud te tonen.

De gitignorepadcontrole is gecorrigeerd voor Windows-CRLF op subprocess-stdin;
de herhaalde normale repositorycheck slaagt: 10 mappen, 16 vereiste bestanden en
128 actuele bestanden gecontroleerd. Ook onwerkzame upstream-gitignorepatronen
met inline commentaar zijn aangevuld met geldige patronen; de originele regels
blijven behouden. Persoonlijke taakstatus en rapporten zijn aanvullend uitgesloten.
Python- en PowerShell-syntaxis en whitespace gecontroleerd. De branchhelper
weigert een vuile werkmap zonder van branch te wisselen. Oorspronkelijke inhoud
van readme.md, AGENTS.md en .gitignore aantoonbaar behouden.

## Afrondingscontrole

Voorbereidingscommit `8c0c60f42be2f9614a5c6bcfa410abb26463dd4b`:
`chore: initialize JARVIS development environment`.
Lokaal gecontroleerd en naar de eigen fork gepusht op zowel `develop` als `main`.
De initiële synchronisatie naar main was fast-forward, vóór activering van
branch protection, en bevatte uitsluitend de geteste voorbereiding.

| Eindcontrole | Resultaat |
| --- | --- |
| Git / GitHub | Werkend; eigen fork en SSH-push geverifieerd |
| Remotes | origin eigen fork; upstream oorspronkelijke bron, lokaal geen push |
| Branches | main en develop lokaal en remote aanwezig; main blijft standaard |
| Structuur / gitignore | 10 vereiste mappen en alle gevoelige proefpaden gecontroleerd |
| Agentinstructies / documentatie | Alle vereiste documenten aanwezig; upstreamtekst behouden |
| Geheimen actuele tree | Geen treffers in gebruikte patronen; geen gevolgde genegeerde paden |
| Historische geheimcontrole | Eén bekende oude TLS-sleutel; zie aparte sectie hierboven |
| Python / PowerShell | Controlescript en helpers syntactisch geldig |
| Branchhelpers | Vuile tree geweigerd; featurebranch correct vanaf develop gemaakt |
| Commit / push | Voorbereidingscommit remote bevestigd; geen force-push |
| CI develop | Geslaagd: <https://github.com/DeBeer05/jarvis/actions/runs/45051645564> |
| CI main | Geslaagd: <https://github.com/DeBeer05/jarvis/actions/runs/45051665939> |
| Branch protection | Via API ingesteld en teruggelezen voor main en develop |

Branch protection vereist een PR, actuele `Repository checks` van de GitHub
Actions-app en opgeloste gesprekken. Nul verplichte andere reviewers voor deze
persoonlijke repository; beheerder is eveneens gebonden, force-push en verwijdering
zijn uitgeschakeld. De afrondingsdocumentatie is via PR #1 en #2 met geslaagde
checks naar develop en main gemerged; de branchkoppen zijn respectievelijk
`548665c` en `def53ba` bij aanvang van de onderstaande hercontrole.
Geen productie-deployment of applicatietests uitgevoerd.

De eerste HTTPS-push werd geweigerd doordat het bestaande OAuth-token de scope
`workflow` mist. Bestaande SSH-authenticatie is daarna met een read-only remotecheck
geverifieerd; origin push wordt via die reeds beschikbare sleutel uitgevoerd.
Geen extra tokenrechten of browserlogin nodig voor deze route.

## Status en handmatige vervolgstappen

Fase 0 is technisch voorbereid. Geen handmatige login/installatie vereist voor
deze werkplek. Een eventueel nog gebruikte historische upstream-TLS-sleutel moet
door de gebruiker van die installatie worden vervangen; deze voorbereiding heeft
geen installatie gestart of sleutel hergebruikt. Op andere werkplekken gelden de
authenticatie- en lokale configuratiestappen in GIT_WORKFLOW.md.
De app zelf is nog niet geïnstalleerd of functioneel gevalideerd. De historische
geheimblootstelling en latere veiligheidsaudit blijven expliciete aandachtspunten.
De volgende stap vereist een nieuwe opdracht. **STOP: geen fase 1 gestart.**

## Nog niet uitgevoerd / pas na nieuwe opdracht

Geen app gestart, `setup.py` uitgevoerd, dependencies of AI-modellen geïnstalleerd.
Geen server, desktop-client of Android-app ontwikkeld. Geen OAuth, Gmail, agenda,
berichten, telefonie, externe toegang of deployment gekoppeld of geactiveerd.
Hardwareprestaties en bestaande upstreamfunctionaliteit zijn niet getest.
Voor fase 1: architectuurkeuzes concretiseren en bestaande code/dependencies auditen.

## Hercontrole fase 0 — 22 november 2026

Alle twaalf gevraagde controles zijn apart vastgelegd in
[docs/PHASE_0_AUDIT.md](docs/PHASE_0_AUDIT.md). Repository, remotes, branches,
structuur, agentinstructies, Git-publicatie en beschermingsregels zijn bevestigd.
Geen ongepubliceerde commits op actieve lokale branches bij aanvang.
De actuele branchkoppen hadden geslaagde CI op main (run `45051885547`) en
develop (run `45051843093`).

Veilig herstel: geheimpatronen ook op Git-indexblobs controleren; CI-whitespace
op daadwerkelijke PR-/pushwijzigingen controleren. Gerichte regressiecontroles
met synthetische fixtures zijn geslaagd. Alleen voorbereidingsbestanden gewijzigd.

Aanvullende lokale Gitleaks 8.30.1-scan: nul bevindingen in de actuele gevolgde
tree, één reeds bekende privé-TLS-sleutel in de geschiedenis van alle refs.
Daarom is de volledige historie niet geheimvrij; die is niet herschreven.
Herstelcommit `b4b151e` is gepubliceerd op origin/fix/phase0-audit in
[PR #3](https://github.com/DeBeer05/jarvis/pull/3). De vernieuwde CI is geslaagd
op de featurepush (run `45052725626`) en PR (run `45052729305`).
Integratie naar develop en main gebruikt de beschermde PR-route, zonder bypass.
De ontwikkelbasis is gereed met deze expliciete historische uitzondering.
Geen handmatige setup nodig; een eventueel nog gebruikte oude sleutel vervangen.
**Geen fase 1 of applicatieontwikkeling gestart.**

## Fase 1 — implementatie en lokale validatie

- Fase 0 opnieuw gecontroleerd: schone Git-status, correcte remotes, volledige
  upstreambasis en geslaagde CI op develop. Bekende historische TLS-sleutel blijft
  gedocumenteerd en wordt niet gebruikt.
- Python 3.12.10 per gebruiker geïnstalleerd; geïsoleerde `.venv` voorbereid met
  alleen server-/testdependencies. Geen desktop-/audio-/modelstack geïnstalleerd.
- Nieuwe `server/`-module: FastAPI-factory/lifespan, localhost-entrypoint,
  health/ready/status, centrale .env-config, begrensde JSON-logs, SQLite met
  migratieversie en korte verbindingen, lokaal procesbeheer en gecontroleerde stop.
- PowerShell-scripts voor omgeving, dependencies, start, status en stop toegevoegd.
- Bestaande Mark-LVII-applicatiebestanden blijven ongewijzigd; cloud/dashboard
  worden niet geïmporteerd omdat zij netwerkbediening/AI/taken activeren.
- Eerste testrun: **37 geslaagd**, 3,19 s; één deprecatiewaarschuwing vanuit de
  huidige Starlette-httpx-testadapter, geen testfouten.
- Voor commit: relevante tests, repositorychecks, whitespace en geheimscan.
  Volgende stappen: verdere foutpaden, echte Windows-script-/prestatiemeting,
  Nederlandse documentatie, server-CI en PR naar develop. Nog niet gemerged.

### Fase 1 — Windows-validatie en CI voorbereiden

- Functionele commit: `d1bfe56`; console-interrupt/ownershipherstel: `9cb37da`.
  Actieve ontwikkelbranch blijft `feature/headless-server`; main is niet gewijzigd.
- **39 pytest-tests geslaagd** op Python 3.12.10; meest recente lokale run 2,74 s.
  Getest: app/lifespan, alle drie endpoints, statusafscherming, Host-/proxybeleid,
  config/ongeldige .env, SQLite/migraties/corruptie/cleanup, fouten zonder secrets,
  JSON-logrotatie/redactie, import zonder GUI/audio/AI, instance-lock, echte
  processtart/stop en interrupt-cleanup. `pip check` geslaagd.
- Alle vijf Windows-scripts daadwerkelijk uitgevoerd: omgeving voorbereiden,
  minimale dependencies installeren, start in achtergrond, status en stop.
  Live health/ready/status geslaagd; precies één luistersocket op 127.0.0.1:8765.
  Runtimecontrolbestand na shutdown verwijderd. Geen service geïnstalleerd.
- Gemeten op de 31,95-GiB-ontwikkeldesktop: working set 46,90 MiB, private memory
  34,70 MiB, processtart tot waargenomen ready 844,2 ms, startscript totaal 1141 ms.
  Idle-CPU 0,000% in 3,013 s op één-kernschaal; korte momentopname, geen garantie
  voor het uiteindelijke 8-GB-apparaat.
- Nieuwe documenten: `docs/HEADLESS_SERVER.md`, `docs/SERVER_API.md`; README,
  structuur, architectuur en CI-plan bijgewerkt. `server-tests.yml` test Windows
  en Linux in geïsoleerde Python-3.12-omgevingen, inclusief Windows-controlscripts.
- Alle oorspronkelijke upstream-Python-bestanden zijn ongewijzigd en statisch
  op syntax gecontroleerd. Desktop-/cloudfunctionaliteit niet interactief gestart.
- Bekend: één deprecatiewaarschuwing van Starlette/httpx in tests; geen testfout.
  Oude TLS-sleutel blijft alleen in de upstreamhistorie; wordt niet hergebruikt.
- PR/merge: nog te publiceren; echte CI wordt vóór merge gecontroleerd.
  Volgende stap: feature push/PR naar develop, verplichte CI bevestigen en veilig
  integreren. **STOP na fase 1; geen fase 2.**

### Oplevering fase 1 — voltooid

- Functionele commits: `d1bfe56` (serverbasis/tests), `9cb37da` (console-interrupt),
  `4fe0dde` (Windows/Linux-CI en handleiding). Laatste bevestigde functionele
  integratiecommit: `6396534dc8ed78484988b42f2ee5bbe490b375fd`.
  Voor de meest recente rapportagecommit is `git log -1 --oneline` leidend.
- [PR #5](https://github.com/DeBeer05/jarvis/pull/5) is **MERGED** naar develop.
  Featurebranch is gepubliceerd; geen force-push, admin-bypass of main-merge.
- Echte PR-CI geslaagd:
  [repository](https://github.com/DeBeer05/jarvis/actions/runs/45055119967),
  [39 tests op Windows en Linux](https://github.com/DeBeer05/jarvis/actions/runs/45055120044).
- Ook CI op de daadwerkelijke develop-mergecommit is geslaagd:
  [repository](https://github.com/DeBeer05/jarvis/actions/runs/45055280413),
  [Windows/Linux-servertests](https://github.com/DeBeer05/jarvis/actions/runs/45055280439).
- Develop vereist nu alle drie checks: `Repository checks`,
  `Server tests (ubuntu-latest)` en `Server tests (windows-latest)`, telkens van
  GitHub Actions, actuele basis vereist. PR-/admin-/force-pushbescherming behouden.
- Main lokaal en remote blijft `c995834127bf447aac653d050b67039a27223933`.
- Gewijzigde bestanden: nieuwe `server/`-modules, zes `tests/test_server_*.py`-
  bestanden plus conftest, zes PowerShell-serverhelpers, geïsoleerde requirements/
  constraints, pytest-config en serverworkflow; .env.example, .gitignore,
  repositorycheck, AGENTS, voortgang/changelog, README/architectuur/structuur/CI-plan
  bijgewerkt. Volledige lijst: `git diff --stat f4b0053 6396534`.
- Acceptatie: headless start zonder GUI/audio/GPU/AI, alle drie endpoints,
  SQLite-initialisatie/migratie/readiness/cleanup, begrensde logs, Windows-scripts,
  tests, documentatie, commits, push en toegestane develop-merge: **gehaald**.
- Geteste server is na validatie gestopt. Geen permanente service of auto-start;
  `.venv` en de lokale lege schema-database/logs blijven als genegeerde lokale data.
- Actieve werkbranch bij oplevering is develop; rapportage wordt eveneens met
  normale commits/PR en verplichte CI geïntegreerd. Geen handmatige actie nodig
  om deze werkplek voor te bereiden; starten kan met de handleiding.
- Bekende punten: één Starlette/httpx-deprecatiewaarschuwing in tests; geen
  functionele testfout. Oude upstream-TLS-sleutel blijft in de behouden historie
  en wordt niet gebruikt. De 8-GB-doelmachine is nog niet afzonderlijk gemeten.
- Volgende fase: uitsluitend na een nieuwe opdracht. **STOP; fase 2 niet gestart.**
