# Changelog

Wijzigingen van deze fork; oorspronkelijke geschiedenis en licentie blijven behouden.

## Unreleased

- Fase 2: gedeelde Gemini/Ollama-teksttransportlaag, centrale fallbackrouter,
  begrensde chat-API/SSE, annuleerbare antwoorden, SQLite-gesprekken en lokale webchat.
- Windows-instructies en Git-branchhelpers gebruiken de ingebouwde PowerShell
  5.1; geen verplichte pwsh-installatie. Windows-CI test beide PowerShell-edities.
- Fase 1: lichte localhost-headlessbasis met health/ready/status, .env-config,
  JSON-logrotatie, SQLite, gecontroleerd procesbeheer, Windows-scripts en pytest.
- Fase 1 via PR #5 geïntegreerd naar develop, met 39 geslaagde tests op Windows
  en Linux, verplichte serverchecks en lokaal gemeten prestatiecijfers.
- Fase-0-hercontrole: staged bestanden afzonderlijk op geheimpatronen controleren;
  CI-whitespacecontrole op de daadwerkelijke PR-/pushwijzigingen richten.
- Fase 0: projectstructuur, ontwikkelplan, blijvende Codex-instructies,
  geheimuitsluitingen, Git-workflowhelpers en minimale repository-CI voorbereid.
- Fase 0 wijzigde geen applicatiecode; fase 1/2 voegen de lokale server toe.
  Geen actieve accountintegraties of deployment.
- Origin/upstream en lokale branchhelpers ingericht; echte CI op main/develop
  geslaagd en branch protection ingeschakeld. Historische upstream-TLS-sleutel
  gedocumenteerd zonder de vereiste bronhistorie te herschrijven.
