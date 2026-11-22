# Beveiliging — fase 3

Dit document betreft de nieuwe headless server op localhost:8765. Het oorspronkelijke
Mark-LVII-dashboard en de desktop-/cloudentrypoints zijn geen onderdeel van deze
beveiligingsgrens en worden niet door deze server gestart. Dit is een ontwikkelopstelling,
geen verklaring dat de hele upstreamapp productieveilig is.

## Authenticatie en autorisatie

- Eén lokale eigenaar, uitsluitend via interactieve CLI-setup met gestopte server.
- Argon2id via argon2-cffi: 64 MiB, 3 iteraties, parallelisme 2, bibliotheeksalt;
  maximaal twee gelijktijdige hashberekeningen buiten de eventloop.
- Onbekende gebruiker volgt dezelfde dure wachtwoordcontrole; generieke loginfout,
  persistente IP-rate limit, geen wachtwoorden of gebruikersnamen in login-audit.
- Willekeurige opaque access-/refresh-tokens met 256 bits entropie. Alleen SHA-256-
  digests staan in SQLite. Geen JWT, gedeeld clientgeheim of zelfgebouwde cryptografie.
- Refreshrotatie is transactioneel. Replay trekt de sessiefamilie in, ook wanneer
  de oude CSRF-binding wordt meegestuurd; intrekking commit voordat een fout terugkomt.
  Maximaal 4096 rotaties per sessie, daarna opnieuw inloggen. Absolute sessieduur
  voorkomt onbeperkte verlenging.
- Default-deny ASGI-gate vóór alle routers; nieuwe onbekende routes vereisen
  eigenaarbeheer. Bekende chat/status/beheerroutes vereisen afzonderlijke rechten.
  Geen authenticatie-uitvlag. Device- en sessiestatus worden serverzijdig gecontroleerd.
- Nieuwe apparaten krijgen alleen expliciet goedgekeurde bestaande rechten.
  chat:delete is apart; gebruik van bestaand modelcontext vereist ook chat:read.
  Alle gesprekken zijn van één eigenaar; dit is geen multi-user-tenantisolatie.
- Beveiligingsmutaties controleren sessiegeldigheid opnieuw in hun schrijftransactie.
  Lopende AI-generatie controleert intrekking iedere 0,5 seconde en sluit transport af.

## Browser- en HTTP-grens

Hostgebonden HttpOnly/SameSite-Strict-authcookies; gebonden CSRF-cookie plus header
voor schrijvende cookieverzoeken, ook login/refresh. CSRF-geheimen worden gehasht
bewaard; korte prelogin-nonces zijn in aantal begrensd. Tokens worden nooit in
browserstorage opgeslagen. Geen CORS-toestemming, geen proxyheadertrust.
Exacte Host-/Origin-allowlists, cross-site Fetch Metadata-weigering, JSON-bodytype
en 64-KiB-requestgrens beschermen aanvullend tegen cross-origin-verzoeken en rebinding.
Publiek zijn alleen health/readiness, statische shells/assets en noodzakelijke
login-/pairingroutes met hun eigen controles. De shells bevatten geen historie.
`/openapi.json` vereist eigenaarrechten; ontwikkelmodus biedt geen Swagger-UI.
De interne status/shutdownroutes gebruiken een apart procescontroletoken, geen
eigenaarsessie; de scripts lezen dat lokaal en geven het niet weer.

Eigen frontendcode toont gebruikers-/modeltekst via textContent, niet via HTML.
Geen externe scripts/fonts; CSP, nosniff, no-store, frame-/referrerbeleid zijn actief.
Dit beperkt XSS; het maakt vertrouwde browserextensies of een besmet OS niet veilig.
SQL gebruikt vaste statements met parameters. UUIDs/namen/scopes worden gevalideerd;
validatiefouten geven de oorspronkelijke invoer niet terug.

## Opslag, audit en back-up

