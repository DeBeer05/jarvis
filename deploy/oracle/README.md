# Oracle ARM64 — reviewbaar voorstel, nog niet uitgevoerd

Status 27 november 2026: uitsluitend read-only SSH-inspectie uitgevoerd. Ubuntu
24.04.5 ARM64, 2 OCPU/12 GB, circa 48 GB vrij; geen swap, git, Docker, Ollama of
Caddy. De lokale installatie blijft actief. Geen remote installatie, upload,
service-, firewall- of DNS-wijziging is toegestaan zonder afzonderlijke goedkeuring
volgens §15/§16 van de eigenaarsopdracht.

## Voorgestelde inrichting

Native systemd heeft hier minder onderdelen dan Docker. Backend als afzonderlijke
`jarvis`-gebruiker; code/releases in `/opt/jarvis/releases/<commit>`, symlink
`/opt/jarvis/current`; database, modellen en secrets buiten releases onder
`/var/lib/jarvis`. Root beheert code en `/etc/jarvis/server.env`; secrets zijn
alleen voor de service-eigenaar leesbaar (0600, bovenliggende directory 0700).
Geen desktoprequirements/PyQt/PySide op Oracle.

- Backend: 127.0.0.1:8765, één worker, bestaande authenticatie en rechten.
- Ollama: 127.0.0.1:11434, bestaand Qwen2.5:3B, één model/verzoek tegelijk.
- Caddy: publieke 80/443 met automatische certificaatvernieuwing, bestaande SSE.
  Er is geen nieuw WSS/full-duplex endpoint geïmplementeerd.
- CPU-spraakhelper in afzonderlijke `.local/voice-venv` per release, uitsluitend
  `requirements-voice-server.txt`. Bestaande lokaal toegestane modellen kunnen
  na toestemming worden overgezet; geen impliciete modeldownload bij runtime.
- Installatie gebruikt `requirements-server.txt` met constraints in een eigen
  `.venv`. ARM64-wheelresolutie is lokaal gecontroleerd voor server én helper;
  dat bewijst nog geen werkelijke inferenceprestaties op deze VM.

Templates: `jarvis.service`, `ollama-override.conf`, `Caddyfile`,
`server.env.example`. Vervang de voorbeeldhostnaam vóór gebruik. De backend
vertrouwt doorgestuurde HTTPS alleen van loopback met exact de ingestelde Host,
één geldig client-IP en HTTPS; interne beheerfuncties blijven onbereikbaar.
Uvicorn houdt `proxy_headers=False`. Geen authenticatie-uitschakelaar toegevoegd.

Backups en gecontroleerde updates hebben voorbereide systemd-services/timers;
geen hiervan is geïnstalleerd of ingeschakeld. De backuptimer bundelt ook de
expliciete configuratie/secrets; pas de lijst aan wanneer Google niet is ingericht.
Maak eerst een afzonderlijke 0600-backupsleutel in `/etc/jarvis/backup.key`.
Bewaar die ook veilig buiten deze VM; het archief bevat zijn eigen sleutel niet.

## Gratis hostnaam en kosten

Voorgesteld: `jarvis.<publiek-IP-met-streepjes>.sslip.io`; dit gebruikt bestaande
IP-afgeleide DNS en vereist geen domeinaankoop of DNS-account. Controleer de
resolutie vóór gebruik. Publieke 80/443 zijn nodig voor HTTP-01 en HTTPS; alleen
22 is momenteel toegestaan. Zowel hostfirewall als OCI ingress moeten hiervoor
expliciet worden gewijzigd. 8765/11434 worden nooit publiek geopend.

De gepubliceerde Always Free A1-limiet is 1500 OCPU-uren en 9000 GB-uren per
maand (equivalent 2 OCPU/12 GB). Deze VM past op zichzelf; accountbrede afname,
opslag en eventuele kosten zijn niet vanuit SSH bewezen. Controleer de console
vóór uitvoering. Geen extra VM, volume, load balancer, upgrade of credits kopen.
Oracle kan inactieve gratis VM's terugnemen; beschikbaarheid is niet gegarandeerd.
De gratis DNS-dienst en gedeelde certificaatlimieten geven evenmin een SLA.

