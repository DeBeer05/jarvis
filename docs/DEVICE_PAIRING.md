# Apparaatkoppeling — fase 3

Er is nog geen Windows- of Android-clientapp. De lokale API ondersteunt wel hun
toekomstige aanmelding. Alleen de ingelogde eigenaar kan een koppelverzoek
goedkeuren. Doe dit uitsluitend voor een apparaat dat je zelf aan het koppelen bent.

## Werking

1. De nieuwe, cookie-vrije client maakt een willekeurige PKCE-verifier en
   bijbehorende S256-challenge. De verifier verlaat deze client pas bij inwisseling.
2. `POST /api/v1/pairing/requests` met device_name, device_type, scopes,
   code_challenge en code_challenge_method `S256` geeft request_id, device_code,
   user_code, verification_uri, expires_in en interval terug.
3. Alleen de menselijk leesbare user_code wordt op het nieuwe apparaat getoond.
   De eigenaar opent `/security` in een reeds ingelogde browser, controleert naam,
   type en rechten, typt de code van het nieuwe apparaat over en kiest expliciet
   **Koppeling goedkeuren**. Met **Weigeren** wordt het verzoek definitief geweigerd.
4. De client wisselt device_code plus code_verifier in via
   `POST /api/v1/pairing/token`. grant_type is
   `urn:ietf:params:oauth:grant-type:device_code`. Alleen na goedkeuring krijgt
   deze client een eigen access-/refresh-token en apparaat-/sessie-UUID.
5. De challenge is één keer bruikbaar en standaard 5 minuten geldig. Alleen de
   aangevraagde én goedgekeurde rechten worden opgeslagen.

