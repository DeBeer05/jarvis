# JARVIS installeren op uw mini-pc

Kopieer de complete map `JARVIS-MiniPC` uit de ZIP naar bijvoorbeeld
`C:\Installatie\JARVIS-MiniPC`. De definitieve installatie staat standaard in
`C:\ProgramData\JARVIS`. Een ontwikkelomgeving of Codex is niet nodig.

## Installatie

1. Rechtsklik op Start → Terminal (administrator) → PowerShell.
2. Voer uit:

```powershell
cd C:\Installatie\JARVIS-MiniPC
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\INSTALL.ps1
```

De installer controleert alle backendbestanden, installeert indien nodig een
ondertekende Python 3.12, maakt een eigen virtual environment, installeert de
begrensde serverdependencies en initialiseert SQLite. U kiest zelf een
gebruikersnaam en wachtwoord; bestaande eigenaarsgegevens worden behouden.
Beveiligingssoftware wordt niet uitgeschakeld. Internet is nodig voor Python,
dependencies en externe diensten. Er wordt geen taalmodel op de mini-pc geïnstalleerd. De bestaande geïsoleerde
Whisper Small/Piper-runtime en goedgekeurde Nederlandse spraakmodellen worden
geïnstalleerd (circa 626 MB modellen, naast de dependencies). Microfoonopname wordt
daarmee niet ingeschakeld. Gebruik `-SkipVoice` voor een bewuste installatie zonder spraak.

De taak `JARVIS-MiniPC` start als SYSTEM bij het opstarten van Windows, ook zonder
aangemelde gebruiker. Een crash wordt maximaal tien keer met een minuut pauze
opnieuw gestart. Alleen lokale poort 8765 wordt gebruikt. De installatie wijzigt
geen Windows-firewallregels. Persoonlijke bestanden, logs en machine-DPAPI-sleutels
zijn alleen toegankelijk voor SYSTEM en lokale administrators.

## Windows-onderdelen die kunnen ontbreken

De geautomatiseerde installatie van deze Windows-onderdelen kon niet worden
opgenomen: automatische veiligheidsreview blokkeerde die uitbreiding zonder
nadere reden. Op systemen waar ze aanwezig zijn, is deze stap niet nodig.

Voor Oracle heeft u uitsluitend de OpenSSH-client nodig. Als CONNECT meldt dat
de client ontbreekt: open PowerShell als administrator en voer zelf uit:

```powershell
Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
```

Dit installeert de client. Installeer hiervoor geen SSH-server en open geen poort.
De [officiële Microsoft-instructie](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse)
beschrijft dezelfde clientinstallatie.

Als het importeren of starten van de lokale spraakruntime een ontbrekende
Microsoft-DLL meldt, open de [officiële Visual C++-downloadpagina](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist),
kies de nieuwste ondersteunde **X64**-download, open het gedownloade installatiebestand
en kies Installeren of Herstellen. Volg een eventuele herstartmelding. Gebruik
geen DLL-downloadsites. Het pakket controleert de echte spraakimports en presenteert
een ontbrekende runtime niet als geslaagde spraakinstallatie.

## Oracle en veilige toegang buitenshuis

Op Oracle moeten `deploy/oracle/install-inference.sh` en `install-gateway.sh`
vooraf zijn uitgevoerd. Gebruik uitsluitend uw bestaande VM; maak geen betaalde
resources aan. De HTTPS-gateway krijgt een gratis IP-afgeleide sslip.io-hostnaam.

Voer op de mini-pc uit:

```powershell
cd C:\ProgramData\JARVIS
.\CONNECT-ORACLE.ps1
```

Geef uw Oracle-host/IP, de **eerder onafhankelijk geverifieerde** SSH-hostsleutel
(`ssh-ed25519 AAAA...`) en de gatewayhostnaam op. De installer zoekt uw bestaande
`Documenten\oracle ssh\private.key`, inclusief Windows/OneDrive-omleiding.
Bij een afwijkende sleutel stopt SSH. Accepteer geen onbekende sleutel op goed geluk.

Een nieuwe tunnelsleutel wordt uitsluitend lokaal opgeslagen. Alleen de publieke
sleutel gaat naar Oracle. De beperkte gebruiker `jarvis-link` kan uitsluitend
de twee benodigde loopbackpoorten doorverbinden; geen shell of algemene proxy.
De taak `JARVIS-OracleLink` herstelt de tunnel automatisch na verbindingsverlies.

AI loopt via localhost:11435 → versleutelde SSH → Oracle localhost:11434.
HTTPS loopt via Oracle:443 → localhost:18765 → SSH → mini-pc localhost:8765.
De telefoon gebruikt gewoon HTTPS; een doorlopende VPN is niet nodig.
De database, machtigingen en persoonlijke geheugenopslag blijven op de mini-pc.
Oracle ontvangt uitsluitend de geselecteerde AI-context. Zet AI op offline om
externe AI en actuele publieke bronnen te pauzeren.

## Desktop, Android en machtigingen

