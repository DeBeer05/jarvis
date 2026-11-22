# Headless Windows-server — fase 2

De lokale JARVIS-serverbasis draait zelfstandig zonder GUI, audioapparaten, GPU,
AI-provider, Ollama of externe database. Versie 0.2.0 gebruikt FastAPI/Uvicorn,
httpx, standaardbibliotheek-SQLite en één worker. Chat is optioneel beschikbaar
op `/chat`; providerconfiguratie en grenzen staan in [AI_ENGINE.md](AI_ENGINE.md).
De bestaande Mark-LVII-desktopapp en cloudhost blijven ongewijzigd.

## Installeren op Windows

Open PowerShell in de bestaande projectroot op branch `develop` (fase 2 staat
bewust nog niet op main). Gebruik Python 3.12; deze werkplek
heeft Python 3.12.10 en een geteste `.venv`. Op een andere Windows-machine met
winget kan Python per gebruiker worden voorbereid:

```powershell
winget install --id Python.Python.3.12 --exact --scope user
```

Daarna, of om de bestaande omgeving veilig opnieuw te gebruiken:

```powershell
powershell.exe -NoProfile -File scripts/Initialize-ServerEnvironment.ps1
powershell.exe -NoProfile -File scripts/Install-ServerDependencies.ps1 -IncludeTests
```

Laat `-IncludeTests` weg voor uitsluitend runtimepackages. De versieconstraints
in `constraints-server.txt` leggen de geteste versies vast; constraints installeren
zelf geen extra packages. Voer **niet** upstream `setup.py` of de volledige
`requirements.txt` uit voor deze server: die installeren GUI, audio en browsertools.
Windows PowerShell 5.1 is voldoende; `powershell.exe` is standaard in Windows
aanwezig. `pwsh` is het aparte PowerShell-7-programma en is niet nodig. De eerdere
instructies veronderstelden ten onrechte dat dit overal beschikbaar was.
Venv-activatie en blijvende aanpassing van de PowerShell execution policy zijn
niet nodig. Als een lokale policy scripts blokkeert, gebruik dan rechtstreeks de
Python-commando's hieronder; verander niet automatisch het organisatiebeleid.

## Start, status, stop

```powershell
# Voorgrond; Ctrl+C sluit correct af.
powershell.exe -NoProfile -File scripts/Start-Server.ps1
# Rechtstreeks hetzelfde entrypoint:
.\.venv\Scripts\python.exe -m server
```

Gebruik slechts één startvariant tegelijk. Voor een verborgen achtergrondproces,
zonder permanente service of automatische systeemstart:

```powershell
powershell.exe -NoProfile -File scripts/Start-Server.ps1 -Background
powershell.exe -NoProfile -File scripts/Get-ServerStatus.ps1
powershell.exe -NoProfile -File scripts/Stop-Server.ps1
```

Rechtstreekse alternatieven: `.\.venv\Scripts\python.exe -m server status` en
`.\.venv\Scripts\python.exe -m server stop`. Status heeft exitcode 1 wanneer geen
passende server draait. Stop forceert geen PID-kill. Het controleert een lokale
instance-ID en gebruikt een per start gegenereerd controletoken voor een lokale
shutdownaanvraag. Uvicorn beëindigt vervolgens de lifespan, sluit SQLite af en
flusht/sluit logs. De lock is ook na een crash door het OS vrijgegeven; een geldig
oud runtimebestand mag bij de volgende start vervangen worden. Onbekende bestanden
worden geweigerd. Bij een bezette poort wordt geen ander proces gestopt.

## API testen

```powershell
Invoke-RestMethod http://127.0.0.1:8765/health
Invoke-RestMethod http://127.0.0.1:8765/ready
Invoke-RestMethod http://127.0.0.1:8765/api/v1/status
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
python scripts/check_repository.py
```

