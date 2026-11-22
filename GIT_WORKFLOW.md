# Git-workflow

## Remotes en basis

- `origin`: <https://github.com/DeBeer05/jarvis> — enige publicatiedoel.
- `upstream`: <https://github.com/FatihMakes/Mark-LVII> — alleen ophalen.
- `main`: stabiele versies; oorspronkelijke standaardbranch blijft behouden.
- `develop`: integratie; aanvankelijk gebaseerd op upstream `main`.
- `feature/*` en `fix/*`: vanaf `develop`; PR naar `develop`.
- `release/*`: vanaf `develop`; geteste release via PR naar `main`, daarna terug
  naar `develop` waar nodig.
- `hotfix/*`: vanaf `main`; PR naar `main` en correctie ook naar `develop`.

Branchnamen met `*` zijn patronen, geen letterlijk aangemaakte lege branches.
Git heeft geen instelling die elk willekeurig `git switch -c` automatisch vanaf
`develop` laat starten. Gebruik daarom de meegeleverde helpers met expliciete basis.

## Lokale configuratie en nieuwe branches

Na een nieuwe Windows-clone: `powershell.exe -NoProfile -File scripts/configure-git.ps1`.
De Windows-branchaliases gebruiken de ingebouwde Windows PowerShell 5.1;
een afzonderlijke `pwsh`-installatie is niet nodig. Op Linux/macOS blijft pwsh nodig
voor deze PowerShell-Git-helpers.
Dit stelt alleen repositorylokale opties in: push naar origin, fast-forward-only
pulls, pruning en de onderstaande aliases. Authenticatie blijft in de keyring;
gebruik `gh auth login` alleen als aanmelding ontbreekt. Upstream push is lokaal
geblokkeerd via `no_push://upstream-read-only`; upstream fetch blijft HTTPS.
Origin fetch gebruikt HTTPS; push gebruikt de bestaande geauthenticeerde SSH-key
(`git@github.com:DeBeer05/jarvis.git`). Het huidige CLI-OAuth-token mist de scope
`workflow`; de bestaande SSH-authenticatie kan workflows wel publiceren. Bij een
andere machine eerst SSH-authenticatie controleren of de benodigde scope regelen.

```powershell
git status --short --branch
Get-Content DEVELOPMENT_PROGRESS.md
git fetch origin
git switch develop
git pull --ff-only
git feature korte-naam
# alternatieven: git fix naam, git hotfix naam, git release versie
# of: powershell.exe -NoProfile -File scripts/new-branch.ps1 -Type feature -Name korte-naam
```

De helper weigert een vuile werkmap, controleert de branchnaam en gebruikt een
expliciete lokale basis. Haal die eerst bij; de helper haalt niets automatisch op.
`develop` is de lokale werkbranch na fase 0; GitHub houdt `main` als standaardbranch.

## Commits, push en PR

Gebruik Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`, `ci:`, `chore:`.
Stage specifieke bestanden en controleer `git diff --cached` en geheimen.
Maak kleine logische commits, bijvoorbeeld
`chore: initialize JARVIS development environment`.

```powershell
python scripts/check_repository.py
git diff --check
git push -u origin HEAD
gh pr create --repo DeBeer05/jarvis --base develop --title "chore: voorbereiding" --body-file pr-body.txt
gh pr checks --repo DeBeer05/jarvis --watch
```

Gebruik voor PR-tekst een lokaal tijdelijk bestand buiten gevolgde bronbestanden.
Geef altijd `--repo DeBeer05/jarvis` en de juiste `--base` op; stuur geen PR naar
upstream zonder aparte opdracht. `gh repo set-default DeBeer05/jarvis` is lokaal ingesteld.

Normale commits, branches, push, PR's en veilige merges binnen de opdracht mogen
zelfstandig worden uitgevoerd met de beschikbare rechten. Merge naar `develop`
pas na passende tests, geslaagde CI en review van de diff. Los conflicten inhoudelijk
op en herhaal relevante controles; vraag om richting bij onduidelijke gebruikerswijzigingen.
Voeg per taak voortgang en een vermelding onder Unreleased in `CHANGELOG.md` toe.
Voor releases: versie en changelog voorbereiden, passende releasechecks uitvoeren,
PR naar `main`, daarna integratie terug naar `develop`.

## Bescherming

Geen force-push naar gedeelde branches, geen onbekende wijzigingen verwijderen,
geen geheimen committen en geen branch protection omzeilen. Nooit ongeteste
functionaliteit naar `main` mergen. Een geslaagde structuurcheck is geen applicatietest.
De fase-0-initiële synchronisatie bevat alleen gecontroleerde voorbereiding.

Beoogde bescherming voor `main` en `develop`: PR verplicht (nul verplichte andere
reviewers voor dit eenpersoonsproject), actuele verplichte `Repository checks`,
gespreksresolutie, bescherming ook voor beheerders, geen force-push of verwijdering.
De werkelijke API-resultaten staan in `DEVELOPMENT_PROGRESS.md`.

Sinds fase 1 zijn op develop ook `Server tests (ubuntu-latest)` en
`Server tests (windows-latest)` verplicht, naast `Repository checks`, met
GitHub Actions als bron. Windows/Linux- en repositorychecks moeten op de actuele
basis slagen. Fase 1 mag uitsluitend naar develop; main blijft in deze opdracht
ongewijzigd. Fase 2 is afzonderlijk opgedragen en gebruikt dezelfde PR-/checkprocedure.
Main blijft ongewijzigd. Stop na fase 2; geen volgende fase zonder nieuwe opdracht.
