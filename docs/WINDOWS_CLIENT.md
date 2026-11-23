# Windows-client — fasen 4–7

## Agenda, e-mail en rechten in 0.7.1

De bestaande app heeft nu leesbare agenda- en mailweergaven onder
**Automatiseringen**. Haal agenda's op, kies er één, kies Vandaag/Morgen/Komende
week of een periode en haal de afspraken op. E-mail toont maximaal vijf afzenders
en onderwerpen. Selecteer een bericht en klik expliciet op **Inhoud lezen**.
Geen bericht-ID's kopiëren, HTML of externe afbeeldingen laden. Oude antwoorden
worden genegeerd na een selectie-/sessiewissel of uitloggen. Gewone chat en spraak
gebruiken dezelfde servertools; de knop **via AI-chat / spraak** opent een voorbeeld
zonder een bestaand ongestuurd bericht te overschrijven.

Bij ontbrekende rechten: klik **Apparaatrechten instellen als eigenaar**. De browser
opent het huidige Windows-apparaat als geselecteerd voorstel. Log zo nodig zelf
in als eigenaar en controleer **Bekijken** en **Taken maken**. Klik zelf op
**Rechten instellen** en bevestig. Er wordt niets verleend door alleen de link
te openen. Gebruik daarna **Rechten vernieuwen** in Windows.

In dezelfde eigenaarinterface kun je je gekoppelde **Android** op naam kiezen
en afzonderlijk rechten geven. Goedkeuren en Accounts beheren zijn aparte keuzes;
deze worden niet automatisch aangezet. Geen nieuwe Google-koppeling of Android-APK
nodig voor de rechten. Android moet al door de eigenaar zijn gekoppeld. Open
daarna Automatiseringen opnieuw of stel je chat-/spraakvraag opnieuw.

De portable bundel staat na bouwen in `.local/client-build/dist/JARVIS/`;
het versiegebonden archief is `JARVIS-Windows-0.7.1-x64.zip`. De ontwikkelapp start
met de bestaande `scripts/Start-WindowsClient.ps1`. Logingegevens, profiel,
microfoonkeuze en Windows Credential Manager-sessie blijven behouden.

Spraak is toegevoegd in versie 0.5.0. Gebruik [VOICE_SETUP.md](VOICE_SETUP.md)
voor microfoontoestemming, PTT, Piper-stemmen en onderbreken. De onderstaande
account-/chat-/systeemvakbediening blijft gelden.

Deze afzonderlijke PySide6-app praat met de bestaande FastAPI-server; hij start
geen server, upstream-PyQt-app of AI-model. Standaard: http://127.0.0.1:8765.
Gebruik de volledige portable map, inclusief _internal en licenties.

## Starten

Vanuit de bestaande projectroot, Windows PowerShell 5.1:

```powershell
powershell.exe -NoProfile -File scripts/Start-Server.ps1 -Background
powershell.exe -NoProfile -File scripts/Start-WindowsClient.ps1
```

De bronclient gebruikt de geïsoleerde `.local/client-venv`. Op een nieuwe
ontwikkelmachine eerst `scripts/Install-WindowsClient.ps1` uitvoeren. De portable
app staat na bouwen in `.local/client-build/dist/JARVIS/JARVIS.exe` en vereist
geen geïnstalleerde Python. Client en server sluiten onafhankelijk af.

## Inloggen en ingelogd blijven

Open **Account**, vul je bestaande JARVIS-gebruikersnaam en wachtwoord in en
kies **Inloggen**. Goedkeuren in een browser is voor de desktopapp niet meer
nodig. Het wachtwoordveld is gemaskeerd en wordt direct na verzenden gewist.
Het wachtwoord wordt niet op schijf bewaard. De server controleert dezelfde
Argon2id-hash en inloglimiet als de webchat.

De app bewaart uitsluitend de refreshcredential in Windows Credential Manager.
Na volledig afsluiten/herstarten wordt de sessie automatisch hersteld, mits
automatisch verbinden aan staat. De desktopsessie is standaard maximaal 30
dagen geldig (`JARVIS_DESKTOP_SESSION_SECONDS=2592000`); een ongebruikte refresh-
credential verloopt standaard na 7 dagen. Regelmatig gebruik vernieuwt die
credential automatisch, tot de absolute sessiegrens. Na uitloggen, intrekking,
wachtwoordwijziging met sessie-intrekking of veilig verloop log je opnieuw in.