Deze werkplek is ook met de vijf PowerShell-scripts en echte HTTP-verzoeken getest;
daarna is het testproces gestopt. Tests gebruiken tijdelijke databases en geen
echte persoonsgegevens. [SERVER_API.md](SERVER_API.md) beschrijft de responses.
CI test Python 3.12 op Windows en Linux en voert op Windows de controlscripts uit
onder zowel ingebouwde Windows PowerShell 5.1 als PowerShell 7.

## Configuratie

Een ontbrekende `.env` is toegestaan: veilige defaults volstaan. Kopieer alleen
wanneer `.env` nog niet bestaat: `Copy-Item .env.example .env`. Omgevingsvariabelen
hebben voorrang boven `.env`; daarna gelden defaults. Relatieve paden zijn altijd
relatief aan de projectroot, niet aan de huidige shellmap. Interpolatie van
`${VAR}` in .env is uitgeschakeld. Ongeldige syntax/waarden stoppen de server met
een veilige foutmelding; de oorspronkelijke waarde wordt niet gelogd.

| Variabele | Default / betekenis |
| --- | --- |
| `JARVIS_ENV` | `development` of `production`; beide blijven lokaal |
| `JARVIS_HOST` | `127.0.0.1`; andere waarden zijn verboden |
| `JARVIS_PORT` | `8765`, bereik 1–65535 |
| `JARVIS_LOG_LEVEL` | `info`; debug/info/warning/error/critical |
| `JARVIS_LOG_PATH` | `.local/logs/server.log` |
| `JARVIS_LOG_MAX_BYTES` | `1048576` (1 MiB); minimaal 1024, maximaal 100 MiB |
| `JARVIS_LOG_BACKUP_COUNT` | `3`; bereik 1–10 |
| `JARVIS_DATABASE_PATH` | `.local/data/jarvis.sqlite3`; lokaal bestand, geen netwerk-URL/UNC |
| `JARVIS_RUNTIME_DIR` | `.local/run`; eigen directory voor proceslock en controletoken |
| `JARVIS_AI_PROVIDER` | `auto`; auto/gemini/ollama, zie AI_ENGINE.md |
| `GEMINI_API_KEY` | leeg; lokale sleutel voor de officiële Gemini-API, alleen op chatverzoek |
| `JARVIS_ENABLE_EXTERNAL_ACCESS` | uitsluitend `false` in deze fase |
| `JARVIS_ENABLE_AUTOMATIONS` | uitsluitend `false` in deze fase |
| `JARVIS_PHASE` | documentair fasekenmerk in het voorbeeld, geen runtimefeatureflag |

Een configuratiewijziging wordt bij herstart gelezen. Behoud dezelfde runtime-
directory voor status/stop terwijl een server draait. Bewaar die directory lokaal
en afgeschermd voor andere gebruikers. `.local/`, .env, databases en logfiles zijn
uitgesloten van Git. Runtime/controlinformatie mag nooit in een issue of commit.
De oude desktopconfig `config/api_keys.json` wordt niet gelezen of aangepast.

## Database, logging en veiligheid

SQLite gebruikt schema 2 met schema_migrations, chat_conversations en chat_turns.
Schema 1 krijgt eerst een unieke pre-v2-back-up. Migraties zijn transactioneel/herhaalbaar; een nieuwer
schema wordt geweigerd. Verbindingen zijn kort, met timeout, en worden ook bij
fouten gesloten. Readiness gebruikt een read-only controle en creëert een
verdwenen database niet opnieuw. Chatgeheugen is lokaal; geen contacten-/integratiegeheugen.

JSON-logs bevatten tijd, level, vaste events en veilige fouttypen; geen request-
bodies, querystrings, headers, configdump of rauwe exceptiontekst. Bekende
configgeheimen en gangbare `password`/`token`-toewijzingen worden geredigeerd.
Default maximaal één actief logbestand en drie backups van circa 1 MiB elk;
rotatie heeft bestands-/recordoverhead. Per-request accesslogging staat uit.