Open op de mini-pc `http://127.0.0.1:8765` en meld u aan. Gebruik op Windows en
Android de bestaande JARVIS-app en vul bij het externe serveradres de volledige
`https://...sslip.io`-origin in. Gebruik geen IP met HTTP buitenshuis.
Android blijft eigenaarpairing vereisen. Verleen alleen de gewenste apparaat-,
microfoon-, automatiserings- en integratierechten. De installer verleent die niet.
Oude desktopcredentials en DPAPI-bestanden kunnen niet zomaar naar SYSTEM of
een andere computer worden gekopieerd. Koppel Google opnieuw of gebruik de
bestaande expliciete portable back-up/importprocedure op de oorspronkelijke pc.
Verwijder de oorspronkelijke gegevens pas nadat u de migratie zelf hebt gecontroleerd.

Microfoon en wake-word blijven onder uw bestaande opt-in staan. Zonder een
beschikbare spraakruntime toont JARVIS dit als ontbrekende configuratie. ElevenLabs
vereist de eigen backend-sleutel; zet die nooit in een chat of ZIP. Voer in de
administrator-PowerShell `./STEM-INSTELLEN.ps1` uit, geef uw Voice ID en daarna de
onzichtbaar ingevoerde sleutel op en voer `./RESTART.ps1` uit. Kies daarna Premium
bij Spraak in de app. De sleutel wordt met machine-DPAPI onder de beveiligde
installatiemap opgeslagen; de client krijgt deze nooit.

## Smart home en andere integraties

Open Instellingen → Integraties. Home Assistant vereist uw bestaande HTTPS-adres,
een beperkte token en expliciet toegestane entiteiten; voer de token in via het
bestaande beveiligde beheerscherm. Creality Cloud en Phone Link hebben niet
vanzelf een algemene ondersteunde bedienings-API. JARVIS toont de beschikbare
koppeling of opent de ondersteunde app; er worden geen print-/belresultaten verzonnen.
Verkeersafhankelijke vertrektijden vereisen een werkelijke verkeersbron. Zonder
bron blijven vertraging en exacte vertrektijd onbekend. Er wordt geen abonnement gekocht.

## Controleren en dagelijks beheer

```powershell
cd C:\ProgramData\JARVIS
.\STATUS.ps1
.\STOP.ps1
.\START.ps1
.\RESTART.ps1
.\REPAIR.ps1
```

Controleer `http://127.0.0.1:8765/ready`, vervolgens de HTTPS-origin op uw telefoon
zonder wifi. Controleer de Oracle-status en meetwaarden in Instellingen. Test een
synthetische afspraak, één bevestiging, een tweede ja, daarna direct een weervraag.
Een API-fout mag nooit als geslaagde afspraak worden gemeld.

Bij tunnelproblemen: controleer Taakplanner → JARVIS-OracleLink, de SSH-hostsleutel,
poort 22 en Oracle `journalctl -u ssh`. Bij HTTPS-problemen: controleer op Oracle
`systemctl status caddy` en `journalctl -u caddy`, DNS en ingress 80/443. Open nooit
11434, 18765 of 8765 publiek. Het certificaat wordt automatisch vernieuwd.
Bij ontbrekend geluid: controleer de gekozen uitgang en spraakruntime op het apparaat.

## Updates, back-ups en herstel

Pak een nieuwe vertrouwde ZIP uit in een aparte map. Bewerk geen manifest.

```powershell
.\BACKUP.ps1
.\UPDATE.ps1 -Package C:\Installatie\Nieuwe-JARVIS-MiniPC
.\UPDATE.ps1 -Package C:\Installatie\Nieuwe-JARVIS-MiniPC -Rollback
.\RESTORE.ps1 -Archive C:\ProgramData\JARVIS\backups\BESTAND.enc -KeyFile C:\ProgramData\JARVIS\secrets\backup.bin
```

Er wordt dagelijks om 03:00 een versleutelde back-up gemaakt via `JARVIS-Backup`.
Controleer vrije schijfruimte; bestaande back-ups worden niet stilzwijgend verwijderd.

Updates bereiden dependencies vooraf voor, bewaren een versleutelde back-up,
wisselen de release en controleren gezondheid. Bij mislukte start worden vorige
code én de database van vóór de update teruggezet; de mislukte database blijft
bewaard. Handmatige rollback wisselt alleen code en vereist een compatibel schema;
gebruik RESTORE wanneer ook het databaseschema moet worden teruggezet.
Herstel bewaart de oude database/configuratie onder een herstelnaam. In het
herstelde exemplaar worden oude sessies ingetrokken en open taken gepauzeerd,
zodat een verzonden bericht of andere actie niet door de back-up opnieuw loopt.
Meld uw apparaten opnieuw aan en beoordeel open taken voordat u die hervat.
Bewaar back-ups en hun sleutel afzonderlijk en beveiligd. DPAPI-sleutels zijn
computergebonden (de nieuw aangemaakte machine-DPAPI-sleutels); voor verhuizen gebruikt u de portable procedure.

`UNINSTALL.ps1` verwijdert uitsluitend automatische taken. Code en persoonlijke
gegevens blijven behouden. Er bestaat geen stilzwijgende gegevensverwijdering.

## Grenzen van verificatie

De mini-pc was tijdens de ontwikkeling niet beschikbaar. Geïsoleerde tests op de
ontwikkeldesktop bewijzen geen werking van uw mini-pc, BIOS, slaapstand of accounts.
Volg na installatie bovenstaande controle. Zonder geconfigureerde accounts,
Home Assistant of oproepkanaal kunnen die externe functies niet volledig worden getest.
