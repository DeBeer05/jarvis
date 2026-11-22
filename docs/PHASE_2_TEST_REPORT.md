# Fase 2 — testverslag

Datum: 22 november 2026, Europe/Amsterdam. Windows-ontwikkeldesktop, Python
3.12.10, profiel desktop-development, localhost:8765. Geen mini-pc of deployment.

## Resultaat en acceptatiegrens

De AI-engine, API, SQLite-migratie en webchat zijn geïmplementeerd. **90 tests
geslaagd** (laatste implementatierun 4,58 s); oorspronkelijke 39 fase-1-tests
inbegrepen en bijgewerkt voor versie 0.2/schema 2. Eén bekende niet-blokkerende
Starlette/httpx-testadapter-deprecatiewaarschuwing. De structuurcheck is aanvullend,
geen vervanging voor applicatietests.

**Tijdens de oorspronkelijke fase-2-controle was nog geen succesvol live
Gemini- of Ollama-antwoord gegenereerd.** De latere modelupdate hieronder heeft
inmiddels een echte succesvolle Ollama/fallbackproef toegevoegd.
Aanvankelijk ontbraken beide providers. De eigenaar heeft tijdens het werk zelf
lokaal een Gemini-sleutel ingesteld. Daarna is Gemini echt aangeroepen via de
chat-SSE-route. Google retourneerde HTTP 503 / UNAVAILABLE met een melding over
hoge vraag naar dit model; een latere herhaling gaf dezelfde uitkomst. Geen
tekst ontvangen. De sleutel is niet getoond of gecommit. De generieke fout is
verbeterd naar een vaste Nederlandse melding voor tijdelijke overbelasting.
Een aanvullende directe REST-diagnose bevestigde de HTTP-status; geen ruwe
providerdiagnose opgeslagen. Het echte arrayformaat van Google's foutresponse
is verwerkt en met extra regressietests gecontroleerd (quota/overbelasting).

Tijdens die oorspronkelijke controle was Ollama op 127.0.0.1:11434 afwezig. Geen model,
provideraccount, GPU-package of Ollama geïnstalleerd. Toen bleef live antwoordacceptatie
open door Gemini-overbelasting en ontbrekende lokale fallback. Herhaal
later de stappen uit [CHAT_API.md](CHAT_API.md), of configureer bewust Ollama.
Er wordt geen live succes geclaimd op basis van mocks.

## Automatische tests met mocks en tijdelijke SQLite

| Gebied | Werkelijk gecontroleerd |
| --- | --- |
| Gemini/Ollama-adapters | Gedeeld echt transport via HTTPX MockTransport; officiële URL, headers, model/body, streamingframes; geen externe netwerkcalls |
| Detectie | Ollama tags/bereikbaarheid, cache, ontbrekend model; Gemini sleutel ontbreekt zonder desktopconfig te lezen |
| Selectie/fallback | auto/expliciet, technische fout vóór tekst, geen tweede antwoord na deeltekst, werkelijke provider/model |
| Fouten | Authenticatie, quota versus rate limit (ook JSON-array), 503-overbelasting, netwerk-/provider-/totale timeout, ongeldige/onvolledige stream, contentfilter |
| Streams/cleanup | Meta/delta/done, annuleren vóór/tijdens generatie, disconnect, verlopen reservering, gesloten providerverbinding |
| Deadline na eerste tekst | Echte HTTPX AsyncByteStream met gesimuleerde stalling: gedeeltelijke tekst behouden, stream gesloten, geen fallback, slot vrij |
| API/veiligheid | JSON/SSE, UUID/invoervalidatie, grote body, externe Origin/client, concurrency/rate-/context-/opslaglimieten, dubbele verzoeken |
| Geheugen | CRUD, heropenen na app-lifespanherstart, cascade delete, geen verwijderen tijdens lopende generatie, geredigeerde sleutelcanaries |
| Migratie | Bestaande schema-1-data behouden, unieke pre-v2-back-up, schema 2, onderbroken beurt herkend bij herstart |
| Profielen/persona | Desktopdefault, mini-pc-grenzen/productiondefaults, ongeldige configuratie geweigerd |
| Webchat | Statische assets, CSP, geen model-HTML/scriptuitvoering, API-contract |
| Fase 1 | Health/ready/status, logging, configuratie, lifecycle/controle, geen GUI/audio/heavy imports |

