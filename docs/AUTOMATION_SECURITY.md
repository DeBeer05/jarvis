# Beveiliging fase 7

Automatiserings-API's vallen onder de bestaande default-deny gate, loopback-
controle, cookie-CSRF, Origin/Host-validatie, bodylimiet 64 KiB en rate limiting.
automation:read/write/approve en integrations:manage zijn aparte rechten. Alleen
de eigenaarbrowser krijgt ze bij migratie op basis van bestaand admin:account;
native rechten worden uitsluitend via een expliciete eigenaargrant toegevoegd.

De enige nieuwe publieke route is de GET OAuth-callback. Een cross-site Google-
redirect mag daar binnenkomen; elke andere cross-site route blijft geweigerd.
De callback vereist state (alleen digest in SQLite), eenmalige consumptie, PKCE,
vijf minuten verval en de nog geldige sessie/rechten van de initiërende eigenaar.
OAuth-codes worden niet in accesslogs geschreven: de bestaande Uvicorn-start
heeft access_log=False. Log nooit callback-URLs via een extra proxy/logger.

Windows DPAPI versleutelt verifier/tokenblobs voor dezelfde Windows-gebruiker.
Er is geen plaintext fallback. Google-clientconfiguratie blijft in een genegeerd
secrets/-bestand. Externe calls gaan naar vaste officiële HTTPS-origins, met
certificaatvalidatie, zonder omgevingsproxy of redirects. Gebruik passende
Windows-bestandsrechten en bescherm ook database/backups tegen andere accounts.

Er worden geen automatisch uitbreidbare AI-rechten gemaakt. Het model genereert
alleen JSON uit een vaste registry en de gebruiker dient een voorstel apart in.
Een samenvatting van e-mail/agenda heeft geen executor. Ontvangen antwoorden
worden nooit als opdrachten of als bewezen toestemming behandeld. Er is geen
eval, exec, subprocess of shell in de Automation Engine.

Gevoelige acties zijn immutable opgeslagen voorstellen. Approvaltokens worden
alleen als digest bewaard, zijn eenmalig, vijf minuten geldig en apparaatgebonden.
Rechten van de oorspronkelijke en goedkeurende apparaten worden opnieuw
gecontroleerd. Vlak vóór elke externe mutatie worden ook de actuele taakstatus,
workflowstatus, input en beleidsregels gecontroleerd. Er is nooit een garantie
dat een al verzonden HTTP-verzoek kan worden teruggeroepen.

Claimen gebeurt transactioneel. Na een crash worden veilige reads hervat;
mogelijk uitgevoerde externe acties krijgen uncertain, nooit een automatische
retry. Gmail heeft geen algemene idempotency-garantie: JARVIS kiest daarom bij
een onbekende uitkomst bewust voor controle door de gebruiker. Calendar-create
krijgt een deterministisch provider-ID; updates/deletes hebben If-Match. De
verwijder-API bewaart de idempotency-tombstone. Externe wijzigingen kunnen niet
als terugkerende blanket approval worden ingepland.

Volledige ontvangen e-mails worden niet persistent in de uitvoeringhistorie
opgeslagen. Expliciete concept-/actiegegevens blijven nodig voor beoordeling;
afgeronde/cancelled/denied/failed payloads ouder dan dertig dagen worden bij
opstart verwijderd. Audit is maximaal tienduizend gebeurtenissen; notificaties
dertig dagen. Backups hebben hun eigen bewaarbeheer en bevatten bestaande
persoonlijke data. Geen geheimen of persoonlijke runtimegegevens in Git.

Geen webhooks, externe FCM-bezorging, WhatsApp/SMS-transport, calls, publieke
gateway of productie zijn ingeschakeld. Echte Google-proeven vereisen een
testaccount en afzonderlijke toestemming; mocks zijn geen bewijs van een
werkende koppeling met jouw account.
