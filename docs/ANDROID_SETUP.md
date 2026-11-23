# Android-app installeren en gebruiken

Fase 7 levert .local/android-build/JARVIS-Android-0.7.0-debug.apk. Installeer die
met dezelfde USB/ADB-stappen hieronder. Automatiseringen vereist daarnaast een
expliciete eigenaargrant; zie WORKFLOW_ENGINE.md en CALENDAR_INTEGRATION.md.

De native app staat in `C:\Users\beren\Desktop\J.A.R.V.I.S\android`.
De backend blijft op je ontwikkeldesktop, **127.0.0.1:8765**.
Op Android betekent 127.0.0.1 normaal de telefoon zelf. Daarom gebruiken we in
deze fase een expliciete USB/ADB-tunnel; er hoeft geen netwerkpoort open.

De nieuwe servercode moet eenmalig worden geactiveerd. De automatische controle
blokkeerde de agent bij de gecombineerde herstart/emulatoropdracht. Voer daarom
zelf vanuit de projectroot de gecontroleerde herstart uit:

```powershell
powershell.exe -NoProfile -File scripts/Stop-Server.ps1
powershell.exe -NoProfile -File scripts/Start-Server.ps1 -Background
```

Je bestaande account en gesprekken blijven in dezelfde database.

## Telefoon via USB

1. Zet op je eigen telefoon ontwikkelaarsopties en USB-foutopsporing aan.
2. Verbind via USB en bevestig zelf de RSA-toestemming op de telefoon.
3. Vanuit de projectroot, met de lokaal geïnstalleerde SDK:

```powershell
.\.local\android-tools\sdk\platform-tools\adb.exe devices
.\.local\android-tools\sdk\platform-tools\adb.exe -s JOUW_APPARAAT_ID install -r android/app/build/outputs/apk/debug/app-debug.apk
.\.local\android-tools\sdk\platform-tools\adb.exe -s JOUW_APPARAAT_ID reverse tcp:8765 tcp:8765
powershell.exe -NoProfile -File scripts/Start-Server.ps1 -Background
```

Gebruik het echte ID uit `adb devices`; `emulator-5554` is alleen de testemulator.
Open JARVIS op de telefoon en kies `http://127.0.0.1:8765` als ontwikkeladres.
De tunnel moet na een USB-/ADB-herstart zo nodig opnieuw worden ingesteld.
`adb reverse --remove tcp:8765` verwijdert alleen deze tunnel.

## Inloggen en koppelen

Voer je bestaande gebruikersnaam/wachtwoord in bij Inloggen. Het wachtwoord wordt
direct uit het invoerveld gewist en niet opgeslagen. Daarna verschijnt de
koppelcode. Je kunt ook rechtstreeks een koppelcode aanvragen zonder het
wachtwoord op Android in te voeren.

Open **op je computer** de bestaande beveiligingspagina:
<http://127.0.0.1:8765/security>. Log zelf in, vergelijk de code, controleer naam,
apparaattype Android en chat-/statusrechten en keur het verzoek goed.
De Android-app rondt de koppeling automatisch af. Refresh wordt versleuteld via
Android Keystore opgeslagen. Na herstart volgt veilig sessieherstel.
De bestaande standaard-pairingsessie verloopt uiterlijk na zeven dagen; daarna
is opnieuw koppelen nodig. Intrekken kan in Account of in de eigenaarinterface.

## Chat en spraak

Chat gebruikt dezelfde centrale gesprekken als Windows/web. Selecteer eventueel
Ollama voor lokale AI. Open bestaande gesprekken via Gesprekken; verwijderen
vraagt bevestiging en geldt ook op je andere apparaten. Antwoorden kun je met
de Android-tekstselectie kopiëren. Bij uitval wordt geen vraag opnieuw verzonden.

Open Spraak, tik **Start luisteren** en geef zelf Android-microfoontoestemming.
Spreek Nederlands; stilte of Opname afronden verwerkt de opname. De status en
niveaubalk tonen luisteren/geluid/verwerking; het transcript toont wat is verstaan.
De bestaande server verwerkt audio met Whisper Small en antwoordt met Piper
Ronnie. Er zijn geen zware modellen op de telefoon nodig.
**Stop alles** stopt uitvoer en lopend antwoord; een nieuwe opname kan daarna
starten. Instellingen bevatten input/output, spreeksnelheid en spraakuitvoer.
Bluetooth gebruikt voorlopig de Android-systeemroute; geen achtergrond-wakeword.
Nederlands is standaard. De optionele Engelse instelling vertaalt de navigatie;
formulieren en spraak zijn in deze versie Nederlands.

## Meldingen en bereikbaarheid

Meldingen: geef Android-notificatierechten, kies categorieën en gebruik Test voor
een generieke lokale voorbeeldmelding. FCM is optioneel en zonder eigen Firebase-
configuratie niet actief. Zie ANDROID_NOTIFICATIONS.md.

Voor wifi of later gebruik zonder handmatige VPN is een vertrouwde HTTPS-gateway
nodig. Die is **niet gepubliceerd of ingericht** in fase 6. Release accepteert
uitsluitend HTTPS; debug laat HTTP alleen op 127.0.0.1, localhost en 10.0.2.2 toe.
10.0.2.2 alleen gebruiken als de backend bewust passende Host-toegang heeft;
de standaard ADB-tunnel vermijdt die aanpassing en behoudt loopbackbeveiliging.
Installeer geen TLS-bypass of onbekend certificaat om dit te omzeilen.

Bij offline: controleer server, USB/ADB en adres; tik de verbindingsstatus aan
voor een controle. Bij ingetrokken/verlopen sessie opnieuw koppelen. Bij audio-
fouten controleer Android-permissie en aangesloten apparaat, en Whisper/Piper op
de server. Deel nooit wachtwoorden, tokens, API-sleutels of persoonlijke logs.
