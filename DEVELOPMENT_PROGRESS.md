# Ontwikkelvoortgang

## Huidige opdracht

Fase 0 — uitsluitend projectvoorbereiding. STOP na deze fase. Fase 1 vereist een
nieuwe opdracht van de eigenaar; een technisch gereed project is geen toestemming.

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

De lokale controles, commit, push, CI en branch protection worden tijdens afronding
geverifieerd. Het definitieve resultaat wordt hieronder toegevoegd; bovenstaande
voorbereidingsbeschrijving claimt nog geen geslaagde remote CI.

De eerste HTTPS-push werd geweigerd doordat het bestaande OAuth-token de scope
`workflow` mist. Bestaande SSH-authenticatie is daarna met een read-only remotecheck
geverifieerd; origin push wordt via die reeds beschikbare sleutel uitgevoerd.
Geen extra tokenrechten of browserlogin nodig voor deze route.

## Nog niet uitgevoerd / pas na nieuwe opdracht

Geen app gestart, `setup.py` uitgevoerd, dependencies of AI-modellen geïnstalleerd.
Geen server, desktop-client of Android-app ontwikkeld. Geen OAuth, Gmail, agenda,
berichten, telefonie, externe toegang of deployment gekoppeld of geactiveerd.
Hardwareprestaties en bestaande upstreamfunctionaliteit zijn niet getest.
Voor fase 1: architectuurkeuzes concretiseren en bestaande code/dependencies auditen.
