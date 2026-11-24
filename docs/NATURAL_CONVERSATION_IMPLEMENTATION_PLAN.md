# Fase 7.5 — technisch implementatieplan

Status: inspectie uitgevoerd; implementatie gestart. Dit is geen voltooiingsrapport.
Opdracht: de volledige 50-delige fase-7.5-specificatie van 24 november 2026.

## Aangetroffen architectuur en hergebruik

- `server/app.py`: één FastAPI-lifespan, loopback:8765, auth, chat en scheduler.
- `server/database.py`: één SQLite-database, WAL, schema 4 en migratiebackups.
- `server/chat_service.py`/`chat_store.py`: centrale conversation_id, historie,
  begrensde SSE, één actieve beurt per gesprek, annulering en idempotente requests.
- `server/ai/router.py`: Gemini/Groq/Ollama, fallback vóór zichtbare output;
  `providers/llm_openai.py` blijft het bestaande teksttransport.
- `server/automation/`: gevalideerde tools, Gmail/Calendar, persistente taken,
  snapshots, eenmalige goedkeuringen, notificatieregels en onzekere resultaten.
- `desktop-client/jarvis_client/voice/`: eigen Qt-thread/workergrens, lokale
  persistent geladen inferencehelper, energie-VAD, wakefrase na transcriptie,
  zins-TTS, apparaatkeuze en korte vervolgmodus. Geen huidige audio-barge-in/AEC.
- `server/mobile.py`: beveiligde WAV/STT/TTS naar dezelfde inferencecode. Nu een
  nieuw proces per request: dit veroorzaakt onnodig herladen voor Android.
- `android/`: Compose, ViewModel/Flow, AudioRecord/AudioTrack, OkHttp/SSE,
  lifecycle-annulering, Keystore/Room/DataStore. Nu geen doorlopende audiomodus.
- Bestaande server gebruikt geen WebSockets. Die worden als optionele transport-
  uitbreiding toegevoegd; SSE en bestaande clients blijven werken.
- Upstream `memory/` en `core/tasks/` gebruiken JSON-bestanden en behoren tot de
  oorspronkelijke GUI/cloudapp. Niet importeren in de headless server en niet
  stilzwijgend migreren; ranking-/taakideeën hergebruiken binnen centrale SQLite.
- Instellingen zijn verspreid over .env, lokale Windows-settings/voice-settings,
  Android DataStore en automation_preferences. Nieuwe globale voorkeuren komen
  centraal; hardwaretoestemming, microfoon/luidspreker blijven per apparaat.

## Git en fasegrens

`feature/natural-conversation-engine` is vanaf actuele develop 436bb2b gemaakt.
De werkende chatgoedkeuring uit open PR #24 is als fast-forward-afhankelijkheid
op de featurebranch meegenomen (497ae2e); develop/main zijn niet omzeild/gemerged.
GitHub Actions was bij de vorige opdracht geblokkeerd met HTTP 422. Opnieuw
controleren vóór afronding; nooit groene CI of merge claimen zonder bewijs.
Geen fase 8, telefonie, mini-pc-migratie, publieke poort of nieuwe backend.

## Implementatievolgorde

1. Centrale fundering in `server/natural/`: strikte instellingenmodellen,
   categorie-/capabilityschema, schema-5-migratie, revision/CAS, autorisatie,
   import/export/reset, audit en veilige wijzigingen tijdens actieve gesprekken.
2. MemoryManager: gebruikersisolatie, FTS5, metadata/ranking, conflicten/expiry,
   expliciete gevoelige toestemming, CRUD/export/wissen, samenvattingen en
   invalidatie van afgeleide gegevens na vergeten. Geen externe vectorservice.
3. ContextManager en NaturalConversationManager: begrensde relevante context,
   persoonlijkheidsprofielen, alle gevraagde staten, leases/overdracht per apparaat,
   einde-/timeoutdetectie, taakreferenties en herstel na serverherstart.
4. Intent-/slotlaag boven bestaande tools: samengestelde intenties, Nederlandse
   datum/tijden, slotcorrecties, gerichte gecombineerde vragen, agenda-conflicten,
   persoon-/berichtverwijzingen, persistente onafgeronde plannen. Approval blijft
   gebonden aan het concrete voorstel; onderbreken van audio annuleert geen
   uitgevoerde of reeds geautoriseerde externe actie.
5. Spraak/transport: inferenceprocessen hergebruiken, getimede STT/AI/TTS,
   geauthenticeerde begrensde WebSocket-sessies, bestaande SSE behouden,
   adaptieve turn-taking en echo-bestendige barge-in via platform/lichte DSP.
   Geen zware modellen/downloads zonder vereiste toestemming.
6. Windows: categorisch instellingen- en geheugenpaneel, zoeken/dirty-state,
   validatie/sync/diagnostiek, natuurlijke spraaksessie, interruptie en testmodus.
7. Android: dezelfde instellingen/context/geheugen en sessieoverdracht,
   foreground-only continue opname, platform-AEC/noise suppression, barge-in en
   lifecycle-/netwerkherstel. Geen ongeoorloofde achtergrondmicrofoon.
8. Regressies, mock-/race-/security-/migratietests, daadwerkelijke builds en
   synthetische audio-/latency-/RAM-metingen. Echte microfoon-/telefoontests apart
   herkennen; niet als bewezen presenteren zonder uitvoering.
9. De veertien gevraagde architectuur-/gebruikers-/testdocumenten, README,
   roadmap, changelog, voortgang, PR en echte CI-status bijwerken.

## Beleid en ontwerpbeslissingen

- Globale gebruikersvoorkeuren veranderen geen auth, credentials, poort of
  hoogrisicoregels. Effectieve autonomie is de doorsnede van instellingen,
  actuele apparaatmachtigingen en verplichte approvals; geen privilege escalation.
- Persoonlijkheid/geheugen/toolresultaten zijn geen bron van nieuwe bevoegdheden.
  Ontvangen inhoud blijft onbetrouwbare data. Alleen eigen expliciete opdrachten
  autoriseren plannen; bewijs van uitgevoerde acties komt uit de engine.
- Geen ruwe audio in SQLite/logs. Geen gevoelige herinneringen automatisch.
  Geen automatische import van persoonlijke upstream-JSON. Offline-modus sluit
  cloudroutes uit, ook voor samenvattingen, planners en embeddings.
- Instellingen voor afwezige providers/modellen worden als niet beschikbaar
  getoond. Geen schijnschakelaars voor AEC, diarization, kostenplafonds of GPU-
  metingen die het platform niet werkelijk ondersteunt.
- Latency 1–3 s is een doel; koude modelstart, gemeten percentielen en hardware-
  beperkingen worden eerlijk gerapporteerd. 8-GB-geschiktheid blijft een inschatting.
- Alle 14 gevraagde statemachine-staten en de 13 categorieën krijgen een expliciet
  contract. Gesprekseigenaarschap staat los van blijvende taken/goedkeuringen.

## Validatie en voltooiing

Per onderdeel betekenisvolle deterministische tests en integratietests. Daarna
serverregressies (fase-7-baseline 255), Windows-tests/build, Android unit/lint/APK
en beschikbare instrumented tests. Synthetische externe integraties; geen echte
mail/agenda-mutaties om te testen. Afzonderlijke scenariohandleiding dekt alle
13 gevraagde hardware-/acceptatietests. Eindrapport bevat implementatie, bewijs,
metingen, grenzen, handmatige stappen en de daadwerkelijke fase-8-gereedheid.
