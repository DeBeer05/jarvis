# AI-engine — fase 2

De headless server 0.2.0 gebruikt één centrale `server/ai/router.py` voor tekst.
Alles is ontwikkeld op de desktop, op localhost:8765. Geen mini-pc-deployment.
De engine voert geen tools, shellcommando's, plugins of autonome acties uit.

## Hergebruik van Mark-LVII

`providers/llm_openai.py` bevatte al asynchrone OpenAI-compatibele streaming voor
Gemini en Ollama. Beide headless adapters gebruiken daadwerkelijk deze klasse.
Opt-in `strict_text` voegt begrensde output, streamvalidatie, typed fouten en
één exacte modelkeuze toe; bestaande desktopdefaults blijven behouden.
`core/gemini.py` heeft desktopconfig/Live/fallback, `engine_pipeline.py` audio en
tools, en dashboard/core-cloud starten aanvullende functies. Deze modules worden
niet door de headless server geïmporteerd. Bestaand desktopgeheugen wordt niet
gekopieerd: de afzonderlijke SQLite-chatopslag kent geen GUI of accountcontext.

## Starten en configureren

Gebruik de bestaande projectroot en Windows PowerShell 5.1:

```powershell
powershell.exe -NoProfile -File scripts/Start-Server.ps1 -Background
Start-Process http://127.0.0.1:8765/chat
```

De omgeving/dependencies zijn op deze desktop al voorbereid. Voor een nieuwe
ontwikkelomgeving: volg [HEADLESS_SERVER.md](HEADLESS_SERVER.md). Geen upstream
`setup.py` of volledige desktop-requirements nodig. `pwsh` is niet vereist.

Maak zo nodig een lokale `.env` op basis van `.env.example`; overschrijf een
bestaand bestand niet. Omgevingsvariabelen hebben voorrang. Nooit sleutels in
commando's, screenshots, Git of de chat plakken. De desktopconfig
`config/api_keys.json` wordt door deze server niet gelezen of gewijzigd.

Voor Gemini, pas uitsluitend de lokale `.env` aan:

```dotenv
JARVIS_HOST=127.0.0.1
JARVIS_PORT=8765
JARVIS_PROFILE=desktop-development
JARVIS_AI_PROVIDER=auto
JARVIS_AI_PREFERRED_PROVIDER=gemini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.8-flash
```

Vul `GEMINI_API_KEY` zelf lokaal in met een geldige eigen sleutel. Het actuele
stabiele Flash-model is bij implementatie tegen de officiële modeldocumentatie
gecontroleerd. De adapter gebruikt de officiële Gemini OpenAI-compatibele API:
`https://generativelanguage.googleapis.com/v1beta/openai/chat/completions`.
Een geconfigureerde sleutel betekent nog geen bevestigde toegang of quota.
Providerstatus doet geen betaalde proefaanroep; het eerste chatbericht test dit.

Voor Ollama, als je die zelf op deze desktop wilt gebruiken: installeer/start de
officiële lokale Ollama-server en download bewust een passend model. Er is in
deze fase geen Ollama of model geïnstalleerd. Daarna bijvoorbeeld:

```powershell
ollama pull qwen3:0.6b
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

```dotenv
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3:0.6b
JARVIS_AI_PROVIDER=ollama
```

Grotere modellen zijn op de desktop mogelijk: download zelf het gewenste model,
verander `OLLAMA_MODEL` en herstart JARVIS. De ingestelde modelnaam moet in
`/api/tags` voorkomen. Deze probe heeft een korte timeout en een cache van 15 s.
Uitsluitend een loopback-Ollama-origin zonder URL-credentials wordt toegestaan.
JARVIS gebruikt `/v1/chat/completions`, `stream`, `max_tokens` en
`reasoning_effort=none` voor Ollama; Gemini gebruikt `reasoning_effort=low`.

Contextgrootte, GPU-gebruik en resident modelgeheugen zijn Ollama-instellingen.
De OpenAI-compatibele chatroute configureert geen `num_ctx` of `keep_alive`.
Gebruik zo nodig een Ollama Modelfile met `PARAMETER num_ctx`; JARVIS-profielen
begrenzen alleen de eigen context/output/verzoeken en garanderen geen RAM-limiet
van een extern modelproces. De uiteindelijke 8-GB-machine is nog niet gemeten.

Na iedere configuratie- of Python-wijziging:

```powershell
powershell.exe -NoProfile -File scripts/Stop-Server.ps1
powershell.exe -NoProfile -File scripts/Start-Server.ps1 -Background
powershell.exe -NoProfile -File scripts/Get-ServerStatus.ps1
Invoke-RestMethod http://127.0.0.1:8765/api/v1/ai/providers
```

## Selectie, fallback en fouten

`auto` probeert de voorkeursprovider en maximaal één alternatief bij een
technische fout vóór de eerste zichtbare tekst. `gemini` en `ollama` gebruiken
uitsluitend die provider. Een veiligheidsweigering wordt niet omzeild. Zodra
tekst is ontvangen, geeft uitval `stream_interrupted`: gedeeltelijke tekst blijft
bewaard, zonder tweede antwoord van een andere provider. UI/SSE tonen fallback
en de werkelijk gebruikte provider/model. Mislukken beide vóór tekst, dan blijven
provider/model leeg: er is geen gegenereerd antwoord om toe te schrijven.

Fouten hebben vaste Nederlandse berichten: ontbrekende sleutel, onbereikbare
Ollama, ontbrekend model, authenticatie, quota, rate limit, tijdelijke modeloverbelasting (HTTP 503), timeout, ongeldige
stream, onderbroken antwoord en outputlimiet. Ruwe providerfouten/headers worden
niet naar de client of log gekopieerd. Annuleren sluit de lopende HTTP-stream;
bij afbreken/herstart wordt de beurt als cancelled/interrupted opgeslagen.

## Profielen en grenzen

| Configuratie | Desktopdefault | Mini-pc-default |
| --- | --- | --- |
| `JARVIS_PROFILE` | `desktop-development` | `mini-pc-production` |
| environment / loglevel zonder expliciete override | development / info | production / warning |
| `JARVIS_AI_MAX_CONCURRENT` | 2 | 1 |
| `JARVIS_AI_MAX_CONTEXT_CHARS` | 24000 | 12000 |
| `JARVIS_AI_MAX_OUTPUT_TOKENS` | 1024 | 512 |
| `JARVIS_AI_TIMEOUT_SECONDS` | 60 | 60 |
| `JARVIS_PROVIDER_TIMEOUT_SECONDS` | 25 | 25 |
| `JARVIS_CHAT_MAX_MESSAGE_CHARS` | 8000 | 8000 |
| `JARVIS_CHAT_MAX_RESPONSE_CHARS` | 16000 | 16000 |
| `JARVIS_CHAT_REQUESTS_PER_MINUTE` | 30 | 30 |
| `JARVIS_CHAT_MAX_CONVERSATIONS` | 100 | 100 |
| `JARVIS_CHAT_MAX_TURNS` | 100 | 100 |

Mini-pc-defaults gelden wanneer alleen het profiel wordt gekozen; expliciete
waarden uit een gekopieerde `.env` blijven overrides en worden gevalideerd.
Mini-pc accepteert maximaal één gelijktijdig antwoord, 16000 contexttekens en
1024 outputtokens. Dit profiel is alleen met tests gecontroleerd, niet uitgerold.
Voorkeur is Gemini; lokaal model standaard qwen3:0.6b. Geen model wordt bij start
opgewarmd en er is geen wachtrij met onbeperkt werk.

Context bevat de systeemprompt, het nieuwe bericht en maximaal 20 complete
succesvolle beurtparen, binnen het tekenbudget; geen mislukte deelantwoorden.
Een gesprek verwerkt één antwoord tegelijk. Verwijderen tijdens generatie wordt
geweigerd. De HTTP-body is begrensd op 65536 bytes vóór JSON-verwerking.

De Nederlandse persona staat in `config/jarvis-system-prompt.txt`.
`JARVIS_SYSTEM_PROMPT_FILE` kiest een ander lokaal UTF-8-bestand;
`JARVIS_SYSTEM_PROMPT` kan de tekst rechtstreeks overriden. Maximaal 12000 tekens,
zonder de inhoud in logs te dumpen. Herstart na aanpassen.

## Geheugen en veiligheid

SQLite staat standaard in `.local/data/jarvis.sqlite3`, met eventuele `-wal` en
`-shm`-bestanden ernaast. Relatieve configuratiepaden zijn vanaf de projectroot.
Schema 1 krijgt vóór de transactionele schema-2-migratie een unieke
`jarvis.sqlite3.pre-v2-*.bak`. Stop de server voordat je handmatig een volledige
databasekopie maakt; losse kopieën van alleen een actief WAL-databasebestand
kunnen onvolledig zijn. Back-ups bevatten chatinhoud en blijven lokaal.

Opgeslagen: gesprek/turn-ID's, UTC-tijdstippen, bericht, antwoord, werkelijke
provider/model, status en veilige foutcode. Configsleutels worden nooit als
metadata opgeslagen. De ingestelde Gemini-sleutel en herkenbare sleutelpatronen
worden vóór opslag/context geredigeerd. Dit is geen universele detectie van elk
mogelijk geheim: deel geen credentials of andere gevoelige tekst in chat.
Gesprekken zijn lokale plaintext; er is geen automatische bewaartermijn of
back-upverwijdering. De webchat kan gesprekken expliciet verwijderen.

Loopback, Host-/Origincontrole, geen CORS/proxytrust, CSP en plaintext-weergave
beperken lokale browseraanvallen. Modeltekst wordt nooit uitgevoerd of als HTML
ingevoegd. Dit is geen authenticatieontwerp voor andere computers of Android;
die toekomstige clients kunnen het API-contract hergebruiken nadat toegang apart
is ontworpen. Geen publieke binding/firewall/tunnel/service geactiveerd.

## Officiële bronnen

- [Gemini Flash-model](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash)
- [Gemini OpenAI-compatibiliteit](https://ai.google.dev/gemini-api/docs/openai)
- [Ollama OpenAI-compatibiliteit en context](https://docs.ollama.com/api/openai-compatibility)
- [Ollama modellenlijst](https://docs.ollama.com/api/tags)

Voor API-voorbeelden en exacte teststappen: [CHAT_API.md](CHAT_API.md).
Werkelijk uitgevoerde controles: [PHASE_2_TEST_REPORT.md](PHASE_2_TEST_REPORT.md).
STOP na fase 2.
