# Authenticatie — fase 3, versie 0.3.0

De server blijft uitsluitend op `http://127.0.0.1:8765`. Persoonlijke API's
vereisen altijd authenticatie; er is geen instelling om die uit te schakelen.
De bestaande gesprekken blijven in dezelfde SQLite-database bewaard.

## Eerste eigenaar

Op deze werkplek heeft de eigenaar dit al zelf uitgevoerd en succesvol ingelogd.
Voor een nieuwe, lege installatie: open een interactieve PowerShell in de
projectroot, installeer de serverdependencies en stop een eventueel draaiende server:

```powershell
powershell.exe -NoProfile -File scripts/Install-ServerDependencies.ps1 -IncludeTests
powershell.exe -NoProfile -File scripts/Stop-Server.ps1
.\.venv\Scripts\python.exe -m server setup-owner
powershell.exe -NoProfile -File scripts/Start-Server.ps1 -Background
Start-Process http://127.0.0.1:8765/login
```

Kies lokaal je gebruikersnaam (standaard `owner`) en typ tweemaal een eigen
wachtwoord van 12–128 tekens. Het wachtwoord verschijnt niet in de terminal en
staat nooit in een commandoregel. De setup accepteert geen niet-interactieve
invoer, gebruikt dezelfde proceslock als de server en weigert een tweede eigenaar.
Er bestaat geen HTTP-registratieroute of ingebouwd standaardwachtwoord.
Bewaar je wachtwoord in je eigen wachtwoordmanager. Er is in deze fase geen
herstelmail of wachtwoordreset zonder de bestaande eigenaar; verwijder daarvoor
niet de database, want die bevat ook je gesprekken.

## Dagelijks gebruik

De Windows-client heeft op gebruikersverzoek ook een directe wachtwoordlogin:
POST /api/v1/auth/desktop-login met username, password, device_name en device_id
(de openbare installatie-UUID). Dit is een cookie-vrije native route met dezelfde
Argon2id-verificatie en brute-forcelimiet; de response bevat opaque access/refresh.
Geen goedkeuringscode nodig voor deze eigenaarlogin. De client bewaart alleen
refresh in Windows Credential Manager. Desktop blijft standaard maximaal 30
dagen aangemeld; de ongebruikte refresh-levensduur blijft standaard 7 dagen.
De browserlogin en andere apparaten met S256-pairing blijven werken.

1. Open `/login`, vul je eigen gegevens in en kies **Inloggen**.
2. De webchat op `/chat` laadt pas na authenticatie je gespreksgeschiedenis.
3. Kies **Beveiliging** of open `/security` voor apparaten, sessies en auditlog.
4. Kies **Uitloggen** om de huidige sessie serverzijdig in te trekken en cookies
   te wissen. Andere apparaten blijven ingelogd.
5. Wijzig onder **Wachtwoord wijzigen** het huidige en nieuwe wachtwoord. De
   standaard aangevinkte optie trekt alle sessies in, inclusief deze browser;
   log daarna opnieuw in. Zonder deze optie blijven bestaande sessies geldig.
6. Onder **Sessies** kun je één specifieke sessie intrekken. Trek je de huidige
   sessie in, dan ga je terug naar de loginpagina.

Een verlopen of ingetrokken sessie krijgt geen toegang tot historie of chat.
Intrekking beëindigt ook een lopende generatie, gecontroleerd iedere 0,5 seconde.
Een procesherstart behoudt geldige sessies; de absolute eindtijd wordt niet verlengd.

## Cookies en API-contract

Browserlogin gebruikt `jarvis_access` (HttpOnly, pad `/`) en `jarvis_refresh`
(HttpOnly, pad `/api/v1/auth`). Beide zijn hostgebonden en SameSite Strict.
`jarvis_csrf` is leesbaar voor de eigen JavaScript-code; ieder schrijvend
cookieverzoek vereist de overeenkomstige header `X-Jarvis-CSRF` én de binding
aan de sessie. Voor login haalt `/api/v1/auth/csrf` een tijdelijke nonce op.
`jarvis_device` onthoudt alleen een apparaat-UUID; dit is geen toegangsbewijs.
Bij HTTPS krijgen cookies automatisch Secure; bij HTTP is uitsluitend localhost
toegestaan. Er staan geen authenticatietokens in localStorage of sessionStorage.