Database: `.local/data/jarvis.sqlite3`, schema 3. Bestaande schema's 1/2 krijgen
vóór migratie een unieke `*.pre-v3-*.bak` via SQLite-backup; chatgegevens blijven
behouden. De back-ups kunnen privégesprekken bevatten: beveilig ze zoals de database.
SQLite is niet versleuteld door deze app. Bescherm Windows-account, schijf, .env,
runtimefiles, logs en back-ups met OS-toegangsrechten en geschikte schijfversleuteling.
De app kan een beheerder of malware onder hetzelfde Windows-account niet tegenhouden.

Auditlog: `/security`, of `GET /api/v1/security/audit?limit=50&offset=0` met
audit:read. Login/fouten/logout, wachtwoordwijziging, refresh/replay, pairingbesluiten,
apparaatbeheer en geweigerde toegang worden als vaste events met tijd/IDs opgeslagen.
Geen wachtwoorden, tokens, koppelcodes, IP-adressen of chatinhoud in auditrecords.
Standaard 30 dagen en maximaal 10000 records; oude records worden bij onderhoud,
schrijven en lezen begrensd. Sessies/refreshhistorie worden na verloop/intrekking
plus één dag opgeruimd bij opstart. Dit is lokaal auditbewijs, geen tegen een
OS-beheerder onveranderlijk logarchief. Per-request accesslogging staat uit.

.env, .local, databases, back-ups en runtimecredentials zijn uitgesloten van Git.
Providerkeys blijven serverzijdig; de gekozen AI-provider ontvangt wel de verzonden
chatcontext zoals beschreven in [AI_ENGINE.md](AI_ENGINE.md).

## HTTPS en Tailscale: uitsluitend voorbereiding

Nu: HTTP op loopback, geen bereikbaarheid vanaf LAN/telefoon/internet, geen
Windows Firewall-uitzondering, routerpoort, proxy, Tailscale-installatie of mini-pc-
deployment. Secure-cookies volgen het echte HTTPS-requestscheme, nooit een
X-Forwarded-Proto-header. Plain HTTP via een andere hostname mag geen authcookies
uitgeven. `JARVIS_COOKIE_SECURE=true` is voor een werkelijk werkende HTTPS-opstelling;
dat aanzetten op huidige HTTP-loopback verhindert browserlogin.

Een latere expliciete opdracht moet eerst private tailnettoegang, apparaatidentiteit,
ACLs/grants, TLS-hostnaam/certificaatbeheer, HTTPS-termination, alleen vertrouwde
proxypaden en Origin-/Hostconfiguratie samen ontwerpen en testen. Alleen een host
aan een allowlist toevoegen is geen ondersteunde remote deployment. Geen publieke
Funnel, port forwarding of internetproxy als stilzwijgend onderdeel hiervan.
Officiële voorbereiding:
[Tailscale HTTPS](https://tailscale.com/docs/how-to/set-up-https-certificates),
[Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve).

## Controle en beperkingen

[PHASE_3_TEST_REPORT.md](PHASE_3_TEST_REPORT.md) bevat de uitgevoerde controles.
Dependency-audit betreft de geïsoleerde servervenv, Bandit de servercode en
secret scanning de nieuwe wijzigingen. Dat is geen externe penetratietest,
formeel bewijs of audit van de volledige desktopstack.

Bekende historische uitzondering: upstreamcommit `067f528` bevatte een oude TLS-
privésleutel, upstream later verwijderd in `8a79f40`. De huidige tree gebruikt
die niet. De behouden forkgeschiedenis bevat hem nog; een volledige historiescan
blijft daarom een treffer geven. Niet hergebruiken; de oorspronkelijke historie
is volgens opdracht niet herschreven. De nieuwe fase-3-wijzigingen mogen geen
nieuwe geheimen bevatten.

Primaire bronnen:
[OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html),
[argon2-cffi](https://argon2-cffi.readthedocs.io/en/stable/howto.html),
[OWASP CSRF](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html),
[RFC 9700](https://www.rfc-editor.org/rfc/rfc9700),
[RFC 8628](https://www.rfc-editor.org/rfc/rfc8628),
[RFC 7636](https://www.rfc-editor.org/rfc/rfc7636).
