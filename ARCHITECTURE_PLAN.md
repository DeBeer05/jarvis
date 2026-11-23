# Architectuurplan — Windows-client en server

## Actuele uitbreiding: fase 7

server/automation is de centrale engine binnen dezelfde FastAPI-lifespan en
SQLite-schema 4. Transactionele claims, opaque approvals, gesloten registry,
state/PKCE en Windows DPAPI scheiden modelvoorstellen, gebruikersrechten en
externe gevolgen. Bestaande AI-router, auth, Windows- en Android-clients worden
hergebruikt. De scheduler doet begrensde lokale checks; providerreads alleen
voor expliciet ingediende taken. Geen nieuwe zware infrastructuur.
Zie docs/AUTOMATION_ARCHITECTURE.md en docs/AUTOMATION_SECURITY.md.
**Actuele fasegrens: stop na fase 7.** Oudere fasegrenzen hieronder zijn historie.

## Actuele uitbreiding: fase 6

Native Kotlin/Compose Android-app in android/, eigen build en MVVM/Flow.
Hergebruikt bestaande chat/auth/pairing en centrale gesprekken. Nieuwe mobile-
spraakroutes verbinden via begrensde private pipes met de bestaande fase-5-
inferencehelper. Geen modellen op de telefoon, GUI-imports in server of extra
backend. Keystore-encryptie, Room-ciphertext en DataStore scheiden geheimen,
offlinecache en voorkeuren. Ontwikkeling via expliciete ADB reverse naar dezelfde
loopback:8765, geen publieke/LAN-binding. Zie docs/ANDROID_ARCHITECTURE.md.
**Actuele fasegrens: stop na fase 6.** De onderstaande secties zijn voorgeschiedenis.

## Actuele uitbreiding: fase 5

Dezelfde client heeft nu een lokaal spraakpaneel, sounddevice-capture/playback,
energie-/Silero-VAD, faster-whisper Nederlands en Piper-stemmen. Een afzonderlijke
inferencehelper gebruikt private pipes en een eigen geïsoleerde omgeving, zonder
extra GUI, backend, credentials of audio-endpoints. Capture/tekst/audioqueues zijn
begrensd; generatiecontrole en procesannulering beschermen tegen oude uitvoer.
De bestaande geauthenticeerde SSE-route en conversation_id behouden context.
Microfoon alleen na sessietoestemming. Zie docs/VOICE_ARCHITECTURE.md.
Experimentele Whisper-wakefrase, CPU-fallback en licht geheugenprofiel; geen XTTS,
spraakgestuurde barge-in/AEC of bewezen Nederlandse wake-modelkwaliteit.
**Actuele fasegrens: stop na fase 5, geen Android of mini-pc-deployment.**
De volgende secties beschrijven de eerder gerealiseerde fasen.

## Windows-client, fase 4

`desktop-client/jarvis_client` is een zelfstandig PySide6-Essentials-proces.
De bestaande upstream-PyQt6-app wordt niet geïmporteerd. Eenzelfde Qt-hoofdthread
beheert de UI; begrensde QRunnable-workers doen HTTP/SSE en leveren via QObject-
slots resultaten. ApiClient, ConnectionManager, WindowsVault en SettingsStore
scheiden protocol, reconnect, veilige opslag en niet-geheime instellingen.
Een QLockFile voorkomt concurrerende instanties met dezelfde refreshcredential.
QSystemTrayIcon levert systeemvak/meldingen, Startup alleen expliciete HKCU Run-
opt-in, LocalAgent uitsluitend een door de gebruiker toegestane system_info-demo.
De eerdere VoiceCapability-placeholder is in fase 5 vervangen door de spraakmodules.

Native desktoplogin gebruikt op gebruikersverzoek de bestaande eigenaarcredentials
via /api/v1/auth/desktop-login. Dezelfde Argon2id-/rate-limitservice geeft minimale
Windows-chat-/statusrechten, zonder beheerrechten. Refresh gaat naar Credential
Manager; de openbare installatie-UUID voorkomt dubbele apparaatregistraties.
De 30-daagse desktopsessie wordt na appherstart via tokenrotatie hersteld.
De bestaande S256-pairing blijft voor andere clients beschikbaar.
Twee zelfbeheerroutes laten een sessie alleen het eigen apparaat zien/intrekken.
Beheer van overige apparaten en wachtwoord blijven bij de eigenaarbrowser.
De server draait onafhankelijk op localhost:8765. Clientprofielen bereiden
HTTPS/remote voor zonder de server bloot te stellen. Portable build via PyInstaller
onedir, eigen omgeving/constraints en licentieverantwoording.

