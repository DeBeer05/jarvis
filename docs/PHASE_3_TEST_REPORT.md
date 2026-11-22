# Testverslag fase 3 — 23 november 2026

Scope: headless server versie 0.3.0, ontwikkeldesktop, Python 3.12.10,
localhost:8765, bestaande Git-root en SQLite. Geen wijzigingen aan echte
eigenaarcredentials, geen echte apparaten ingetrokken en geen bestaande chats gewist.

## Automatische functionele controle

` .\.venv\Scripts\python.exe -m pytest -q `: **156 geslaagd** in 51,36 seconden.
Dit omvat de 99 bestaande regressietests, nu met echte authenticatie in de
API-fixtures, plus 57 nieuwe beveiligings-/procesgevallen. Eén bekende
Starlette/httpx-testadapterdeprecatiewaarschuwing; geen testfouten.
Tests gebruiken uitsluitend tijdelijke databases en synthetische accounts.
AI-transporttests gebruiken mocks; geen API-sleutels of modeldownloads in tests/CI.

| Onderdeel | Uitgevoerd en geslaagd |
| --- | --- |
| Eigenaar | Eenmalig, CLI-only, interactieve verborgen invoer, Argon2id-productieparameters |
| Login/logout | Correct/fout wachtwoord, generieke fout, cookieflags, sessie-intrekking |
| Wachtwoord | Correct/incorrect huidig wachtwoord, revoke-all aan/uit |
| Sessies | Access-/absolute expiry, persistente geldigheid na herstart, sessieoverzicht/intrekking |
| Refresh | Rotatie, oude token/CSRF-replay, concurrerende vernieuwing, familie-intrekking, opslaglimiet |
| API/historie | Default-deny, bevoegde toegang, onbekende nieuwe route, status-/beheerrechten |
| Pairing | Aanvraag, codevergelijking, expliciete goedkeuring/weigering, S256-bewijs, expiry, polling/slowdown, replay |
| Gelijktijdigheid | Eén succesvolle inwisseling; geen dubbele apparaten; replay trekt vernieuwde sessie in |
| Apparaten | Naam, soft revoke, volledige verwijdering met credentialcleanup; geen verlies van chat/audit |
| Minimale rechten | Read-only, aparte chat:delete, write-only mag geen bestaande context opvragen, geen admin-/toekomstscopes |
| Lopende generatie | Revocation stopt normale én SSE-antwoorden en sluit provider af |
| Misbruik | IP-/route-/code-/bewijslimieten, auditretentie/capaciteit |
| Browser | CSRF login/write/refresh, Origin/Host/Fetch Metadata, Secure bij HTTPS, geen proxyheadertrust |
| Invoer/opslag | SQL-/XSS-achtige namen als letterlijke data; geen innerHTML/tokenstorage; geen secrets in DB/audit/logs |
| Migratie | Schema 2 naar 3 met voorafgaande back-up en behoud van opgeslagen chattekst |
| Proces/TCP | Echte tijdelijke server, ownerlogin, pairing, rechten, revoke, refresh, stop/start, sessie/historie/audit/logout |

Fixtures versnellen de meeste wachtwoordcontroles met een lichtere Argon2-
testhasher. Een afzonderlijke test controleert expliciet de echte runtimekosten
(64 MiB/t=3/p=2/Argon2id). Er is geen productie-bypass of vaste testlogin.
De procesproef draait op een tijdelijke poort/database, niet op de persoonlijke server.

## Echte desktopcontrole

- Bestaande database veilig naar schema 3 gemigreerd; pre-v3-back-up aanwezig.
- De eigenaar maakte zelf lokaal het account aan met setup-owner en bevestigde dit.
- De eigenaar logde zelf in Chrome in; de beveiligde webchat met bestaande historie
  en een succesvol Groq-antwoord is daadwerkelijk waargenomen.
- De loginpagina is in de browser bekeken. Schoon beeld zonder privégegevens:
  [login-screenshot](images/auth-login.jpg).
- Persoonlijke apparaten, wachtwoordwijziging en pairinggoedkeuring zijn niet
  handmatig op echte data uitgevoerd; die paden zijn met tijdelijke gegevens getest.
- De geteste broncode is via Stop-Server.ps1 / Start-Server.ps1 -Background actief
  gemaakt: health/ready 200; anonieme status, historie, apparaten en interne
  processtatus 401. Eigen controlstatus werkt met het script. Schema 3, 9 gesprekken,
  26 beurten en één pre-v3-back-up behouden; foreign_key_check zonder fouten.

## Beveiligingsscans

Geïsoleerde tools onder de genegeerde `.local/security-tools`; rapporten blijven
lokaal onder `.local/`. Niet de oorspronkelijke desktopdependencyboom installeren.

| Controle | Resultaat / scope |
| --- | --- |
| pip-audit 2.10.1 | 0 bekende kwetsbaarheden in de geïnstalleerde servervenv na update pip naar 26.3 |
| Bandit 1.9.4 | 0 bevindingen in server/; geen nosec-onderdrukkingen |
| Repositorysecretcheck | Huidige bestanden en index; geen nieuwe geheimpatroontreffers |
| Gitleaks 8.30.1 | Nieuwe fase-3-index/commitrange; resultaat bij Git-afronding hieronder |
| JS/pip/whitespace/structuur | Vier node --check, pip check, git diff --check en check_repository.py |

Het oude pip 25.0.1 had bekende advisories. De installer en CI upgraden nu eerst
naar de vastgelegde pip 26.3. Ook enkele statische waarschuwingen zijn zonder
onderdrukking opgelost. Scanresultaten zijn momentopnamen, geen garantie over
onbekende kwetsbaarheden. De oude upstream-TLS-sleutel blijft een bekende historische
treffer buiten de nieuwe wijzigingen; zie [SECURITY.md](SECURITY.md).

Herhaal lokaal, nadat de geïsoleerde scantools beschikbaar zijn:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
python scripts/check_repository.py
git diff --check
node --check server/static/chat.js
node --check server/static/auth.js
node --check server/static/login.js
node --check server/static/security.js
.\.local\security-tools\Scripts\python.exe -m pip_audit --path .venv/Lib/site-packages --format json --output .local/phase3-pip-audit.json
.\.local\security-tools\Scripts\python.exe -m bandit -r server -f json -o .local/phase3-bandit.json -q
```

## Zelf lokaal accepteren

1. Controleer health/ready op poort 8765 en log in op `/login`.
2. Open `/chat`, controleer bestaande historie en stuur een eigen kort testbericht.
3. Open `/security`: apparaten/sessies/audit worden alleen als eigenaar getoond.
4. Test optioneel een apart synthetisch apparaat volgens [DEVICE_PAIRING.md](DEVICE_PAIRING.md).
   Trek uitsluitend dat testapparaat in; dezelfde token moet daarna 401 krijgen.
5. Herstart met Stop-Server.ps1 en Start-Server.ps1 -Background; heropen de historie.
6. Uitloggen blokkeert nieuwe private API-verzoeken; log daarna zelf opnieuw in.
   Het echte wachtwoord wijzigen is niet nodig om de automatische testuitslag te bevestigen.

CI draait Repository checks en Server tests op Windows/Linux voor de PR naar
develop. Werkelijke PR-/merge-uitkomsten worden in DEVELOPMENT_PROGRESS.md en het
eindrapport vastgelegd; een lokale testuitslag vervangt die checks niet.
Main blijft buiten deze fase. Geen clientapps, Tailscale, LAN/publicatie, firewall-
wijzigingen, spraak, integraties, automatiseringen of mini-pc-deployment uitgevoerd.
**STOP na fase 3.**