Dit is gebaseerd op [RFC 8628](https://www.rfc-editor.org/rfc/rfc8628) met een
verplichte S256-bewijsuitbreiding naar [RFC 7636](https://www.rfc-editor.org/rfc/rfc7636).
Het is geen volledige OAuth-server: routes en foutresponses gebruiken het bestaande
JARVIS-contract `{"error":{"code":"...","message":"..."}}`.
verification_uri bevat nooit een code of geheim in de URL. De beheer-GET toont
geen user_code, device_code of verifier; de eigenaar moet de code echt vergelijken.

## Rechten

| Recht | Toegang |
| --- | --- |
| `chat:read` | Alle bestaande eigenaargesprekken bekijken |
| `chat:write` | Nieuwe gesprekken en chatberichten; vervolg in bestaande gesprekken vereist ook chat:read |
| `chat:delete` | Gesprekken verwijderen; afzonderlijk expliciet goedkeuren |
| `status:read` | Server- en providerstatus |

Standaard vraagt een apparaat alleen chat:read en chat:write aan. De eigenaar
kan die selectie verkleinen. Adminrechten, auditrechten en toekomstige integraties
zijn niet aan te vragen. Rechten gelden voor de ene eigenaar, niet voor afzonderlijke
gesprekken: geef chat:read alleen aan apparaten die alle gesprekken mogen lezen.
Ondersteunde typen: browser, windows, android, other; het type verleent geen rechten.

## Lokale proef met Windows PowerShell 5.1

Gebruik alleen synthetische gegevens. Log eerst in je browser in en open
`http://127.0.0.1:8765/security`. Voer daarna in een aparte lokale PowerShell uit:

```powershell
$jarvisBase = 'http://127.0.0.1:8765'
$pairBytes = New-Object byte[] 32
$pairRng = [Security.Cryptography.RandomNumberGenerator]::Create()
try { $pairRng.GetBytes($pairBytes) } finally { $pairRng.Dispose() }
$pairVerifier = [Convert]::ToBase64String($pairBytes).TrimEnd('=').Replace('+','-').Replace('/','_')
$pairSha = [Security.Cryptography.SHA256]::Create()
try { $pairHash = $pairSha.ComputeHash([Text.Encoding]::ASCII.GetBytes($pairVerifier)) } finally { $pairSha.Dispose() }
$pairChallenge = [Convert]::ToBase64String($pairHash).TrimEnd('=').Replace('+','-').Replace('/','_')
$pairBody = @{device_name='Lokale testclient';device_type='windows';scopes=@('chat:read','chat:write');code_challenge=$pairChallenge;code_challenge_method='S256'} | ConvertTo-Json
$pairRequest = Invoke-RestMethod "$jarvisBase/api/v1/pairing/requests" -Method Post -ContentType 'application/json' -Body $pairBody
Write-Host ('Vergelijk en vul deze code in je eigenaarbrowser in: ' + $pairRequest.user_code)
```

Keur nu precies dit verzoek in de browser goed. Voer pas daarna uit; respecteer
altijd het teruggegeven pollinterval bij herhalen:

```powershell
Start-Sleep -Seconds $pairRequest.interval
$pairTokenBody = @{grant_type='urn:ietf:params:oauth:grant-type:device_code';device_code=$pairRequest.device_code;code_verifier=$pairVerifier} | ConvertTo-Json
$pairCredentials = Invoke-RestMethod "$jarvisBase/api/v1/pairing/token" -Method Post -ContentType 'application/json' -Body $pairTokenBody
$jarvisHeaders = @{Authorization=('Bearer ' + $pairCredentials.access_token)}
$pairSession = Invoke-RestMethod "$jarvisBase/api/v1/auth/session" -Headers $jarvisHeaders
$pairSession | Select-Object device_id,session_id,permissions
Invoke-RestMethod "$jarvisBase/api/v1/chat/conversations" -Headers $jarvisHeaders
```

Laat `$pairRequest`, `$pairCredentials`, `$jarvisHeaders` en de tokenbody niet
los afdrukken. De voorbeelden houden geheimen uitsluitend in het shellgeheugen;
schrijf ze niet naar een bestand en deel de terminal niet. Sluit de testshell na
afloop en trek **Lokale testclient** in via de eigenaarbrowser. Dit voorbeeld
maakt geen echte clientapp of permanente credentialopslag.

Vernieuw voor tokenverloop met de native route, zonder browsercookies:

```powershell
$refreshBody = @{refresh_token=$pairCredentials.refresh_token} | ConvertTo-Json
$pairCredentials = Invoke-RestMethod "$jarvisBase/api/v1/auth/token" -Method Post -ContentType 'application/json' -Body $refreshBody
$jarvisHeaders = @{Authorization=('Bearer ' + $pairCredentials.access_token)}
```

Een tweede inwisseling van hetzelfde oude refresh-token trekt de gehele sessie
in. Dit is bedoeld beveiligingsgedrag; probeer bij netwerkonzekerheid niet
blind het oude token opnieuw, maar koppel opnieuw wanneer nodig.

## Fouten en grenzen

| Code | Actie |
| --- | --- |
| authorization_pending | Wacht op eigenaar en minimaal het pollinterval |
| slow_down | Verleng interval met 5 seconden, maximaal 30 seconden |
| expired_token | Start een nieuw koppelverzoek |
| access_denied | Eigenaar of poginglimiet heeft geweigerd; geen tokens |
| invalid_grant | Verkeerd bewijs, onbekende of al gebruikte code |
| rate_limited / busy | Wacht; geen onmiddellijke herhaallus |

Maximaal 5 nieuwe verzoeken per minuut/IP, 20 open verzoeken en 5 foutieve
code-/bewijspogingen per verzoek. Tokenpolls hebben daarnaast een per-IP-limiet.
Codes, tokens en verifier horen niet in logs, URLs of notificaties.

## Beheren en intrekken

Open `/security`. Hier staan naam, type, laatste activiteit, vertrouwen, rechten
en sessies per apparaat. Naam wijzigen behoudt UUID en rechten. Vink de
bevestiging aan en kies **Apparaat intrekken** om alle sessies en refresh-tokens
ervan direct te blokkeren. De registratie blijft zichtbaar als ingetrokken.
**Apparaat verwijderen** verwijdert de registratie, rechten en credentials;
gesprekken en beveiligingslog blijven bewaard. Voor het huidige apparaat volgt
opnieuw de loginpagina. Opnieuw koppelen maakt een nieuwe UUID.

API voor eigenaarbeheer: `GET /api/v1/devices`, `PATCH /api/v1/devices/{uuid}`
met name, `POST /api/v1/devices/{uuid}/revoke`, `DELETE /api/v1/devices/{uuid}`.
Een gekoppelde client kan deze beheerroutes niet gebruiken. Goedkeuring loopt via
`POST /api/v1/pairing/requests/{uuid}/decision` met approve, user_code en scopes;
de browser voegt automatisch de CSRF-header toe.
