# Upstreamreview — 22 november 2026

Bron: <https://github.com/FatihMakes/Mark-LVII>, basis
`752ff618a4e6a4bf2e675866b993071d739cfce2`, standaardbranch `main`,
56 commits bij clone. De laatste vijf commits zijn upload-/gitignorewijzigingen
op 11 november, 4 november en 17 oktober 2026 en 27 september 2026.
Volledige inspectie blijft mogelijk met `git log upstream/main`; geen historie gewist.

## Licentie en fork

De behouden `LICENSE` noemt FatihMakes, copyright 2026 en CC BY-NC 4.0:
<https://creativecommons.org/licenses/by-nc/4.0/legalcode>.
Niet-commerciële reproductie en bewerking zijn toegestaan onder de voorwaarden.
Behoud auteur, bron, copyright en licentie; vermeld aanpassingen. Commercieel
gebruik is niet toegestaan zonder afzonderlijke rechten. GitHub meldde
`allow_forking: true`; de eigen fork verwijst naar FatihMakes/Mark-LVII als parent.
GitHubs automatische SPDX-detectie gaf `NOASSERTION`; de daadwerkelijke
licentietekst is gecontroleerd in plaats van alleen dat metadata-veld.
Deze fork voegt uitsluitend projectvoorbereiding toe; auteur niet als sponsor voorstellen.

## Structuur en configuratie

Bestaande mappen staan in `PROJECT_STRUCTURE.md`. Configuratie bestaat uit
`.gitignore`, `AGENTS.md`, `requirements.txt`, `setup.py`, `config/` en de
runtimeconfigbeheerder `memory/config_manager.py`. Geen bestaande GitHub
Actions-workflow of root pyproject/Android-buildconfig aangetroffen.
`setup.py` installeert dependencies en Playwright-browsers en is daarom niet uitgevoerd.
Runtimegeheimen horen volgens upstream in `config/api_keys.json`, OAuth-tokenfiles
en dashboardsessies/certificaten; die bestanden zijn niet in de clone aangetroffen.
`providers/_tests.py` en `core/_smoke_harness.py` bestaan al, maar zijn geen bewijs
van actuele testdekking en zijn in fase 0 niet als applicatietest uitgevoerd.

## Controle op gevoelige gegevens

De huidige 109 upstreambestanden leverden geen treffers met de gebruikte
geheimpatronen op. De volledige lokale historie bevat echter een reeds openbare
privé-TLS-sleutel in `config/certs/jarvis.key` (blobprefix `b7b1138042e5`).
Toegevoegd in commit `067f528`, verwijderd in commit `8a79f40` op 25 augustus 2026.
De sleutel staat niet in de huidige tree. Waarden worden niet in rapporten getoond.
Omdat de opdracht de oorspronkelijke geschiedenis moet behouden, is deze niet
herschreven; de fork erft deze blootstelling. Gebruik deze sleutel nooit opnieuw.
Als iemand hem gebruikt, moet die installatie een nieuwe sleutel/certificaat krijgen.
Een aparte `python scripts/check_repository.py --history` rapporteert dit bewust
als fout. Normale CI controleert de actuele bestanden, niet een herschreven historie.