De API bindt alleen aan loopback, controleert statusclients op een echt loopback-
adres en negeert proxyheaders. Hostheaders zijn begrensd ter bescherming tegen
DNS-rebinding. Status heeft in deze lokale fase geen gebruikerstoegangstoken;
het stopendpoint vereist wel het private controletoken. Dit is geen beveiligings-
ontwerp voor publicatie op internet. Geen firewallregel, certificaat, tunnel,
Windows-service of deployment is geïnstalleerd.

## Historische fase-1-nulmeting op deze Windows-werkplek

22 november 2026, ontwikkeldesktop met 31,95 GiB fysiek RAM, Python 3.12.10,
localhost, één worker, zonder AI:

| Meting | Resultaat |
| --- | --- |
| Totale achtergrondstart via PowerShell-script tot gereedmelding | 1141 ms |
| Processtart tot waargenomen gereedmelding | 844,2 ms |
| Working set na gereedmelding / idleproef | 46,90 MiB |
| Private memory | 34,70 MiB |
| Idle-CPU over 3,013 seconden, schaal één kern | 0,000% gemeten |

Dit is een korte lokale momentopname met proces-/PowerShell-overhead, geen
garantie voor de uiteindelijke 8-GB-mini-pc of langdurige belasting. Nul gemeten
CPU betekent onder de meetresolutie in dat interval, niet nul verbruik voor altijd.

## Onderzoek van Mark-LVII en hergebruik

| Bestaand onderdeel | Bevinding / besluit voor fase 1 |
| --- | --- |
| `main.py` / `ui.py` / `gui/` | Main maakt JarvisUI, GUI-thread en audio/AI-loop; niet importeren |
| `dashboard/server.py` | FastAPI-netwerkdashboard met uploads, pairing, acties en binding op 0.0.0.0; niet starten |
| `core/cloud.py` | Bestaande headless cloudhost met ThreadingHTTPServer, Telegram, brain, taken/routines en Linux-deploy; run bindt 0.0.0.0; buiten deze fase |
| `core/gemini.py`, `providers/` | Fase 2 hergebruikt providers.llm_openai; core.gemini blijft desktopgebonden |
| `memory/config_manager.py` | Desktop-JSON-config/credentials met locks; blijft uitsluitend voor desktop |
| `memory/memory_manager.py` | Persoonlijk JSON-geheugen; niet nodig voor de nieuwe databasebasis |
| `core/plugin_loader.py` / acties | Discovery wordt door JarvisLive gestart; plugins kunnen acties activeren; nu niet initialiseren |
| `core/tasks/`, `core/routines/` | Bestaande workers/schedulers hebben AI-/actiecontext; geen achtergrondtaken starten |
| Bestaande logging | Veel print/traceback; aparte begrensde serverlogger voorkomt GUI/configkoppeling |

De bestaande code en auteurs-/licentiegegevens blijven behouden. De nieuwe module
hergebruikt de repository en de bestaande FastAPI/Uvicorn-technologie, maar start
bewust geen bestaande entrypoint met ongewenste neveneffecten. Oorspronkelijke
Python-bestanden zijn byte-inhoudelijk (na CRLF-normalisatie) en statisch op syntax
gecontroleerd; bestaande desktopfunctionaliteit is niet interactief getest.

## Grenzen en bekende punten

Fase 2 bevat AI-router/chat en Gemini/Ollama-adapters. Geen spraak, clients, agenda/Gmail,
berichten, bellen, automatiseringen of productie-service. De bekende oude
upstream-TLS-sleutel blijft in de behouden Git-geschiedenis en wordt nooit gebruikt.
De geteste Starlette/httpx-testadapter meldt één deprecatiewaarschuwing; alle tests
slagen en geteste versies zijn vastgelegd. Een latere dependency-update kan die
adapter vervangen; voor deze fase is geen runtimefout waargenomen.

Bronnen voor gebruikte mechanismen:
[FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/),
[Python SQLite](https://docs.python.org/3.12/library/sqlite3.html),
[python-dotenv](https://bbc2.github.io/python-dotenv/).
Zie [PHASE_2_TEST_REPORT.md](PHASE_2_TEST_REPORT.md) voor actuele controles.
**STOP na fase 2.**
