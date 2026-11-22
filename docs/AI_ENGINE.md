# AI-engine — fase 2, beveiligd in fase 3

De headless server 0.3.0 gebruikt één centrale `server/ai/router.py` voor tekst.
Fase 3 beveiligt de bestaande chat: log eerst in via `/login` of koppel een
client volgens [AUTHENTICATION.md](AUTHENTICATION.md) en
[DEVICE_PAIRING.md](DEVICE_PAIRING.md). De providerconfiguratie blijft behouden.
Alles is ontwikkeld op de desktop, op localhost:8765. Geen mini-pc-deployment.
De engine voert geen tools, shellcommando's, plugins of autonome acties uit.

## Hergebruik van Mark-LVII

`providers/llm_openai.py` bevatte al asynchrone OpenAI-compatibele streaming voor
Gemini, Groq en Ollama. De headless adapters gebruiken daadwerkelijk deze klasse.
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
`reasoning_effort=none` voor Ollama (niet door elke model/servercombinatie afgedwongen); Gemini gebruikt `reasoning_effort=low`.

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

## Groq: gratis cloudoptie naast Gemini en Ollama

Groq ondersteunt een Free Plan met gebruikslimieten. Standaardmodel voor JARVIS:
`openai/gpt-oss-120b`. De officiële limietpagina vermeldt bij implementatie
30 requests/minuut, 1000/dag en 8000 tokens/minuut; controleer de exacte limieten
van je eigen organisatie in de Groq Console. Geen onbeperkt gratis gebruik.
Gebruik het Free Plan; JARVIS wijzigt geen abonnement en koopt geen credits.
Een betaald account kan voor hetzelfde model wel kosten rekenen.

Maak zelf een sleutel via https://console.groq.com/keys en zet die alleen lokaal:

```dotenv
GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-120b
JARVIS_AI_PROVIDER=auto
JARVIS_AI_PREFERRED_PROVIDER=groq
```

Vul de lege sleutelregel zelf lokaal in. Herstart met de Windows-scripts en
herlaad `/chat`. Kies Groq voor uitsluitend die cloudprovider. Auto met voorkeur
Groq probeert Groq en vervolgens Ollama; Gemini wordt dan niet aangeroepen.
Auto met voorkeur Gemini behoudt Gemini → Ollama, en voorkeur Ollama behoudt
Ollama → Gemini. Geen cloudprovider wordt heimelijk als derde poging toegevoegd.

De adapter hergebruikt hetzelfde Mark-LVII-streamingtransport op de officiële
`https://api.groq.com/openai/v1`-origin. GPT-OSS gebruikt low reasoning,
include_reasoning=false en max_completion_tokens. Geen tools/code/search
geactiveerd. Groq-status betekent sleutel ingesteld, geen betaalde proefcall.
Sleutels van beide cloudproviders worden in opslag/context/logs geredigeerd;
herkenbare gsk_-sleutels worden aanvullend gemaskeerd. De Groq-toevoeging vereiste
geen eigen migratie; fase 3 gebruikt inmiddels schema 3 voor authenticatie.

Op deze desktop is een echte expliciete Groq-SSE-proef geslaagd: vier tekstframes,
completed en precies 'Groq werkt.'; provider/model en opgeslagen antwoord
gecontroleerd. Alleen het eigen synthetische testgesprek verwijderd.