## Gerealiseerd in fase 3

`server/security/` scheidt schema, transactionele opslag, Argon2id-service,
default-deny ASGI-gate en HTTP-routes. Eén eigenaar wordt lokaal interactief
aangemaakt. Browserauthenticatie gebruikt HttpOnly-cookies plus gebonden CSRF;
native clients gebruiken opaque access-/refresh-tokens. Refreshrotatie, replay-
intrekking en absolute sessieduur leven serverzijdig in SQLite-schema 3.
Bestaande chatdata blijven behouden na voorafgaande pre-v3-back-up.

Apparaten hebben UUID/type/naam/trust/rechten en afzonderlijk intrekbare sessies.
RFC8628-gebaseerde pairing vereist eigenaarcodevergelijking, expliciete rechten
en een S256-clientbewijs. Geen beheerscopes voor gekoppelde clients; chat lezen,
schrijven en verwijderen zijn apart. Audit is begrensd en bevat geen credentials.
Een actieve generatie controleert sessie-intrekking ook tijdens het antwoorden.
De webchat, login en beveiligingspagina gebruiken alleen eigen statische assets.

De procescontrolstatus heeft een apart lokaal token; persoonlijke status vereist
status:read. Publieke health/ready onthullen geen chat of configuratie.
Argon2id is de enige nieuwe directe runtimeafhankelijkheid. Eén worker/loopback
en poort 8765 blijven behouden; TLS/Tailscale is uitsluitend gedocumenteerd voor
een latere opdracht. Geen client- of mini-pc-deployment.
Zie [authenticatie](docs/AUTHENTICATION.md), [pairing](docs/DEVICE_PAIRING.md),
[beveiliging](docs/SECURITY.md) en [testverslag](docs/PHASE_3_TEST_REPORT.md).
**Huidige fasegrens: STOP na fase 3.** De volgende secties zijn voorgeschiedenis
en ontwerp voor later, geen toestemming om nieuwe onderdelen te activeren.

## Gerealiseerd in fase 2

`server/ai/` bevat de centrale tekst-router en adapters voor het gedeelde
Mark-LVII-transport `providers/llm_openai.py`. De opt-in headlessmodus gebruikt
geen desktopconfig, GUI, audio of tools. Gemini, Groq en lokale Ollama ondersteunen
SSE-streaming; fallback gebeurt uitsluitend vóór eerste tekst.
`chat_service.py` begrenst context/concurrency/verzoeken, beheert annulering en
sluit providerverbindingen. `chat_store.py` bewaart gespreksbeurten in schema 2,
met back-up vóór migratie. `api/chat.py` ontsluit JSON/SSE, historie en providerstatus;
`static/` bevat de lichte webchat. Origin-/Host-/loopbackcontrole, CSP en
plaintext-weergave vormen de lokale browsergrens. Geen AI-acties worden uitgevoerd.

Profielen begrenzen JARVIS-belasting; ze configureren geen Ollama-RAM/GPU/context.
Alleen desktop-development is lokaal actief. Externe clients/mini-pc zijn toekomstig
werk. Details: [AI-engine](docs/AI_ENGINE.md), [API](docs/CHAT_API.md),
[testverslag](docs/PHASE_2_TEST_REPORT.md). Live modelacceptatie is nog open.
De fase-1-metingen hieronder zijn historische nulmetingen, geen fase-2-benchmark.


## Gerealiseerd in fase 1

De lokale serverbasis in `server/` is nu geïmplementeerd met FastAPI/Uvicorn,
één worker, uitsluitend 127.0.0.1, lifespan-beheer, centrale .env-config,
health/ready/status en SQLite-schema versie 1. Er worden geen bestaande GUI,
cloudhost, pluginworkers, AI-providers of routines geïmporteerd/geactiveerd.
De bestaande netwerkservers zijn onderzocht: dashboard bindt op alle
netwerkinterfaces; core/cloud start ook Telegram/taken/routines en deploycode.
Die behouden hun oorspronkelijke functie en blijven buiten deze lokale basis.

Nieuwe grenzen: `server/config.py` voor configuratie, `database.py` voor korte
SQLite-verbindingen/migraties, `logging_config.py` voor roterende JSON-logs,
`app.py`/`api/` voor lifespan en routers, `control.py` voor lokaal procesbeheer.
Status is tot loopback beperkt; shutdown vereist een apart lokaal controletoken.
Geen publieke authenticatie/deployment ontwerpen via deze lokale toegang.

