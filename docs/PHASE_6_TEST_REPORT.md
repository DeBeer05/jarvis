# Testverslag fase 6

Geïmplementeerd op feature/android-client vanaf develop a78257e (fase 5 / PR #16).
De native debug-APK bouwt en start echt op een Android-16/API-36-emulator met
WHPX op deze Windows-desktop. Eerste koude start gemeten: 6683 ms inclusief
emulator/debug-opstartbelasting; geen claim over snelheid op een echte telefoon.

Geïmplementeerd: Compose/Material3 en tien schermen, foreground-MVVM/Flow,
OkHttp/SSE, health/reconnect, ownerpairing na optionele wachtwoordcontrole,
Keystore-ciphertext/refresh, Room-versleuteling, DataStore, centrale gesprekken,
PTT/PCM-WAV naar bestaande Whisper/Piper-helper, AudioTrack/stop/audiofocus,
meldingskanalen en lokale testmeldingen, optionele FCM-registratieworker.

## Uitgevoerde verificatie

- Vijf JVM-tests: endpointvertrouwen/debuggrens, RFC7636-S256, complete zinnen /
  decimalen, WAV-formaat en backoff/toekomstige oproepcategorieën.
- Zes instrumented tests op de echte API-36-emulator: Keystore/AAD/ciphertext,
  DataStore/Room, echte TCP-login→ownerpairing→refresh→tweebeurtchat→SSE→historie→
  intrekking, lokale pushregistratie en kanalen, afgewezen self-signed TLS,
  Compose-navigatie, echte Piper/Whisper en Android AudioTrack/AudioRecord/stop.
- Debug- én unsigned releasebuild geslaagd; Android-lint **0 fouten**, acht
  niet-blokkerende versie-/stijlwaarschuwingen. Geen lintregels uitgeschakeld.
  Synchrone ciphertext-commit is bewust nodig voor duurzame refreshrotatie.
- Bestaande Windows-client: **74 tests geslaagd**. Server: oorspronkelijke 165
  regressies plus zeven mobile-auth/audio/pushgevallen, inclusief intrekking
  tijdens inference. Eén bestaande Starlette/httpx-testadapterwaarschuwing.
- Alle drie Pythonvenvs: pip check goed. Server-runtime-audit: nul bekende
  kwetsbaarheden. Bandit: zeven lage signalen, nul middel/hoge en geen suppressies;
  het gaat om bestaande best-effort audioabort en vaste eigen subprocess/
  taskkill-aanroepen zonder shell of modelgestuurde invoer.
- Repository-/whitespacecontroles geslaagd. Git-/CI-verificatie loopt via een
  eigen PR naar develop; geen main-wijziging of force-push.

De ADB-testtunnel is expliciet ingesteld vóór de laatste suite. Een eerdere
verdwenen tunnel is hersteld; testsessies worden per test gewist. De eigen
synthetische fixture is na testen gestopt. Hij gebruikte nooit de echte database
of providerkeys. De testgoedkeuringsroute bestaat alleen in dat testproces.

## Artefact en resterende activering

Installeerbaar artefact: `.local/android-build/JARVIS-Android-0.6.0-debug.apk`,
19.215.931 bytes. SHA256:
`0e91bc2f4a345727109437409a314d3e479c57f9fac98dc6db1f4da414f4aa78`.
Het standaard Gradle-artefact staat ook onder android/app/build/outputs/apk/debug.
Integratie via [PR #17](https://github.com/DeBeer05/jarvis/pull/17). De eerste CI
ontdekte een lege EOF-regel in de meegebundelde licentietekst en een ontbrekende
SDK-manager op de runner. Alleen EOF is genormaliseerd; de Linux-SDK wordt nu
zelf met vastgepinde download en SHA256 geïnstalleerd. De licentie-inhoud blijft
behouden. Merge uitsluitend na alle groene checks op de exacte laatste head.
Release is unsigned; er zijn geen persoonlijke signinggegevens aangeleverd.

De automatische goedkeuringscontrole blokkeerde de gecombineerde opdracht voor
herstart van de echte server en extra emulatorbediening met 'blocked by policy',
zonder nadere reden. Die opdracht is niet uitgevoerd. De APK is afzonderlijk
veilig klaargezet; de gebruiker moet de echte server gecontroleerd herstarten
om de nieuwe routes te activeren. Account en gesprekken worden niet gemigreerd
of gewist. Alle routeproeven zijn op een aparte echte tijdelijke server gedaan.

## Grenzen

Geen externe FCM-test/configuratie aanwezig: alleen lokale notificaties en
digestregistratie, geen externe bezorging geclaimd. Geen permanent wake word,
geen achtergrondmicrofoon, geen WSS-backend of automatische productie-failover,
geen WebRTC/Telecom-oproepen, geen publieke gateway of mini-pc-deployment.
Releasebuild is unsigned tenzij de eigenaar eigen signing configureert.
Audio is daadwerkelijk met de echte engines en Android-audio-API's verwerkt.
De emulator heeft geen hostmicrofoon ingeschakeld: AudioRecord-capture bevat
stilte, de aparte rondreis gebruikt synthetische Nederlandse spraak. Daarmee
wordt geen volledig zelf ingesproken PTT-gesprek of hoorbare kwaliteit op de
fysieke telefoon geclaimd. Die proef blijft bij installatie nodig.

## Handmatige telefoonacceptatie

Installeer debug-APK via ANDROID_SETUP. Bevestig zelf USB/Android-rechten en
eigenaarcode. Test twee chatbeurten met context, geschiedenis openen/verwijderen,
herstart/sessieherstel, PTT met Nederlandse spraak en Stop tijdens een lang
antwoord. Test schermrotatie, achtergrond/terugkeer, internet-/USB-uitval,
geweigerde microfoon/meldingen, apparaat loskoppelen, notificatiecategorieën en
intrekken. Vergelijk transcript en hoorbare spraak met de werkelijkheid.

Zonder deze fysieke proef wordt geen echte telefoon-/akoestische kwaliteit
geclaimd. Emulatorcompatibiliteit en synthetische audio zijn apart aantoonbaar.
Stop na fase 6; geen integraties/fase 7 of volledige oproepen/fase 8.
