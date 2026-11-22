# Projectstructuur

## Bestaande Mark-LVII-code — behouden

| Pad | Bestaande rol |
| --- | --- |
| `main.py`, `ui.py` | App-entrypoint en bestaande Qt-interface |
| `core/` | AI, audio, taken, routines en ondersteunende logica |
| `actions/`, `plugins/` | Acties en uitbreidingspunten |
| `agents/` | Bestaande runtime-agentdefinities, geen Codex-subagents |
| `gui/` | Bestaande Windows/cross-platform desktopinterface; hergebruiken |
| `dashboard/` | Bestaand webdashboard/server; eerst onderzoeken voor hergebruik |
| `providers/` | AI-providerabstracties; llm_openai hergebruikt met opt-in strikte tekstmodus |
| `memory/` | Geheugenbeheer; lokale gebruikersdata blijven buiten Git |
| `config/` | Bestaande configuratiemodule en icoon; hergebruikt |
| `requirements.txt`, `setup.py` | Bestaande dependency-/installatieconfig; niet uitgevoerd |

## Aanvullende structuur — fase 3

| Pad | Huidige rol of gereserveerde bestemming |
| --- | --- |
| `server/` | Geïsoleerde headless serverbasis: config, AI-router/adapters, chat-API/SSE, webchat, SQLite, logging, procesbeheer |
| `server/security/` | Argon2id, default-deny gate, tokens/sessies, apparaten/pairing, audit en schema 3 |
| `server/static/` | Webchat plus login- en beveiligingspagina; geen frontendbuild of tokenstorage |
| `desktop-client/` | Gereserveerd voor packaging/clientgrens; `gui/` blijft bestaande UI |
| `android-app/` | Toekomstige mobiele app |
| `integrations/` | Toekomstige adapters, geen actieve koppelingen |
| `tests/` | Pytest voor serverbasis, AI-adapters/router, chat/API/SQLite/security; upstreamchecks blijven op hun oorspronkelijke plaats |
| `scripts/` | Git-/repositoryhelpers en Windows-omgeving/start/status/stop |
| `infrastructure/` | Gereserveerd; geen productieconfiguratie |
| `docs/` | CI-plan, AI-/API-handleidingen, testverslagen, screenshots en bron-/licentieverantwoording |
| `.github/workflows/` | Repositorycheck en geïsoleerde servertests op Windows/Linux |

De nog lege gereserveerde mappen bevatten `.gitkeep`. Buiten server/tests/scripts
betekent aanwezigheid geen geïmplementeerde component of besluit tot duplicatie.
Geen bestanden verplaatst en geen tweede `jarvis/`-root gemaakt.

Rootdocumenten: bestaande `readme.md` (op Windows geen tweede `README.md` maken),
`DEVELOPMENT_PROGRESS.md`, `GIT_WORKFLOW.md`, `SETUP_CHECKLIST.md`,
`ARCHITECTURE_PLAN.md`, `AGENTS.md` en `CHANGELOG.md`.
