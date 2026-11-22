# Chat-API — versie 0.2.0

Basis `http://127.0.0.1:8765`, echte loopbackclients, geen externe toegang.
Alle payloads zijn JSON; streaming gebruikt SSE over een POST met fetch/curl,
niet de alleen-GET-EventSource-constructor. Zie ook [SERVER_API.md](SERVER_API.md).

## Berichten

`POST /api/v1/chat` en `POST /api/v1/chat/stream` accepteren dezelfde invoer:

```json
{"message":"Hallo JARVIS, antwoord kort in het Nederlands.","provider":"auto"}
```

`provider` is optioneel (configdefault) of auto/gemini/ollama. Geef bij een vervolg
`conversation_id` uit de vorige response mee. Optioneel `request_id`: een nieuwe
UUID per verzoek, ook handig voor annuleren. Hergebruik wordt met 409 geweigerd;
dit is geen retry die dezelfde modelaanroep herhaalt. Onbekende velden, ongeldige
UUID's, lege/te lange berichten en ongeldige providers worden geweigerd.

Nonstream: HTTP 200 bij completed, 502 bij providerfout, 499 bij annulering:

```json
{
  "request_id":"00000000-0000-4000-8000-000000000001",
  "conversation_id":"00000000-0000-4000-8000-000000000002",
  "provider":"gemini", "model":"gemini-3.8-flash",
  "status":"completed", "message":"Hallo! Waarmee kan ik helpen?", "error":null
}
```

Dit is een contractsvoorbeeld, geen hier live gegenereerd antwoord. Bij een fout
bevat `error` een `code` en veilig Nederlands `message`. Gedeeltelijk ontvangen
tekst blijft in `message`; provider/model zijn null als geen tekst werd ontvangen.

SSE-responses starten met HTTP 200 zodra de generatie is toegelaten; lees daarna
de events om succes/fout te bepalen. Iedere frame heeft `event: <type>` en één
`data: {...}`-regel, gevolgd door een lege regel:

| Type | Inhoud |
| --- | --- |
| `meta` | request_id, conversation_id |
| `fallback` | from, to, code, message |
| `provider` | werkelijk gebruikte provider en model |
| `delta` | tekstfragment in text |
| `error` | code en message |
| `done` | volledige nonstream-response, definitieve status |

Bij een levende verbinding eindigt het antwoord met done. Bij disconnect kan de
client dit event niet ontvangen; de server annuleert en bewaart de status alsnog.
Een halve stream zonder eindmarkering geldt als fout, niet als succesvol antwoord.

## Overige routes

| Route | Gedrag |
| --- | --- |
| `POST /api/v1/chat/requests/{request_id}/cancel` | cancelling of not_active; geen willekeurige processkill |
| `GET /api/v1/chat/conversations?limit=50&offset=0` | items met metadata, has_more; limit 1–100 |
| `GET /api/v1/chat/conversations/{id}` | metadata en turns, inclusief user_text, assistant_text, provider, model, status, error_code/error |
| `DELETE /api/v1/chat/conversations/{id}` | deleted; verwijdert beurten transactioneel mee; 409 tijdens generatie |
| `GET /api/v1/ai/providers` | mode, preferred, profile, providers met model/configured/available en reden |
| `GET /chat` | lokale statische webchat, geen externe frontendassets |

Gemini beschikbaarheid is null/not_verified bij een aanwezige sleutel: geen
betaalde achtergrondtest. Ontbrekende sleutel is false/not_configured. Ollama
wordt echt met /api/tags geprobed, inclusief exacte modelnaam.

Toelatingsfouten gebruiken `{"error":{"code":"...","message":"..."}}`.
Mogelijke statussen: 404 onbekend gesprek, 409 dubbel/vergrendeld/volle historie,
413 te grote body, 422 ongeldige invoer, 429 bezet/rate limit. Origin buiten de
eigen localhost-origin krijgt 403; proxyheaders verlenen geen toegang.
Geen inputtekst of ruwe providerdiagnose wordt in foutresponses teruggekaatst.

## Zelf testen in Windows PowerShell 5.1

Start en controleer de server; configureer eerst één provider volgens
[AI_ENGINE.md](AI_ENGINE.md). Zonder provider is een duidelijke fout de verwachte
uitkomst, geen bewijs dat AI-antwoorden live werken.

```powershell
powershell.exe -NoProfile -File scripts/Start-Server.ps1 -Background
Invoke-RestMethod http://127.0.0.1:8765/health
Invoke-RestMethod http://127.0.0.1:8765/ready
Invoke-RestMethod http://127.0.0.1:8765/api/v1/ai/providers
Start-Process http://127.0.0.1:8765/chat
```

Normaal verzoek en vervolg in hetzelfde gesprek:

```powershell
$payload = @{message='Onthoud voor dit testgesprek: mijn testkleur is blauw.';provider='gemini'} | ConvertTo-Json
$answer = Invoke-RestMethod http://127.0.0.1:8765/api/v1/chat -Method Post -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($payload))
$conversationId = $answer.conversation_id
$payload = @{message='Wat is mijn testkleur?';conversation_id=$conversationId;provider='gemini'} | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8765/api/v1/chat -Method Post -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($payload))
```

Verander de provider in ollama voor een eigen geïnstalleerd lokaal model. Test
auto nadat beide providers beschikbaar zijn; een ontbrekende Gemini-sleutel met
werkende Ollama toont fallback en daarna Ollama als werkelijke provider.

Streaming zonder frontend, met Windows curl.exe en een tijdelijk UTF-8-bestand
(geen sleutels of persoonsgegevens in deze test):

```powershell
$requestId = [guid]::NewGuid().ToString()
$payload = @{message='Noem kort vijf planeten.';provider='auto';request_id=$requestId} | ConvertTo-Json
$testBodyPath = Join-Path $env:TEMP ('jarvis-chat-' + $requestId + '.json')
[IO.File]::WriteAllText($testBodyPath, $payload, (New-Object Text.UTF8Encoding($false)))
try {
    curl.exe --no-buffer --silent --show-error -H 'Content-Type: application/json' --data-binary "@$testBodyPath" http://127.0.0.1:8765/api/v1/chat/stream
} finally {
    Remove-Item -LiteralPath $testBodyPath
}
```

Bekijk meta/provider/delta/done en eventuele fallback/error. Stop in de webchat
een langer antwoord met **Stop**. Of voer in een tweede terminal, met de UUID van
het lopende verzoek, `Invoke-RestMethod -Method Post
http://127.0.0.1:8765/api/v1/chat/requests/UUID/cancel` uit. Na de definitieve
status mag een volgend bericht weer starten.

Herstart en controleer dezelfde historie:

```powershell
Invoke-RestMethod "http://127.0.0.1:8765/api/v1/chat/conversations/$conversationId"
powershell.exe -NoProfile -File scripts/Stop-Server.ps1
powershell.exe -NoProfile -File scripts/Start-Server.ps1 -Background
Invoke-RestMethod "http://127.0.0.1:8765/api/v1/chat/conversations/$conversationId"
```

Open hetzelfde gesprek ook na paginavernieuwing in de webchat. Verwijder alleen
je eigen testgesprek via de prullenbak of de DELETE-route; controleer dat het uit
de lijst verdwijnt. De SQLite-bestanden staan standaard in `.local/data/`.
