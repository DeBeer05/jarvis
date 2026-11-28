# Gemeten hybride prestaties — 28 november 2026

Alle account-/agendaresultaten in deze metingen zijn synthetisch. De Oracle- en
HTTPS-metingen gebruikten wel de echte bestaande VM en verbinding. Geen microfoon
of persoonlijke database gebruikt; geen luisteracceptatie of mini-pc-meting.

## Gespreksroutering

Drie synthetische geauthenticeerde HTTP-proeven met dezelfde mocks:

- Vooraf: bevestiging mediaan 5545.9 ms; weer 103.5 ms.
- Na router-/approvalwijziging (laatste drie proeven): bevestiging mediaan 294.1 ms; weer 142.2 ms.

Vooraf ging de weervraag ten onrechte naar het model (één call, nul broncalls).
Daarna: nul modelcalls, één echte bronadapteraanroep per proef. De twee weertijden
zijn daardoor geen snelheidsvergelijking van dezelfde functie. Een bevestiging
wacht nu direct op de bestaande executor en het API-resultaat, in plaats van eerst
vijf seconden op een niet-actieve achtergrondtick te wachten.

## Echte Oracle-benchmarks

Ubuntu ARM64, 2 CPU, 12 GB RAM; Ollama v0.40.19; één geladen model/aanvraag,
2048 context, maximaal 96 antwoordtokens, temperatuur 0, twee CPU-threads.
Drie fictieve Nederlandse prompts per model; geen modeltraining.

| Model | Eerste koude token | Mediane eerste token (3 cases) | Beoordeling |
|---|---:|---:|---|
| qwen2.5:3b | 10.69 s | 2.69 s | Snelste; onjuiste aanspreekvorm/rekenantwoord in deze proef |
| qwen3.5:4b | 16.57 s | 6.65 s | Trager; rekenuitleg niet consequent |
| qwen3:4b | 12.48 s | 6.42 s | Afgewezen: Engelse denkregels in antwoord |
| qwen2.5:7b | 31.91 s | 6.03 s | Afgewezen als standaard: trager en rekenantwoord onjuist |

Keuze: Qwen2.5:3B blijft het lichte standaardmodel op Oracle. Grotere/nieuwere
modellen worden niet als verbetering voorgesteld op grond van alleen hun naam.
Deze CPU-modellen halen in deze proef niet consequent het gewenste redeneerniveau.
Bestaande expliciet gekozen Gemini/Groq-providers blijven beschikbaar. Kalender-,
tijd-, machtigings- en uitvoeringsbeslissingen blijven in deterministische Python.
De aanwezigheid van een verwacht trefwoord is geen kwaliteitsscore.

## Werkelijke HTTPS-keten

Een verse synthetische eigenaar/SQLite, dezelfde gateway, SSH-tunnel en Oracle-
3B-service. TLS, veilige cookies, CSRF-login, 401 zonder login, afgeschermde
interne controleroutes en voltooide SSE-uitvoer zijn werkelijk gecontroleerd.

- Volledige context: eerste antwoord 62.74 s; totale respons 64.50 s.
- Compacte Oracle-context: eerste antwoord 14.45 s; totale respons 16.43 s.

Dit zijn twee afzonderlijke live proeven, geen statistische garantie voor ieder
gesprek. De verkorte stockinstructies behouden serverbewijs, privacy, aanspreekvorm
en onbetrouwbare contextgrenzen. Eigen systeeminstructies worden volledig bewaard.

## STT en geheugen

Een CPU-only proef op de ontwikkeldesktop, acht door Piper gemaakte Nederlandse
zinnen, dezelfde Whisper Small-decoder, geen echte uitspraak/ruis.
- Baseline mediaan 2.62 s; zonder timestamps 2.51 s.
- Beide 4 genormaliseerde woordfouten op 60 referentiewoorden.
- Geobserveerde piek van de spraakhelper: 900 MiB.

De bestaande decoderkeuze is behouden; dit is geen bewijs voor nauwkeurigheid van
uw microfoon of prestaties van de nog ontbrekende mini-pc. TTS- en native
STT/first-audio-tijden blijven beschikbaar in de bestaande diagnostiek.

## Reproduceerbaar

- `scripts/benchmark_routes.py --output <bestand>`: alleen mocks.
- `scripts/benchmark_oracle_models.py`: alleen na expliciete modeldownloadopdracht op de VM.
- `scripts/check_hybrid_gateway.py --run-live ...`: tijdelijke eigenaar/database; geen persoonlijke data.
- `scripts/check_minipc_installation.ps1 -Package <pakket>`: echte geïsoleerde installatie, geen systeemtaak of account.

Externe broninformatie: [NDW-incidenten](https://docs.ndw.nu/faq/incidenten/),
[Caddy streamingproxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy),
[Ollama chat API](https://docs.ollama.com/api/chat).

Het versie-endpoint op Oracle had over de bestaande SSH-tunnel in drie proeven
een mediane HTTP-rondreis van 61,0 ms. Dit omvat ook de korte remote handler;
het is geen losse pakket-/netwerkmeting.