Na correcte eigenaarlogin: gesprekken lezen/schrijven/verwijderen en status
bekijken, zonder beheerrechten. De openbare installatie-UUID voorkomt steeds
nieuwe apparaatregistraties; de UUID zelf verleent geen toegang.
Wachtwoord wijzigen en andere apparaten
beheren gaat via **Account → Wachtwoord en eigenaarsessies beheren** in de bestaande
eigenaarbrowser. Dit hergebruikt de fase-3-beveiliging.

**Uitloggen** trekt alleen deze sessie in. **Apparaten → Deze apparaatkoppeling
intrekken** trekt de hele eigen apparaatregistratie in, na bevestiging. De
server accepteert hierbij geen ander apparaat als doel. Bij intrekking/verloop
wordt persoonlijke inhoud gewist uit de UI en moet je opnieuw inloggen.

## Chat en navigatie

**Chat** ondersteunt Enter om te versturen, Shift+Enter voor een nieuwe regel,
providerkeuze, zichtbare provider/modelmetadata, streaming en **Stop antwoord**.
**Nieuw gesprek** begint zonder oude context. In **Gesprekken** kun je historie
laden, meer laden, openen en — met expliciet recht en bevestiging — verwijderen.
De server blijft bron van waarheid; de client bewaart geen chathistoriebestand.

**Meldingen** toont maximaal 100 lokale statusmeldingen. Windows-traymeldingen
zijn instelbaar, worden per type beperkt en bevatten geen antwoordtekst.
Windows Focus Assist/OS-instellingen kunnen zichtbare meldingen onderdrukken.

## Instellingen en systeemvak

Instellingen worden zonder secrets bewaard onder `%LOCALAPPDATA%/JARVIS/Desktop`.
Kies serverorigin/profiel, automatisch verbinden, thema, meldingen, systeemvak,
provider en logniveau. HTTPS is verplicht buiten loopback; TLS-validatie kan niet
worden uitgezet. `auto` probeert alleen expliciet ingestelde origins en gebruikt
voor iedere origin afzonderlijke credentials. Een actief antwoord wordt niet
naar een andere server overgezet of automatisch opnieuw verstuurd.

De bestaande server is nog uitsluitend lokaal beschikbaar. Een extern profiel
bereidt de client voor; het opent geen firewall, tunnel, Funnel of remote backend.
De interface is Nederlands; de English-optie vertaalt voorlopig de hoofdnavigatie.
Logniveau wordt bij herstart toegepast.

**Start deze app bij Windows-aanmelding** staat standaard uit. Alleen opslaan
na jouw expliciete keuze verandert de eigen HKCU Run-waarde JARVISDesktop;
uitschakelen verwijdert die waarde. Geen administratorrechten of server-autostart.
Verplaats de portable map niet terwijl autostart naar die map verwijst.

Venster sluiten verbergt de app in het systeemvak als dat is ingeschakeld en
beschikbaar. Openen kan via de tray. **App afsluiten / Volledig afsluiten** stopt
ook netwerkwerk en verwijdert het trayicoon. Er kan maar één client per profiel
draaien; een tweede instantie verwijst naar het bestaande systeemvak.

## Diagnostiek en grenzen

Geen server? Start hem apart, controleer health/ready en het adres. Geen rechten?
Log opnieuw in met je eigenaargegevens als de sessie is verlopen of ingetrokken.
Een onzekere refreshpoging leidt veilig tot opnieuw inloggen, zodat een mogelijk
verbruikt token niet wordt herhaald.
Bij corrupte settings wordt het bestand behouden en volgt een duidelijke fout.
Logbestand: `%LOCALAPPDATA%/JARVIS/Desktop/client.log`, maximaal 3 × 256 KiB.

De lokale demonstratie **Systeeminformatie** vereist een expliciet aangevinkte
toestemming en toont alleen OS/architectuur/CPU-aantal lokaal. Er is geen shell-
executor en de AI kan deze actie niet activeren. Fase 4 opent geen microfoon;
volledige spraak is een afzonderlijk geautoriseerde fase 5.
