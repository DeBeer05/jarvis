# Native Android-architectuur — fase 6

Project: `android/`, Kotlin, Compose/Material 3, MVVM met ViewModel/StateFlow,
Coroutines en expliciete dependency injection via AppGraph. Eén appmodule met
aparte packages core, data, features, voice, notifications en domain.
Geen tweede AI-backend en geen Whisper-/XTTS-modellen op Android.

- JarvisApi: OkHttp, exacte vertrouwde origins, TLS-validatie, redirectverbod,
  geserialiseerde refreshrotatie, begrensde JSON/WAV/SSE en geen automatische
  herverzending van chatmutaties. Credentials zijn per origin gescheiden.
- ConnectionManager: healthcontrole op service-identiteit, sessiecontrole,
  foreground-/netwerkcallbacks en exponentiële backoff. Geen achtergrondpolling.
- SecretVault: Android Keystore AES-GCM met origin als authenticated data;
  uitsluitend ciphertext in appprivate SharedPreferences. Access alleen in RAM.
- ConversationCache: Room bewaart uitsluitend versleutelde metadata/gesprekken.
  Offline historie alleen met eerder bewaarde credential; verwijderen na logout,
  401 en expliciete verwijdering. Geen schijnantwoorden bij offlinegebruik.
- SettingsStore: DataStore voor niet-geheime voorkeuren.
- AudioClient: foreground AudioRecord PCM16/16 kHz, maximaal 60 seconden,
  energie-/stiltepoort, AudioTrack, audiofocus, generatie-/jobannulering. Geen
  microfoon zonder runtimepermission en expliciete PTT. Geen audiofiles.
- Notifications: vier echte Android-kanalen, generieke private payloads,
  optionele FirebaseMessaging en WorkManager voor begrensde registratiepogingen.
- FutureCallTransport/CallState: alleen interfaces/modellen. Alleen urgent kan
  later automatisch ringwaardig zijn. Geen belknop, WebRTC, Telecom of TURN/STUN.

## Hergebruik bestaande backend

Chat, geschiedenis, SSE, annulering, minimale scopes, S256-pairing en tokenrotatie
komen uit de bestaande API's. Nieuw: `/api/v1/auth/android-login` controleert de
eigenaarcredentials via dezelfde Argon2id/rate-limitservice en start uitsluitend
een pairingverzoek. Pas eigenaargoedkeuring plus S256-bewijs leveren een Android-
apparaatsessie. Windows-login blijft ongewijzigd.

`server/mobile.py` voegt toe: authenticated WAV-transcriptie, zins-TTS en beperkte
pushregistratie. Bestaande chat:write/read en status:read zijn expliciet vereist.
De centrale SpeechBridge roept dezelfde fase-5-inferencehelper aan via private
pipes, in de bestaande aparte voice-venv. De servervenv importeert geen GUI of
zware inferencebibliotheken. Verwerking is geserialiseerd en begrensd, inclusief
bodylimiet vóór parsing en hercontrole van de sessie na inference.

Chat blijft SSE over HTTP(S), geen verzonnen WebSocket-route. WSS is een latere
transportuitbreiding indien de server die krijgt. Serveradres wisselen is nu
expliciet; credentials blijven aan de juiste origin gebonden. Automatische
LAN/externe failover wordt niet geactiveerd zolang er geen vertrouwde gateway is.
De ontwikkelserver blijft uitsluitend loopback:8765; de telefoon gebruikt ADB
reverse. Geen publieke toegang, firewall-/routerwijziging of mini-pc-deployment.

## Lifecycle en grenzen

Bij onStop worden opname, playback en lopende chat gestopt en polling afgemeld.
Op de voorgrond volgt herverbinden. Instellingen en ciphertext blijven bewaard;
geen wachtwoord/pairingverifier in SavedState of logs. Generaties verhinderen
dat late responses na uitloggen/profielwissel weer persoonlijke inhoud tonen.
Een geïnitialiseerde en geconfigureerde FCM-service kan later het proces wekken;
zonder Firebase zijn uitsluitend lokale testmeldingen beschikbaar.

Wake word op de achtergrond is niet actief: Android beperkt achtergrondstart van
microfoon-foregroundservices en vereist zichtbaar gebruik/toestemming. PTT blijft
zelfstandig werken. Achtergrondmicrofoon, volledige internetoproepen en productie-
deployment behoren niet tot deze fase. Geen permanente foregroundservice.
