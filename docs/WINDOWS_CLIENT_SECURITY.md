# Windows-client: beveiligingsgrens

De client importeert geen server/GUI/audio/plugins van Mark-LVII. PySide6-Essentials
is gekozen volgens gebruikersvoorkeur, met één QApplication en widgets op de
Qt-hoofdthread. HTTP/SSE draait op maximaal vier workers; signalen/slots leveren
resultaten aan de UI-thread. Tests controleren daadwerkelijk de thread-ID's.

Op expliciet gebruikersverzoek gebruikt de desktopapp nu gebruikersnaam en
wachtwoord via POST /api/v1/auth/desktop-login. De bestaande Argon2id-verificatie,
generieke fouten en dezelfde IP-inloglimiet worden hergebruikt. De route geeft
geen cookies af en weigert browsers met authcookies; de Origin-/JSON-/loopback-
controles blijven gelden. Een correcte eigenaarlogin verleent alleen de vier
bestaande chat-/statusrechten aan een Windows-apparaat. De installatie-UUID
is openbaar, wordt pas na wachtwoordcontrole gebruikt en kan geen browserapparaat
overnemen. Opnieuw inloggen hergebruikt het apparaat en trekt oude sessies ervan in.
Wachtwoordbeheer en overige apparaatbeheer blijven bij de eigenaarinterface.
De S256-pairing-API blijft beschikbaar voor andere clients, zonder bypass.

Refresh-tokens staan uitsluitend in Windows Credential Manager, generiek type,
per exacte serverorigin gehashte targetnaam. Access-tokens blijven in geheugen.
Geen plaintextfallback. Een proceslock voorkomt gelijktijdige instanties die
dezelfde refreshcredential roteren. Rotatie is binnen het proces geserialiseerd;
het oude duurzame token wordt vóór het verzoek verwijderd. Een verbindingsfout
vóór verzending behoudt de credential; bij een crash of onzekere refresh-response
is opnieuw inloggen nodig, in plaats van tokenreplay. Desktopsessies zijn standaard
maximaal 30 dagen geldig; ongebruikte refresh-tokens standaard 7 dagen.

TLS-certificaten/hostnamen worden geverifieerd, redirects worden niet gevolgd,
omgevingproxy's worden niet gebruikt. HTTP is uitsluitend toegestaan voor
127.0.0.1/localhost/::1. Een lokale HTTP-server wordt herkend aan het JARVIS-health-
contract; dit biedt geen cryptografische bescherming tegen malware onder hetzelfde
Windows-account. Remote endpoints vereisen echte vertrouwde HTTPS-certificaten.
Credentials worden nooit automatisch van de ene origin naar een andere gekopieerd.

UI-tekst is plaintext, geen HTML-uitvoering of modelcommando's. Verwijderen en
intrekken vragen bevestiging. Twee nieuwe API-routes laten een sessie alleen
het eigen apparaat bekijken/intrekken: GET /api/v1/auth/device en
POST /api/v1/auth/disconnect. Andere apparaten blijven eigenaarbeheer.
Cookiegebruik behoudt CSRF; native Bearer-gebruik behoudt fase-3-autorisatie.

De client logt geen verzoekbodies, tokens, codes of chattekst. Traymeldingen zijn
generiek. Logs en instellingen leven lokaal buiten Git. De lokale agent heeft
alleen een expliciete system_info-capability; geen shell of AI-aansturing.
Autostart staat uit en verandert alleen na expliciete gebruikerskeuze.

De build is unsigned. Geen SmartScreen-/antimalwarebeveiliging wordt uitgeschakeld.
Dit is geen externe penetratietest of garantie tegen een gecompromitteerd OS.
Zie ook de [serverbeveiliging](SECURITY.md) en [licenties](WINDOWS_CLIENT_THIRD_PARTY.md).