| Route | Gebruik |
| --- | --- |
| `GET /api/v1/auth/status` | Publiek: alleen `setup_required` |
| `GET /api/v1/auth/csrf` | Publiek: CSRF-cookie, geen toegangstoken |
| `POST /api/v1/auth/login` | JSON username/password/device_name + CSRF; cookies, geen tokens in JSON |
| `GET /api/v1/auth/session` | Huidige sessie en rechten, geen geheimen |
| `POST /api/v1/auth/refresh` | Browser: refresh-cookie + CSRF; roteert alle sessiegeheimen |
| `POST /api/v1/auth/token` | Native: JSON refresh_token, zonder browserauthcookies |
| `POST /api/v1/auth/logout` | Trekt huidige sessie in |
| `GET /api/v1/auth/sessions` | Alleen eigenaarbeheer |
| `DELETE /api/v1/auth/sessions/{uuid}` | Alleen eigenaarbeheer; één sessie intrekken |
| `POST /api/v1/auth/password` | current_password, new_password, optioneel revoke_all_sessions |

Native clients verkrijgen hun eerste sessie via [apparaatkoppeling](DEVICE_PAIRING.md).
Daarna sturen ze `Authorization: Bearer <access_token>` in een header. Een
refresh-token mag uitsluitend naar de tokenroute in een JSON-body. Bewaar het in
een geschikte OS-secretstore bij toekomstige clientontwikkeling. Geen tokens in
URL's, terminaloutput, shellhistorie, screenshots of Git.

Access-tokens zijn standaard 5 minuten geldig. Vernieuw vóór afloop en vervang
atomair het oude refresh-token door het nieuwe. Hergebruik van een verbruikt
refresh-token trekt de hele sessie in. De browser coördineert vernieuwing tussen
tabbladen via Web Locks waar beschikbaar; verouderde browsers zonder die API
kunnen bij gelijktijdig vernieuwen opnieuw moeten inloggen.

## Instellingen in de lokale .env

| Variabele | Default | Toegestaan |
| --- | --- | --- |
| `JARVIS_ACCESS_SECONDS` | 300 | 60–900 |
| `JARVIS_REFRESH_SECONDS` | 604800 | 3600–2592000; maximaal sessieduur |
| `JARVIS_SESSION_SECONDS` | 604800 | 3600–2592000, absolute eindtijd |
| `JARVIS_DESKTOP_SESSION_SECONDS` | 2592000 | 3600–2592000, absolute eindtijd bij desktopwachtwoordlogin |
| `JARVIS_PAIRING_SECONDS` | 300 | 60–900 |
| `JARVIS_PAIRING_POLL_SECONDS` | 5 | 5–30 |
| `JARVIS_LOGIN_MAX_ATTEMPTS` | 5 | 1–20 per IP en tijdvenster |
| `JARVIS_LOGIN_WINDOW_SECONDS` | 300 | 60–3600 |
| `JARVIS_AUTH_REQUESTS_PER_MINUTE` | 60 | 10–120 per publieke authroute/IP |
| `JARVIS_AUDIT_RETENTION_DAYS` | 30 | 1–365 |
| `JARVIS_AUDIT_MAX_ENTRIES` | 10000 | 100–100000 |
| `JARVIS_MAX_DEVICES` | 20 | 2–100 actieve apparaten |
| `JARVIS_MAX_SESSIONS` | 20 | 2–100 actieve sessies |
| `JARVIS_PASSWORD_REVOKE_ALL` | true | true/false; API kan expliciet kiezen |
| `JARVIS_COOKIE_SECURE` | auto | auto/true; true vereist HTTPS voor browsergebruik |
| `JARVIS_TRUSTED_HOSTS` | 127.0.0.1,localhost | Maximaal 10 exacte hosts, geen wildcard |
| `JARVIS_ALLOWED_ORIGINS` | http://127.0.0.1:8765,http://localhost:8765 | Exacte origins, HTTP alleen localhost |

Herstart na wijzigingen met de stop- en startscripts. Origin-/hostinstellingen
openen geen netwerktoegang. Houd een werkende eigenaarbrowser beschikbaar om
oude apparaten/sessies in te trekken voordat een ingestelde limiet bereikt is.
Zie [beveiligingsgrenzen](SECURITY.md) voor TLS en toekomstig Tailscale-gebruik.
