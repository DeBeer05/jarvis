# Architectuurreview — JARVIS-ervaring

Onderzocht op 25 november 2026, vóór de functionele wijzigingen op
`feature/jarvis-experience-overhaul`. Dit is een codeanalyse; aanwezigheid van
code bewijst geen natuurlijke gesprekken of geslaagde hardwareacceptatie.

## Bestaande onderdelen en grenzen

| Verantwoordelijkheid | Bestaande implementatie | Beoordeling |
|---|---|---|
| Backend/compositie | `server/app.py`, `server/database.py` | Eén FastAPI op 8765, SQLite schema 7, gedeelde managers; behouden. |
| Gesprek | `server/chat_service.py`, `server/natural/conversation.py` | Historie, SSE, annulering, finalisatie, leases/epochs en 14 toestanden bestaan. |
| Context | `server/natural/context.py`, `private_context.py` | Begrensde complete beurtparen, lokale bronnotities en tijdelijke privécontext; geen volledige database per call. |
| Geheugen | `server/natural/memory.py`, `preferences.py`, `contacts.py` | FTS5, revisies, categorieën, vergeten, toestemming en contacten bestaan. Algemene semantische/episodische terugvindbaarheid is beperkt. |
| AI | `server/ai/router.py`, `providers.py`, `policy.py` | Gedeeld Mark-LVII-transport, Gemini/Groq/Ollama, requestbeleid en fallback uitsluitend vóór zichtbare tekst. |
| Vaardigheden | `server/automation/chat.py`, `models.py`, `google.py` | Gesloten registry en Google-integraties. Kandidaatselectie en planner zijn te bepalend voor gewone gesprekken. |
| Rechten | `server/security/`, `automation/engine.py`, `chat_approval.py` | Sessies, actuele apparaatrechten, expliciete schrijfintentie en exacte eenmalige approval blijven serververantwoordelijkheid. |
| Taken/events | `automation/engine.py`, `reschedule.py`, `natural/tasks.py` | Scheduler, duurzame jobs, notificaties en opt-in mailopvolging; geen algemene autonome agent toevoegen. |
| Antwoorden | `natural/responses.py`, `personality.py` | Kanaalgebonden antwoordbeleid en brongebonden toolspraak bestaan; standaardinstructies zijn te vraaggericht. |
| Spraak | `server/mobile.py`, `natural/tts.py`, `providers/voice_pipe.py`, `speech_format.py` | Herbruikbare private inferencehelper, lokale STT, Supertonic/Piper, speech-SSE en cache; geen echte full-duplex audiostream. |
| Windows | `desktop-client/jarvis_client/voice/`, `natural_settings.py` | PySide6-hoofdthread, workers, adaptieve beurtwisseling, echo-referentie, annulering en vervolgmodus. Het gemelde focusprobleem is nog geen geslaagde fysieke acceptatie. |
| Android | `android/.../features/JarvisViewModel.kt`, `voice/`, `NaturalSettingsScreen.kt` | Compose/Flow, authenticated WAV/SSE, platform-AEC indien beschikbaar, lifecycle- en epochcontroles. Achtergrondluisteren is niet impliciet toegestaan. |
| Instellingen | `natural/settings.py`, `models.py`, beide clients | Centrale CAS/revisies en apparaatkeuze apart. Sommige voorkeuren geven modelaanwijzingen; ze garanderen geen modelgedrag. |
| Upstream | `main.py`, `gui/`, `core/`, `memory/`, `actions/`, `plugins/`, `dashboard/` | Aparte bestaande desktop/cloudstack; niet vervangen of importeren in headless server. Ook `android-app/` is geen tweede native fase-6-client. |
| Tests/Git | `tests/`, `desktop-client/tests/`, `android/.../test`, `.github/workflows/`, `scripts/` | Veel technische contracttests; geen bewijs dat de acht volledige gespreksscenario's subjectief slagen. |

## Vastgestelde oorzaken in de begincode

1. **Verouderde systeemgrens.** `config/jarvis-system-prompt.txt` zegt dat de
   versie alleen tekst kan en geen agenda/berichten/acties heeft. Dit botst met
   de feitelijke gesloten vaardigheden. Oplossing: onderscheid modelvoorstel,
   serveruitvoering en uitvoeringsbewijs, zonder algemene toolbevoegdheid te claimen.
2. **Onderwerp wordt toolkandidaat.** `AutomationChat.candidate()` gebruikt
   `TOPIC.search()`: een verhaal over een afspraak kan een plannercall veroorzaken.
   Een bestaande `read_question` maakt vrijwel iedere volgende zin kandidaat.
   `slot_answer()` kan een vrije onderwerpwisseling als titel of persoon behandelen.
3. **Gespreksterugval verliest context.** Bij `{"chat":true}` geeft `answer()`
   voor woorden als 'mijn'/'morgen' een vaste functie-uitleg. Anders volgt een
   afzonderlijke korte prompt zonder de gedeelde historie, instellingen en stijl.
   `stream()` buffert dat antwoord in plaats van normale tokenstreaming.