Tests staan in `tests/test_ai_providers.py`, `tests/test_ai_chat.py` en de
bestaande servertests. Tijdelijke testdatabases bevatten alleen synthetische tekst.

## Echte lokale server en browser

- Voor de wijziging: server 0.1 daadwerkelijk gestart, health/ready/status,
  SQLite/logbestand en alle 39 bestaande tests gecontroleerd; daarna gestopt.
- Server 0.2 daadwerkelijk gestart op 8765; bestaande eindpunten werken.
  Echte lokale database gemigreerd naar schema 2 met pre-v2-back-up.
- Webchat echt in de browser geopend: providerkeuze, verzenden, ontbrekende
  sleutelmelding, nieuw gesprek, historie heropenen en verwijderen gecontroleerd.
  Geen JavaScript-consolefouten waargenomen.
- Responsieve 390x844-weergave visueel en met pagina-afmetingen gecontroleerd;
  overbodige buitenste scrollbar verholpen. Screenshots van echte lokale UI:
  [desktop](images/chat-desktop.jpg) en [mobiel](images/chat-mobile.jpg).
- Synthetisch chatverzoek via echte HTTP gaf de verwachte missing-key-fout en
  werd opgeslagen. Eigen proces met de Windows-scripts gestopt/herstart;
  hetzelfde gesprek inclusief bericht/foutstatus daarna uit SQLite opgehaald en
  in de browser heropend. Alleen het bekende eigen testgesprek verwijderd.
- Een succesvol mockantwoord is apart na een app-herstart teruggelezen.
  De echte procesherstart bewijst opslag van de echte foutbeurt; dit wordt niet
  voorgesteld als live modelgeneratie.

## Herhaalbare lokale controles

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
node --check server/static/chat.js
python scripts/check_repository.py
git diff --check
```

Node is alleen een optionele ontwikkel-/CI-syntaxcheck; de server en webchat
vereisen geen Node, npm of frontendbuild. Git-/CI-verificatie en de uiteindelijke
mergegegevens worden vastgelegd in [DEVELOPMENT_PROGRESS.md](../DEVELOPMENT_PROGRESS.md).
De verplichte CI voert dezelfde tests op Windows/Linux uit en controleert op
Windows de controlscripts onder zowel Windows PowerShell 5.1 als PowerShell 7.
Geen CI-secret of echte provider nodig.

Geheimcontrole: repository/index-patrooncontrole en Gitleaks op de nieuwe commits.
De bekende oude upstream-TLS-sleutel blijft uitsluitend in de behouden historie;
niet gebruikt of opnieuw toegevoegd. Geen chatdatabase/.env/runtime-token in Git.

## Nog handmatig te valideren

Gemini is inmiddels lokaal geconfigureerd maar tijdelijk overbelast. Probeer
later opnieuw, of configureer zelf een lokaal Ollama-model; herstart en test
antwoord/streaming/Stop/context volgens CHAT_API.md. Test auto-fallback met twee
bruikbare providers. Providerkwaliteit, echte quota, netwerkvertraging, langdurige
belasting en model-RAM/GPU-gebruik zijn hier niet live gemeten. Het mini-pc-profiel
is geen bewijs dat elk gekozen model binnen 8 GB past.

## Aanvullende modelupdate na de eerste fase-2-oplevering

Op 22 november is op verzoek lokaal gemini-4-hydrogen ingesteld. Officiële
Google-documentatie en de echte modelcatalogus voor de ingestelde sleutel
bevestigen dit stabiele model. Server herstart en modelstatus gecontroleerd.
Een expliciete Gemini-SSE-proef gaf wederom modeloverbelasting, zonder tekst.

Ollama qwen3:0.6b was inmiddels door de eigenaar beschikbaar gemaakt. Echte
HTTP/SSE-proef met auto leverde technische Gemini-fout vóór tekst, fallback naar
Ollama en een succesvol antwoord op: vijf delta-events, completed en 17 tekens.
Het opgeslagen antwoord is via de historie teruggelezen; daarna uitsluitend
het bekende synthetische testgesprek verwijderd. Geen mocks voor deze proef.
38 relevante configuratie-/adaptertests slagen; geen applicatiecode gewijzigd.

Fase 2 is technisch geïmplementeerd en live Ollama/fallback werkt. Een succesvol
live Gemini-antwoord blijft nog open wegens providerfouten.
STOP na fase 2. Geen clientapps, spraak, agenda/berichten, bellen of automatisering.
