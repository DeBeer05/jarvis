# Fase-4-testverslag — 23 november 2026

Uitgangspunt develop 19f3e27, branch feature/windows-desktop-client. De gebruiker
heeft inmiddels ook fase 5 opgedragen; het bestaande fase-4-werk wordt als basis
behouden en beoordeeld, niet stilzwijgend als eerder afgerond aangenomen.

Uitgevoerd op Windows/Python 3.12.10:

- 156 oorspronkelijke servertests geslaagd vóór clientwerk.
- 159 servertests geslaagd inclusief eigen-apparaatstatus/intrekking en echte
  native TCP-proef; één bekende Starlette/httpx-deprecatiewaarschuwing.
- 34 clienttests geslaagd: initialisatie, instellingen, veilige origins, S256-
  pairing/polling, logout/revoke, refresh/concurrentie/onzekere uitkomst, historie/
  streamingcontract, authenticatie, notificatielimiet, lokale rechten, UI/tray/
  afsluiten, herverbinding en main-thread-callbacks.
- Echte Windows Credential Manager roundtrip met unieke synthetische target,
  daarna opgeschoond; persoonlijke credentials niet gelezen.
- Echte TLS-handshake tegen een tijdelijk zelfondertekend certificaat geweigerd
  vóór enige HTTP-/tokenuitwisseling. Geen TLS-disableoptie.
- Echte tijdelijke TCP-server met de werkelijke native ApiClient: eigenaarlogin,
  pairinggoedkeuring, chat/SSE, historie, refresh, eigen gesprek verwijderen en
  eigen apparaat intrekken. Synthetische gegevens/providers; geen kosten/echte data.
- Bronclient zichtbaar gestart en Account-scherm visueel gecontroleerd; geen
  microfoon geopend. De werkelijke eigenaarpairing wordt afzonderlijk door de
  gebruiker gedaan; dat is geen geautomatiseerde toegangsovername.
- Portable onedir-build succesvol gemaakt: 225 bestanden, circa 148 MB bij de
  eerste build. Bronrookproef: echt Qt-venster, 6 pagina's, netwerk uit, tray aanwezig.
  De definitieve executable krijgt dezelfde rookproef na laatste bronwijzigingen.
- Lokale portable proef vond build-PATH-vervuiling: een ICU-DLL van externe
  PDF-tools kwam onterecht in de build en miste Qt's vereiste exports, terwijl
  de schone CI-runner wel slaagde. Buildscript isoleert nu zijn PATH en gebruikt
  Qt's coherente gepinde CRT-set in _internal.
  Geen Windows-systeembestanden of global runtime-installatie aangepast.
  De herbouwde portable executable start nu ook lokaal: Qt-venster, 6 pagina's,
  geen netwerk in de rookproef, zelfstandig afgesloten met exitcode 0.
- Pip check en dependency-audit clientomgeving zonder bekende kwetsbaarheden.
  Bandit: 0 bevindingen, geen onderdrukking. Index-/Gitleaks-/repository-/whitespace-
  controles geslaagd. Echte CI wordt vóór merge gecontroleerd.

Tests gebruiken mocks waar hardware/OS-notificatiepresentatie onzeker is.
Een echte native OS-toast kan door Focus Assist verborgen worden; showMessage
en de lokale meldingenlijst zijn apart. Autostartregistratie wordt niet zonder
gebruikerskeuze geactiveerd. De optionele English-keuze vertaalt de navigatie;
volledige lokalisatie is geen claim van deze oplevering.

Geen remote server, Funnel/VPN, firewallwijziging, volledige spraak, Android,
agenda-/berichtintegraties, AI-shellcommando's of mini-pc-deployment in fase 4.
Fase 5 bouwt de apart opgedragen voice-pipeline bovenop deze client.