Officiële bronnen: [modellen](https://console.groq.com/docs/models),
[Free Plan-limieten](https://console.groq.com/docs/rate-limits),
[OpenAI-compatibiliteit](https://console.groq.com/docs/openai) en
[API/reasoning](https://console.groq.com/docs/api-reference).

## Nieuwere lokale modelkeuze: Gemini 4 Hydrogen

Op verzoek is op deze desktop `GEMINI_MODEL=gemini-4-hydrogen` in de lokale .env
gezet en is de server herstart. Dit is een stabiel Gemini-4-model uit november
2026 voor snelle dagelijkse taken. De officiële API-modelcatalogus bevestigt de
modelnaam voor de ingestelde sleutel. De bestaande OpenAI-compatibele route met
reasoning_effort=low ondersteunt dit model zonder package-update.

De versievaste repositorydefaults/voorbeelden hierboven blijven gemini-3.8-flash;
voor Hydrogen kun je uitsluitend de lokale modelregel aanpassen. Beide gebruiken
hetzelfde transport. De echte Hydrogen-streamingproef kreeg HTTP 503 wegens
modeloverbelasting, dus een succesvol live antwoord is nog niet bevestigd.
Herlaad /chat om de nieuwe modelnaam te zien en probeer later opnieuw.
Ollama qwen3:0.6b is inmiddels lokaal beschikbaar. Een echte auto-proef schakelde
na een Gemini-fout over naar Ollama en eindigde met een volledig gestreamd,
opgeslagen antwoord. Auto werkt daarmee lokaal, ook als Gemini niet antwoordt.

Bronnen: [Gemini 4 Hydrogen](https://aistudio.google.com/docs/models/gemini-4-hydrogen)
en [OpenAI-compatibiliteit](https://aistudio.google.com/docs/openai).

## Selectie, fallback en fouten

`auto` probeert de voorkeursprovider en maximaal één alternatief bij een
technische fout vóór de eerste zichtbare tekst. `gemini`, `groq` en `ollama` gebruiken
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

## Herhalende antwoorden van het lokale minimodel

De screenshotmelding met steeds dezelfde begroeting is onderzocht. De engine
stuurt het nieuwste gebruikersbericht correct door, ook na identieke eerdere
modelantwoorden (regressietest). Qwen3 0.6B gaf in echte proeven echter zwakke
Nederlandse antwoorden en vraagecho. Extra persona-instructies hielpen niet
betrouwbaar en zijn niet opgeslagen. Een proef met Qwen3 4B gaf hier denk-tekst
in content en een timeout; die variant is niet de actieve lokale keuze geworden.

Op deze desktop is daarom `OLLAMA_MODEL=qwen2.5:3b` ingesteld. De officiële
instructievariant is via de bestaande lokale Ollama gedownload (circa 1,9 GB).
Alle Ollama-tekstaanroepen gebruiken nu temperature=0.2, zodat kleine lokale
modellen minder willekeurig antwoorden. Groq/Gemini behouden hun eigen defaults.
De lichte repository-/mini-pc-defaults zijn niet veranderd; niets is uitgerold
naar de mini-pc. De onderzochte Qwen3 4B blijft als niet-actief model geïnstalleerd.

Echte HTTP-tests: twee afzonderlijke gesprekken met ieder hallo, hoe heet je,
met je praten en twee plus drie. Alle acht beurten completed, verschillende
passende antwoorden, JARVIS als naam en vijf als rekenantwoord; opslag bevestigd.
Dit is een gerichte regressieproef, geen garantie voor alle modelantwoorden.
Begin in de webchat een nieuw gesprek en kies Ollama; oude herhalingen blijven
als bewaarde geschiedenis bestaan. Voor betere cloudkwaliteit kun je Groq kiezen.

Bron: [Qwen2.5 3B](https://ollama.com/library/qwen2.5:3b).

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
Schema 1/2 krijgt vóór de transactionele schema-3-migratie een unieke
`jarvis.sqlite3.pre-v3-*.bak`. Stop de server voordat je handmatig een volledige
databasekopie maakt; losse kopieën van alleen een actief WAL-databasebestand
kunnen onvolledig zijn. Back-ups bevatten chatinhoud en blijven lokaal.

Opgeslagen: gesprek/turn-ID's, UTC-tijdstippen, bericht, antwoord, werkelijke
provider/model, status en veilige foutcode. Configsleutels worden nooit als
metadata opgeslagen. De ingestelde Gemini-/Groq-sleutels en herkenbare sleutelpatronen
worden vóór opslag/context geredigeerd. Dit is geen universele detectie van elk
mogelijk geheim: deel geen credentials of andere gevoelige tekst in chat.
Gesprekken zijn lokale plaintext; er is geen automatische bewaartermijn of
back-upverwijdering. De webchat kan gesprekken expliciet verwijderen.

Loopback, Host-/Origincontrole, geen CORS/proxytrust, CSP en plaintext-weergave
beperken lokale browseraanvallen. Modeltekst wordt nooit uitgevoerd of als HTML
ingevoegd. Fase 3 voegt eigenaarlogin, sessies, minimale apparaatrechten en veilige
pairing toe; zie [SECURITY.md](SECURITY.md). Toegang vanaf andere computers en
clientapps blijven een latere opdracht. Geen publieke binding/firewall/tunnel/service geactiveerd.

## Officiële bronnen

- [Gemini Flash-model](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash)
- [Gemini OpenAI-compatibiliteit](https://ai.google.dev/gemini-api/docs/openai)
- [Ollama OpenAI-compatibiliteit en context](https://docs.ollama.com/api/openai-compatibility)
- [Ollama modellenlijst](https://docs.ollama.com/api/tags)

Voor API-voorbeelden en exacte teststappen: [CHAT_API.md](CHAT_API.md).
AI-controles: [PHASE_2_TEST_REPORT.md](PHASE_2_TEST_REPORT.md).
Actuele beveiliging/regressies: [PHASE_3_TEST_REPORT.md](PHASE_3_TEST_REPORT.md).
STOP na fase 3.
