# CI/CD-plan

## Actief in fase 3

De matrix draait ook 57 nieuwe beveiligings-/procesgevallen (156 tests totaal),
met tijdelijke accounts/databases, echte authenticatie en een echte TCP-herstartproef.
Argon2id wordt geïsoleerd geïnstalleerd. De installer wordt eerst met constraints
naar pip 26.3 bijgewerkt vanwege gevonden advisories. Vier frontend-JavaScript-
bestanden krijgen syntaxcontrole. De drie verplichte develop-checks blijven staan.
Pip-audit, Bandit en Gitleaks zijn daarnaast lokaal uitgevoerd/te controleren
vóór push; ze zijn geen nieuwe verplichte automatische CI-jobs. Zie het
[fase-3-testverslag](PHASE_3_TEST_REPORT.md) voor scope en reproduceerbare opdrachten.

## Actief in fase 2

De bestaande Windows-/Linuxmatrix voert nu ook de Gemini-/Groq-/Ollama-transporttests,
router/fallback, streaming/annulering, chat-API, migratie/geheugen en webchatchecks
uit. Providers zijn mocks: geen API-sleutels, kosten of modeldownloads in CI.
JavaScript wordt aanvullend met `node --check` op syntax gecontroleerd; geen npm
of frontendbuild. De drie vereiste develop-checks blijven ongewijzigd.

## Actief sinds fase 1

`server-tests.yml` installeert alleen de minimale vastgelegde server- en
testdependencies in een venv en voert pytest/pip check uit op Python 3.12,
Windows en Linux. Windows voert bovendien de start/status/stopscripts uit onder
zowel Windows PowerShell 5.1 (`powershell`) als PowerShell 7 (`pwsh`).
Geen productie-deployment, GUI-/audio-/modelinstallaties of externe AI-aanroepen.
De bestaande repositorycheck blijft actief; `.env.example` bevat nu de veilige
fase-2-defaults. Beide OS-serverchecks en `Repository checks` zijn via de
develop-branchbescherming verplicht gemaakt en geslaagd vóór de fase-1-merge.
De Actions zijn op officiële releasecommits gepind: checkout v7.0.1 en
setup-python v7.1.0, beide met Node 24 in hun actionmetadata. Dit vervangt de
oudere Node-20-actions die GitHub in de eerste runs via compatibiliteit uitvoerde.

## Actief in fase 0

`Repository checks` in `.github/workflows/repository-check.yml` draait op push
en pull requests voor alle branches en op handmatige aanvraag. Alleen checkout
en een standaardbibliotheek-Pythoncontrole: vereiste structuur/documenten,
veilige voorbeeldconfiguratie, gitignoregedrag, gevolgde gevoelige bestandsnamen
en bekende geheimpatronen in zowel werkmap als Git-index. De whitespacecheck
vergelijkt een PR met de basiscommit en een push met de vorige branchcommit;
bij een nieuwe branch of handmatige run wordt de laatste commit gecontroleerd.
Daarvoor haalt checkout de volledige geschiedenis op. Geen appimport of installatie van
`requirements.txt`. Workflow heeft uitsluitend `contents: read`, geen secrets,
geen artifacts met privédata en geen deployment. Checkout bewaart geen credentials.

Forks kunnen Actions standaard uitschakelen. Controleer de repositoryinstelling
en een echte run voordat een verplichte statuscheck wordt ingesteld.
Branch protection moet exact de checknaam `Repository checks` gebruiken.

## Later voorbereiden, nu niet activeren

| Workflow | Nodig voor activering |
| --- | --- |
| Overige Python-tests | Servertests zijn actief; desktoptests pas bij latere opdracht; headless AI-tests nu actief |
| Android-builds | Toolchainkeuze, SDK/Gradle, tests, signing via secretstore |
| Desktop-clienttests | Qt-testaanpak, Windows-runner, packaging en UI-smoketests |
| Security scanning | Dependency-/licentieaudit, secret scanning en passende SAST |
| Releases | Versies, changelog, geteste artifacts, provenance en getagde bron |
| Deployment | Eerst goedgekeurde omgeving, toegangsmodel, rollback en expliciete opdracht |

Structuur-CI bewijst geen functionele werking, volledige afwezigheid van geheimen
of productieveiligheid. De patrooncontrole wordt later aangevuld door een
gespecialiseerde scanner. Geen productieomgevingen of deployments aangemaakt.
