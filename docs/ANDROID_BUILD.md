# Android bouwen

Project: `C:\Users\beren\Desktop\J.A.R.V.I.S\android`.
Getest met JDK 17, AGP 9.5.0, Gradle 9.6.0, Kotlin/Compose-plugin 2.3.20,
Compose BOM 2026.09.00, compile SDK 37.2, target 36 en min 26.
Versies zijn vastgepind; Gradle-wrapper controleert de distributie-SHA256.
Compile SDK is hoger dan target om actuele AndroidX-API's te kunnen compileren,
zonder ongetest nieuw targetgedrag te claimen.

De SDK staat op deze desktop onder `.local/android-tools/sdk`. Maak bij een
nieuwe checkout de SDK klaar met scripts/Install-AndroidTools.ps1 (zie script-
help voor de expliciete SDK-licenseoptie). Android Studio met dezelfde SDK/JDK
kan ook. `android/local.properties` met sdk.dir blijft buiten Git.

```powershell
# Alleen bij een nieuwe installatie, na lezen van de SDK-voorwaarden:
powershell.exe -NoProfile -File scripts/Install-AndroidTools.ps1 -AcceptSdkLicenses
powershell.exe -NoProfile -File scripts/Build-Android.ps1
```

De tweede opdracht test/bouwt beide varianten en kopieert de debug-APK naar
`.local/android-build/JARVIS-Android-0.6.0-debug.apk` met SHA256-uitvoer.

Vanuit projectroot:

```powershell
cd android
.\gradlew.bat :app:assembleDebug
.\gradlew.bat :app:testDebugUnitTest :app:lintDebug
.\gradlew.bat :app:assembleRelease
```

Artefacten:

- `android/app/build/outputs/apk/debug/app-debug.apk` — installeerbare debug-APK.
- `android/app/build/outputs/apk/release/app-release-unsigned.apk` — geen eigen
  signing key beschikbaar; niet rechtstreeks installeerbaar als productie-release.

De app bevat geen servercredentials, persoonsgegevens, Whisper-/Piper-modellen
of releasekeystore. Er wordt geen Play Store-release gemaakt. Debugsigning is
ontwikkelsigning, geen productiesigning. Bewaar APK-hash en testverslag bij delen.

## Emulator/instrumented tests

De lokale API-36-emulator gebruikt WHPX; op Linux-CI kan KVM worden gebruikt.
Tests met een tijdelijke synthetische testserver staan in tests/android_test_server.py.
Die module wordt nooit door productie-startscripts geladen en weigert een gewone
datamap. Alleen de fixture heeft een testgoedkeuringsroute; echte accounts worden
niet aangepast. Zet voor deze tests ADB reverse naar de fixturepoort 8766.

```powershell
# Na starten van de expliciete synthetische fixture en emulator:
.\.local\android-tools\sdk\platform-tools\adb.exe -s emulator-5554 reverse tcp:8765 tcp:8766
cd android
.\gradlew.bat :app:connectedDebugAndroidTest
```

Instrumentatie met echte STT/TTS vereist de eerder toegestane modellen en voice-
venv op Windows. Er wordt nooit automatisch een model gedownload. Hostmicrofoon
blijft op de testemulator uit (geen -allow-host-audio); de opnameproef test het
Android-driverlifecycle met stilte. De aparte echte Piper→Whisper→AudioTrack-
proef gebruikt alleen synthetische Nederlandse spraak. Een fysieke telefoonproef
met eigen stem en hoorbare uitvoer blijft een aparte gebruikersacceptatie.
