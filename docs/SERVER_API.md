# Server-API — versie 0.3.0

Basis: `http://127.0.0.1:8765`. Alleen lokaal; geen commandobesturing.
FastAPI-factory in `server/app.py`, basisrouters in `server/api/routes.py`.
Fase 2 voegt `server/api/chat.py` toe: [Chat-API](CHAT_API.md).
Fase 3: alle persoonlijke routes vereisen een geldige sessie en expliciete rechten.
Zie [AUTHENTICATION.md](AUTHENTICATION.md) en [DEVICE_PAIRING.md](DEVICE_PAIRING.md).
Health/ready blijven publiek; statische pagina's bevatten geen privégegevens.

## GET /health

Liveness van het proces: HTTP 200, onafhankelijk van AI/database-readiness.

```json
{"status":"ok","service":"jarvis-server"}
```

## GET /ready

HTTP 200 wanneer lifespan actief is en een korte read-only SQLite-query de
verwachte schemaversie en migratierecord bevestigt:

```json
{"status":"ready","service":"jarvis-server"}
```

Anders HTTP 503 met `status: "not_ready"`. Providerbeschikbaarheid is geen
startup-/readinessvoorwaarde in deze fase.

## GET /api/v1/status

Alleen een echte loopbackclient met authenticatie en status:read; zonder sessie
HTTP 401, zonder recht HTTP 403. Een extern clientadres krijgt HTTP 403.
Proxyheaders maken een client niet lokaal. HTTP 200, voorbeeld:

```json
{
  "status":"running",
  "service":"jarvis-server",
  "version":"0.3.0",
  "instance_id":"example-instance-id",
  "uptime_seconds":12.5,
  "environment":"development",
  "components":{"api":true,"database":true,"ai":true},
  "ai_providers":{
    "selected":"auto",
    "gemini":{"configured":false,"available":false},
    "groq":{"configured":false,"available":false},
    "ollama":{"configured":true,"available":null}
  }
}
```

De instance-ID identificeert het proces maar verleent geen rechten. Bij database-
uitval is status `degraded` en `components.database` false. `configured` is alleen
een lokale configuratie-indicator. Gemini/Groq available is null bij een ingestelde
sleutel (ongetest), false wanneer ontbrekend. Ollama available is null vóór een
providerprobe en daarna de gecachte modelbereikbaarheid. De statusroute doet zelf
geen providerverzoek. Geen paden, credentials, tokenwaarden of modelcalls.

## Overige routes en fouten

- `/openapi.json`: alleen development met eigenaarrechten; geen Swagger-/ReDoc-GUI.
- `GET /internal/status`: voor lokale controlscripts met het aparte
  procescontroletoken; dit is niet de persoonlijke statusroute. Gebruik het statusscript.
- `POST /internal/shutdown`: alleen voor lokale controlscripts, niet opgenomen
  in OpenAPI. Vereist een per proces gegenereerd Bearer-controletoken én loopback;
  antwoord 202 bij acceptatie, 401 zonder correct token. Geen publiek beheerendpoint.
  Gebruik het stopscript in plaats van zelf tokens uit bestanden te kopiëren.
- Onbekende route: eerst authenticatie en eigenaarrechten, daarna 404.
  Ongeldige invoer: generieke 422 zonder teruggekaatste input.
- Onverwachte fout: 500 `{"detail":"Internal server error"}`; fouttype in JSON-log,
  geen exceptionbericht met mogelijke geheimen.
- Ongeldige Host-header: 400. Geen CORS, proxytrust of publieke binding ingeschakeld.