4. **Stijl verschilt per kanaal.** `ContextManager.build()` voegt `describe()`
   alleen voor voice toe. De basis en antwoordprompt sturen ook verhalen steeds
   richting 'direct antwoord'. Alleen het classic_butler-profiel heeft daar een
   expliciete stijlzin; andere profielwaarden bereiken tekst minder volledig.
5. **Dubbele selectie.** `ChatService.events()` roept `candidate()` nogmaals aan
   voor de speechwrapper. Die selectie leest ook taakgeheugen. Eén routebeslissing
   per beurt volstaat.
6. **Gespreks- en taakcontext zijn verschillend.** De planner krijgt huidige
   instructie en opgeslagen toolreferenties, maar niet automatisch de gewone
   gespreksbeurten. Algemene verwijzingen uit een informeel gesprek zijn daardoor
   niet universeel opgelost. Context is nooit nieuwe toestemming.
7. **Samenvatten is niet overal actief.** Gewone tekst gaat rechtstreeks door de
   router; voice splitst zinnen. Toolspraak wordt apart ingekort; langere historie
   wordt lokaal extractief samengevat. Dat is niet hetzelfde als elke gebruikerszin
   door een samenvattingsmodel sturen. Wel kan verkeerde routing ongewenste
   toolspraak/standaarduitleg veroorzaken.
8. **Schaal en latency.** De planner kan drie modelrondes uitvoeren en vrij lange
   schemas/instructies krijgen. Qwen2.5:3B ontvangt dus soms een moeilijkere taak
   dan een gewoon gesprek. Voorafgaande rapporten melden koude providerdeadline
   en TTS-verschillen; deze review bewijst geen nieuwe end-to-end audiolatency.
9. **Werkelijke Ollama-context wijkt af.** De echte eerste 20/50-beurtproef
   gebruikte Qwen2.5:3B. `/api/ps` rapporteerde 4096 tokens runtimecontext, terwijl
   de server 6000 inputtokens plus output kon aanbieden. Ook met het beginonderwerp
   aantoonbaar in de servercontext miste het model de laatste terugverwijzing.
   Dit bewijst een configuratiemismatch; het bewijst niet dat iedere herhaling
   daardoor wordt veroorzaakt. Daarom is de bestaande transportklasse uitgebreid
   met een headless opt-in voor native `/api/chat` en `options.num_ctx`, inclusief
   input/output/rolreserve. Desktop- en clouddefaults blijven hetzelfde.

## Gap analysis

Status: **W** = technisch getest/werkend binnen genoemd bewijs, **O** = bestaand
maar onvoldoende, **D** = gedeeltelijk, **N** = niet geïmplementeerd,
**E** = externe beperking, **T** = nog niet daadwerkelijk geaccepteerd.