Gemeten op de ontwikkelwerkplek: 46,90 MiB working set, 34,70 MiB private memory,
844,2 ms processtart tot waargenomen gereedmelding en 1141 ms inclusief Windows-
startscript. Korte idleproef van 3,013 s gaf 0,000% op één-kernschaal; dit is een
momentopname, geen garantie voor de uiteindelijke 8-GB-mini-pc. Details en grenzen:
[docs/HEADLESS_SERVER.md](docs/HEADLESS_SERVER.md).
Onderstaande onderdelen blijven plannen voor latere expliciete opdrachten.

## Doel en grenzen

Een persoonlijke, niet-commerciële JARVIS-assistent op een Windows-mini-pc met
8 GB RAM, met een Windows Desktop Client en een toekomstige Android-app.
Mark-LVII is de bestaande basis; fase 0 bouwt of activeert geen onderdelen.
Onderstaande keuzes zijn voorstellen voor latere bespreking en meting.

## Hybride AI en beperkte hardware

Lichte lokale verwerking voor bediening, beleidscontrole, taakstatus en caching.
Zware redenering of multimodale verzoeken via een instelbare cloudprovider met
expliciete dataminimalisatie, kostenlimieten en time-outs. Hergebruik van
`providers/` en `core/` eerst beoordelen. Offline-modellen alleen na RAM-/CPU-
metingen en een nieuwe opdracht; geen aanname dat een groot LLM binnen 8 GB past.
Voorgesteld uitgangspunt: één zware taak tegelijk, begrensde wachtrij/cache,
geen model op voorhand resident en voldoende ruimte voor Windows en de GUI.
Haalbaarheid, latency, energiegebruik en geheugenverbruik zijn nog onbewezen.

## Componentgrenzen

- Windows-client: bestaande Qt-UI in `gui/` als uitgangspunt; bediening, duidelijke
  toestemmingen, microfoonstatus, taakstatus en herstelbare fouten.
- Serverlaag: toekomstige geauthenticeerde interface en taakcoördinatie. Eerst
  het bestaande `dashboard/` beoordelen; geen tweede server zonder onderbouwing.
- Android-app: toekomstige dunne client voor taken, status en notificaties;
  geen providergeheimen opnemen in een APK.
- Integraties: afzonderlijke adapters met minimale rechten; tokens serverzijdig
  in een OS-secretstore bewaren, buiten Git, logs en mobiele builds.

## Externe toegang

Standaard uit en lokaal begrensd. Voorstel voor later: private VPN of beoordeelde
tunnel met TLS, sterke apparaatauthenticatie, intrekbare sessies, rate limits en
auditinformatie zonder inhoudelijke persoonsgegevens. Geen open port forwarding.
Het bestaande dashboard is niet automatisch goedgekeurd voor internetpublicatie.
Geen service, certificaat, firewallregel of deployment aangemaakt in fase 0.

## Geplande koppelingen

| Onderdeel | Ontwerp voor later |
| --- | --- |
| Agenda en Gmail | OAuth met minimale scopes; lezen en schrijven scheiden; verzending bevestigen |
| Berichtenintegraties | Officiële ondersteunde APIs/voorwaarden beoordelen; per ontvanger toestemming en zichtbare status |
| Internetbellen | VoIP/SIP-provider, kosten, identiteit en expliciete belbevestiging eerst uitwerken |
| Zelfstandige automatiseringen | Duurzame taakstatus, beperkte rechten, herhaalveiligheid, retries met limiet, noodstop en stille uren |

Geen Google-account, berichtenaccount of telefoniedienst gekoppeld. De bestaande
upstreammogelijkheden zijn hiermee niet getest, geactiveerd of veilig verklaard.
Bij autonome acties onderscheid maken tussen lezen, omkeerbare acties en acties
zoals verzenden/bellen/verwijderen die afzonderlijke toestemming vereisen.

## Kwaliteit en beslismomenten

Latere tests: unit-/contracttests per adapter, Qt-threadgrenzen, mobiele
authenticatie, autorisatie, foutpaden, taakherstel en 8-GB-belasting. Geen echte
persoonsgegevens in fixtures. Logging maskeert tokens en standaard geen inhoud.
Voor ontwikkeling nog besluiten: protocol, packaging, databewaring, spraakstack,
providerbudget en client-/serverversies. Geen technologie vastzetten via installatie
of applicatiecode in fase 0.
