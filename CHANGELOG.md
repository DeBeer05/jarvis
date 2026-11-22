# Changelog

Wijzigingen van deze fork; oorspronkelijke geschiedenis en licentie blijven behouden.

## Unreleased

- Fase 3 / 0.3.0: lokale eenmalige eigenaarsetup, Argon2id, beveiligde webchat,
  HttpOnly-sessies/CSRF, korte opaque tokens, refreshrotatie/replay-intrekking,
  sessie- en wachtwoordbeheer, default-deny en afzonderlijke apparaatrechten.
- Veilige apparaatpairing met menselijk vergeleken code, expliciete goedkeuring
  en S256-bewijs; apparaat hernoemen/intrekken/verwijderen, begrensd auditlog.
- SQLite-schema 3 met pre-migratieback-up en behoud van gesprekken; aparte
  procescontrolstatus. 156 tests inclusief echte tijdelijke TCP/herstartflow.
- Serverinstaller/CI werkt pip bij naar vastgelegde 26.3; lokale dependencyaudit
  en Bandit zonder actuele bevindingen. Nederlandse auth-/pairing-/securitydocs.
- Alleen ontwikkeldesktop localhost:8765; geen nieuwe clients of externe toegang.

- Lokale herhalingsmelding: nieuwste-berichtregressie toegevoegd, Ollama-temperature
  0.2 en lokale Qwen2.5 3B-keuze. Twee echte gesprekken van vier beurten geslaagd;
  bestaande gebruikersgesprekken en lichte repositorydefaults behouden.

- Groq met GPT-OSS 120B toegevoegd als derde provider, met streaming, veilige
  sleutels, webchatkeuze en auto-voorkeur Groq → Ollama. Echte Groq-proef geslaagd;
  geen nieuwe dependency of database-migratie. 99 automatische tests.

- Lokale Gemini-modelkeuze op verzoek bijgewerkt naar stabiele Gemini 4 Hydrogen;
  server herstart en echt getest. Google gaf ook hier tijdelijk 503-overbelasting.
  Echte auto-fallback naar inmiddels beschikbare Ollama qwen3:0.6b geslaagd.
  Geen wijziging van repositorydefaults, sleutels of applicatiecode.

- Fase 2 via PR #9 naar develop; 90 tests, echte browser-/herstartcontrole en
  live Gemini-proef (503-overbelasting, nog geen live antwoord). Google-foutarrays
  ondersteund, duidelijke overbelastingsmelding en veilige Windows-envkopieën.

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