| Gewenste ervaring | Huidige werking/gap en technische oorzaak | Status | Verbetering/prioriteit | Afhankelijkheden en bewijs |
|---|---|---|---|---|
| Vrij praten, twintig beurten | Gewone router bestaat; onderwerpwoorden leiden naar planner | O | P0: gesprek als standaard; request-gating | A, regressie zonder plannercalls; menselijke beoordeling apart |
| Onderwerp wisselen tijdens taak | Open leesvraag blijft kandidaatschap afdwingen | O | P0: alleen actuele, passende vervolginvoer | B/C; taak bewaren zonder nieuwe actie |
| Eén persoonlijkheid | Tekst mist volledige stijlcontext, terugval heeft aparte prompt | O | P0: gedeelde context/antwoordroute | A/G, beide kanalen, ingestelde aanspreekvorm |
| Verwijzingen zonder herhalen | Gevalideerde toolreferenties bestaan; vrije gesprek-naar-taakreferenties beperkt | D | P1: contextbewuste planning, één vraag bij ambiguïteit | B/C; geen verzonnen ID of impliciete approval |
| Vijftig beurten | Contextbudget/40 recente beurten en extractieve notities | D/T | P1: testen wat werkelijk in context blijft | H; bronnotities zijn geen volledig episodisch geheugen |
| Onderbreken/zelfcorrectie | Epoch/cancel/AEC-guards bestaan | D/T | P1: fysieke interruptie-/focusproef | D, zichtbare audiostop en taakcontrole |
| Stiltes/automatisch luisteren | Adaptieve heuristiek, VAD, ingestelde vervolgmodus | D/T | P1: echte spraak/denkpauses beoordelen | Windows/Android met bestaande consent |
| Lage latency | SSE en geladen helper; plannerbuffer en koude modelstart kosten tijd | O/T | P1: gewone route streamen en meten | Eerste token ≠ eerste audio; CPU/GPU/RAM apart |
| Nederlandse mannenstem | Supertonic M1–M5 en Piper geïntegreerd, eerdere metingen | W/T | P1: huidige stemmen vergelijken in Voice Studio | Gebruikersluistertest; geen definitieve selectie automatisch |
| Korte én uitgebreide antwoorden | Modi/profielen bestaan; vraaggerichte prompt te algemeen | O | P0: situationeel reageren; geen universele samenvatting | Verhaal, grap, technisch en toolresultaat regressies |
| Kort/lang/taak/contactgeheugen | SQLite CRUD/FTS5, bronvergeten en adressen | W/D | P2: relevantie en contactrelaties verdiepen | Privacy, expiry, edit/delete, geen dump van database |
| Episodische herinneringen | Recente historie en extractieve notities; geen algemene semantische retriever | D | P2: eerst retrievalbewijs verzamelen | H en cross-conversation tests; geen extra vectorstack nu |
| Ollama/Gemini/modelwissel/offline | Centrale router/context en requestpolicy bestaan | W/T | P0: behoud Qwen2.5:3B en test contextwissel | E/G; mock bewijst geen echte Gemini-kwaliteit |
| Agenda plannen/conflicten | Bestaande CalendarRead/create/update, buffer-/conflictlogica | W/D | P2: contextovergang; echte reistijdbron ontbreekt | B, synthetische kalender; geen onbewezen vrije tijd |
| Mail/antwoorden opvolgen | Gevalideerde reads/drafts/send approval, opt-in followup | W/D | P2: integratie met gesprek verbeteren | Exacte preview/approval; geen echte accounttest |
| Autonomie binnen regels | Instellingen beperken actuele rechten; externe mutatie approval | W | P2: behouden, geen modelgrant | Negatieve securitytests en stale approval tests |
| Proactieve melding + gesprek | Scheduler/quiet hours/categorieën aanwezig, geen algemene eventintelligentie | D/T | P2: simulatie met broncontext | F; geen verzonnen urgentie of automatische oproep |
| Instellingen overal toepassen | Gedeeld schema, native schermen; modelwaarden zijn instructies | D | P0: tekststijl aansluiten; verdere runtime-audit | Settingscontract/Windows/Android regressie |
| Edge/XTTS | Geen huidige runtime; online/extra dependency/licentievragen | N/E | P3: onderzoek behouden, niet stilzwijgend installeren | Zie TTS_PROVIDERS; consent/download nodig |
| WhatsApp/Signal/SMS/nieuws | Geen betrouwbare gesloten integraties in huidige registry | N/E | Roadmap | Platform/rechten/bronkeuze vóór implementatie |
| Telefonie/24×7/mini-pc | Geen fase-8-calls/deployment; mini-pc-CPU onbekend | N/T | Toekomstig, buiten deze uitvoering | Aparte fase, FCM-config, WebRTC/HTTPS, hardwaretest |

## Git/eigendom

`origin/develop` is opgehaald en lokaal actueel. De benodigde fase-7.5-code staat
nog in PR25/PR26, niet in develop. De nieuwe branch bouwt daarom voort op de
bestaande PR26-head `3643cb0`; geen ontbrekende implementatie vanaf develop
namaken. De standaardhelper weigert de twee bestaande mailwijzigingen. Die zijn
inhoudelijk gelezen en blijven ongestaged/ongewijzigd; er is geen stash/reset.
Een afhankelijke PR maakt de eigen diff reviewbaar. Geen merge voordat basis,
inhoudelijke review en vereiste CI werkelijk zijn geslaagd.

## Externe bronnen en besluit

Primaire documentatie opnieuw bekeken op 25 november 2026:
[Ollama Chat](https://docs.ollama.com/api/chat),
[Ollama OpenAI-compatibiliteit](https://docs.ollama.com/api/openai-compatibility),
[Supertonic 3 modelkaart](https://huggingface.co/Supertone/supertonic-3),
[Piper](https://github.com/OHF-Voice/piper1-gpl),
[Edge-TTS repository](https://github.com/rany2/edge-tts),
[XTTS-v2 modelkaart](https://huggingface.co/coqui/XTTS-v2).
Ollama ondersteunt chatrollen/historie. De beginversie gebruikte het
OpenAI-compatibele chattransport, dat geen requestparameter voor contextgrootte
heeft. Na de echte mismatchmeting gebruikt uitsluitend de headless Ollama-route
de native opt-in in hetzelfde gedeelde transport. Er is geen tweede AI-router.
Supertonic/Piper blijven de bestaande lokale kandidaten. Edge is online en
XTTS vraagt een andere runtime/modellicentie; geen installatie of benchmark
van afwezige providers en geen stemkeuze zonder luisteren.

Het besluit is incrementeel: verbeter de bestaande selectie, context en
antwoordroute. Geen tweede Conversation/Memory/Event-engine, database,
framework, modelwissel of veiligheidsversoepeling.
