# CI/CD-plan

## Actief in fase 0

`Repository checks` in `.github/workflows/repository-check.yml` draait op push
en pull requests voor alle branches en op handmatige aanvraag. Alleen checkout
en een standaardbibliotheek-Pythoncontrole: vereiste structuur/documenten,
veilige voorbeeldconfiguratie, gitignoregedrag, gevolgde gevoelige bestandsnamen,
bekende geheimpatronen en `git diff --check`. Geen appimport of installatie van
`requirements.txt`. Workflow heeft uitsluitend `contents: read`, geen secrets,
geen artifacts met privédata en geen deployment. Checkout bewaart geen credentials.

Forks kunnen Actions standaard uitschakelen. Controleer de repositoryinstelling
en een echte run voordat een verplichte statuscheck wordt ingesteld.
Branch protection moet exact de checknaam `Repository checks` gebruiken.

## Later voorbereiden, nu niet activeren

| Workflow | Nodig voor activering |
| --- | --- |
| Python-tests | Geïsoleerde dependencies, unit-/contracttests en geschikte OS-matrix |
| Android-builds | Toolchainkeuze, SDK/Gradle, tests, signing via secretstore |
| Desktop-clienttests | Qt-testaanpak, Windows-runner, packaging en UI-smoketests |
| Security scanning | Dependency-/licentieaudit, secret scanning en passende SAST |
| Releases | Versies, changelog, geteste artifacts, provenance en getagde bron |
| Deployment | Eerst goedgekeurde omgeving, toegangsmodel, rollback en expliciete opdracht |

Structuur-CI bewijst geen functionele werking, volledige afwezigheid van geheimen
of productieveiligheid. De patrooncontrole wordt later aangevuld door een
gespecialiseerde scanner. Geen productieomgevingen of deployments aangemaakt.