Bronnen: [Oracle Always Free](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm),
[IP-afgeleide DNS](https://sslip.io/),
[Caddy HTTPS](https://caddyserver.com/docs/automatic-https).

## Backup en herstel vóór installatie/cutover

`scripts/cloud_backup.py` maakt via SQLite.backup een consistente snapshot,
controleert integriteit en versleutelt het geheel met een afzonderlijke Fernet-
backupsleutel. Geen ruwe live-DB/WAL kopiëren. `restore` weigert een bestaande
doelmap en controleert bestandsnamen, checksums en database vóór uitvoer.
Het hulpmiddel verzendt niets en start geen services.

Voorbeeld op Windows (pas na akkoord op de echte migratie uitvoeren):

```powershell
.venv/Scripts/python.exe scripts/cloud_backup.py keygen --key-file "$env:LOCALAPPDATA/JARVIS/Secrets/backup.bin"
.venv/Scripts/python.exe scripts/cloud_backup.py backup --database .local/data/jarvis.sqlite3 --archive .local/migration.enc --key-file "$env:LOCALAPPDATA/JARVIS/Secrets/backup.bin" --portable
.venv/Scripts/python.exe scripts/cloud_backup.py restore --archive .local/migration.enc --directory .local/restore-check --key-file "$env:LOCALAPPDATA/JARVIS/Secrets/backup.bin"
```

`--portable` ontsleutelt DPAPI-OAuth op de oorspronkelijke Windows-host en
versleutelt uitsluitend de snapshot opnieuw met een nieuwe vaultsleutel. Die
sleutel zit binnen het versleutelde archief; lopende OAuth-handshakes worden in
die kopie verwijderd. Brondata en Windows-DPAPI blijven ongemoeid. Zonder
`--portable` is een Windows-backup niet automatisch Linux-bruikbaar.

De DB bevat niet alle configuratie. Voeg expliciet benodigde bestanden toe met
`--include` (bijvoorbeeld Google-clientconfig); deze worden binnen het archief
versleuteld. Kopieer geen SSH-private key. ElevenLabs-DPAPI-bestanden moeten
afzonderlijk op Windows worden ontsleuteld en onder Linux als eigenaar-only
bestand opgeslagen; kopiëren van de DPAPI-bytes werkt daar niet. Herschrijf
alle Windows-paden naar de gecontroleerde Linux-configuratie. Een Windows-
DPAPI-backupsleutel kan ook niet rechtstreeks op Linux worden gelezen: herstel
lokaal, of draag hem bij de migratie via een apart beveiligd kanaal over en
gebruik de Linux-secretstore. Geen sleutels via chat/Git/commandlinewaarden.
De hele export/hersteloperatie hoort onder een afgeschermd eigenaaraccount.

Bestaande Google-refreshtokens blijven afhankelijk van hun oorspronkelijke
OAuth-client. Vervang die client niet blind. Een nieuwe cloudkoppeling vereist
een Web OAuth-client met exact `https://<host>/oauth/google/callback` geregistreerd
en een bewuste nieuwe eigenaarstoestemming. Dit is nog niet uitgevoerd.

## Uitvoervolgorde na afzonderlijke toestemming

1. Bevestig accountbrede gratis capaciteit, hostnaam, exact CI-groen commit en
   de opgesomde installatie-/netwerkwijzigingen; behoud SSH-toegang.
2. Installeer Ubuntu-onderdelen Python venv/git en gecontroleerde ARM64-versies
   van Ollama/Caddy uit officiële bronnen. Geen willekeurig `curl | sh` of
   ongecontroleerde automatische upgrades. Bewaar versies/hashes in het log.
3. Maak servicegebruiker/directories en release met de geïsoleerde environments.
   Valideer `systemd-analyze verify`, `caddy validate`, pip check, lokale health
   en echte CPU-inference. Qwen-download alleen na akkoord op omvang (circa
   2 GB); behoud Qwen2.5:3B. Meet latentie en RAM; geen snelheid claimen vooraf.
4. Eerst synthetische testdatabase en `AUTOMATIONS_ENABLED=false`. Open pas
   afgesproken 80/443, test geldig TLS/certificaatvernieuwing, login/pairing,
   autorisaties, spraak/cancel en externe afwijzing van interne endpoints.
5. Voor persoonlijke cutover: stop lokale planner/server, maak finale consistente
   export en test herstel. Breng gegevens/secrets alleen nu over. Laat cloud-
   automatiseringen uit totdat eigenaar inhoud en werking heeft gecontroleerd.
   Activeer maximaal één scheduler; maak geen nieuwe externe testberichten.
6. Verbind Windows/Android met dezelfde goedgekeurde HTTPS-host. Bestaande
   eigenaar/apparaatrechten blijven vereist; telefoon krijgt geen modellen.
7. Bewaar Windows als gestopte terugvalinstallatie en een tweede versleutelde
   backup buiten de VM. Retentie bijvoorbeeld 7 dagelijkse/4 wekelijkse backups,
   met afzonderlijk opgeslagen sleutel en periodiek testherstel. Nog geen
   backuptimer of externe opslag geïnstalleerd. De voorbereide timer maakt
   dagelijks een backup, maar verwijdert nog niets automatisch; bewaak schijfruimte
   en leg retentie/offsite-kopieën vast vóór permanente ingebruikname.

## Updates en rollback

Geen automatische pull van een bewegende branch. Voor elke update: expliciet
goedgekeurd exact commit, geslaagde CI, aparte kandidaat-release, pip check en
smoketest. Zet automatiseringen uit/stop service vóór databasebackup en migratie.
Schakel `current` pas na checks om; start eerst met automatiseringen uit en
controleer readiness. Oude release blijft beschikbaar.

`scripts/deploy_release.py` automatiseert dit voor een reeds geïnstalleerde
kandidaat. Een root-beheerd 0600-bestand `/etc/jarvis/approved-release.json` bevat
uitsluitend `{"release":"/opt/jarvis/releases/<commit>","commit":"<40-hex-commit>"}`.
Maak dit pas ná CI en inhoudelijke goedkeuring. De updater controleert commit,
schone werkboom, root-beheer van de releasepaden en de onderhoudsfence. Hij stopt
de service vóór backup, wisselt de symlink en controleert readiness. Bij fouten
worden oude database en release teruggezet vóór herstart; automatiseringen
blijven uit. Een mislukte ticket wordt hernoemd, zodat de timer niet eindeloos
herhaalt. Een backupfout laat de service veilig gestopt voor lokale inspectie.
Eerste installatie en persoonlijke cutover worden niet door dit script gedaan.
Orchestratie/rollback zijn met synthetische SQLite-backups en nagebootste
servicebesturing getest; systemd/Caddy-validatie op de VM staat nog open.

Bij mislukking vóór hervatten van acties: stop kandidaat, herstel geteste backup
in een nieuwe directory en schakel terug naar het vastgelegde oude commit.
Na uitgevoerde externe acties mag geen oude database blind worden teruggezet:
anders kunnen taken dubbel worden uitgevoerd. Houd dan beide schedulers uit,
behoud actuele taakstatus/tombstones en beoordeel onzekere acties apart.
Automatische onbeoordeelde productie-updates en cutover zijn niet ingericht.

## Nog te accepteren

Op echte Oracle-installatie: CPU-inference/latentie, langdurig RAM-gebruik,
publiek TLS/renewal, OAuth-herkoppeling en volledige restore/cutover. Native apps
en premiumstem zijn lokaal getest; Oracle is nog niet geïnstalleerd of gemigreerd.
