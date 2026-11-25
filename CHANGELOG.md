# Changelog

Wijzigingen van deze fork; oorspronkelijke geschiedenis en licentie blijven behouden.

## Unreleased

- Spraakstart kan bij een voldoende lange eerste clausule eerder beginnen;
  Windows/Android gebruiken gereed speech-materiaal zonder tweede zinsbuffer.
  Lange/oudere speech-events blijven begrensd en volledig beschikbaar.
- Maximaal één audioblok vooruit voorbereiden naast playback; uit bij barge-in
  voor STT-prioriteit. Stop/epochwissel laat oude voorbereide audio vervallen.
- Gecachte CUDA-fallback en STT-gewichten vrijgeven vóór modelwissel, met behoud
  van int8/één helper en de lichte geheugenmodus. Geen GPU- of modelinstallatie.
- CPU-only/decoderbenchmarks en ontwerpbudget voor een toekomstige 8-GB-host;
  geen mini-pc-migratie of claim van fysieke audioacceptatie.

- Centrale JARVIS-mastervisie met architectuur-/gapanalyse, ervaringscriteria,
  gespreksscenario's A–H en verbeterplan; blijvende verwijzingen vanuit AGENTS.
- Gesprek als standaard bij verhalen met domeinwoorden; oude leesvragen binden
  aan de laatste vraag. Planner-chat behoudt historie, persoonlijkheid en
  streaming; geen vaste functie-uitleg of dubbele kandidaatselectie voor voice.
- Persoonlijkheidswaarden ook voor tekst, situationele basisprompt en begrensde
  bronnotities die beginonderwerpen van lange gesprekken beter behouden.
- Headless Ollama gebruikt native Chat met expliciete contextallocatie in de
  bestaande transportklasse. Desktop-/cloudtransport blijft compatibel. Lokale
  repositorydefault Qwen2.5:3B; bestaande .env-/modelkeuze niet overschreven.
- Reproduceerbare lokale gesprek-/audio-/TTS-benchmarks en eerlijk gescheiden
  technische resultaten, modelbeperkingen en open menselijke acceptatie.

- Korte mailoverzichten noemen de afzender eerst in een natuurlijke gesprekszin.
- Mailoverzicht standaard in één korte zin, gegroepeerd op afzender en doel met
  aantallen; zonder aparte kop of herhaalde bespreking van vergelijkbare berichten.
- AI-mailsamenvattingen gebruiken bij gevoelige inhoud lokaal Ollama in plaats van
  de AI over te slaan. Terugval vermeldt de oorzaak; compacte Unicode voorkomt
  kunstmatige overschrijding van het contextbudget.
- Recente mails: maximaal twintig berichten daadwerkelijk lezen en gezamenlijk
  samenvatten; geverifieerde verwijzingen tot en met de twintigste mail behouden.
  Specifieke zoekfilters blijven via de bestaande gevalideerde zoekroute lopen.
- Windows-spraak: verouderde heartbeatreacties stoppen geen nieuwere spraakbeurt;
  autorisatiefouten blijven stoppen en een late timer heropent na Stop geen microfoon.

- Intelligent Response Engine: kanaalgebonden lengte/profielen, korte toolspraak naast
  geschreven broninformatie, behoud van deadlines/goedkeuringen, contextgebonden
  mailvervolgvragen en gesloten tijdelijke/permanente gesproken instellingen.
- Classic Butler-persoonlijkheid en gedeelde Nederlandse SpeechFormatter.
- Centrale lokale TTS-router met Supertonic 3 M1–M5, Piper-fallback, providerbinding
  per antwoord en sessie-/geheugenversiegebonden vluchtige audiocache.
- Voice Studio op Windows en Android (708): geïnstalleerde stemmen beluisteren,
  serieel vergelijken en als globale favoriet opslaan; geen microfoon of online TTS.
- Expliciete modelinstallatie na toestemming (~400 MB), 42 echte synthetische
  benchmarkproeven en annuleringsproef. Geen betaalde diensten, cloning of migratie.
- Tweede Windows-start opent het bestaande venster; updatebuild kan naast de
  actieve artifactdirectory worden voorbereid zonder gebruikersgegevens te wijzigen.


- Persoonlijk adresboek op Windows en Android (build 707): namen en aliassen
  koppelen aan één e-mailadres, zoeken, wijzigen, verwijderen en synchroniseren.
  Backend koppelt expliciet genoemde ontvangers vóór toolplanning; dubbele namen
  vragen verduidelijking. Verzendgoedkeuring blijft aan het exacte concept gebonden.
- SQLite schema 7 met voorafgaande back-up; contactwijzigingen gebruiken revisies.


- Android-reparatiebuild 706: overname-/stopherstel en afscherming tegen oude
  foutcallbacks. Chatfinalisatie overleeft herhaalde disconnects, zodat een
  gesprek niet blijvend bezet raakt. Overname wacht op annulering van de oude beurt.
- Natuurlijke afspraak-aanmaak en vrije slotantwoorden behouden eerdere gegevens;
  mogelijkhedenvragen gebruiken feitelijke serverfuncties. Vervolgvragen volgen
  de ingestelde combineerkeuze; proactiviteitspresets en plannertijdzone aangesloten.

- 0.7.5-kandidaat: optionele persistente mailopvolging en contextgebonden vraag
  naar ontvangen antwoorden; controles gebruiken bestaande leesrechten en
  kunnen geen nieuwe verzending autoriseren.
- Persoonlijkheidsvoorbeeld op Windows/Android zonder opslag of tooluitvoering.
  Geheugensynchronisatie uit beperkt toegang tot het oorspronkelijke apparaat;
  schema 6 bewaart die herkomst. Diagnostiek uit start geen resourceprobe.

- Handmatige spraakactivatie reserveert de centrale sessie vóór opname op Windows
  en Android; annuleren maakt late activatie ongeldig.

- Brongebonden invalidatie bewaart onverwante samenvattingen bij vergeten.
  Agenda-alternatieven blijven met volledige buffer binnen het gecontroleerde
  bereik. Android-instellingencontract wordt reproduceerbaar uit de backend
  gegenereerd en in CI gecontroleerd.

- Geschiedenis uit houdt nieuwe gewone gesprekstekst alleen tijdelijk in RAM;
  Android schakelt caching uit. Retentie, conservatieve automatische voorkeuren,
  echte profielpresets en brongebonden ‘onthou dit’/‘vergeet dat’ aangesloten.

- Natuurlijke afspraakslots, correcties zonder dubbele afspraak, popupherinneringen
  en gevalideerde samengestelde opdrachten. Iedere actie behoudt eigen rechten,
  idempotency-key en verplichte exacte goedkeuring.
- Diagnostiekpagina in beide native apps met veilige numerieke export en echte
  latency-/procesmetingen. Python-lint/typechecks zijn reproduceerbaar in CI.

- Fase 7.5 in uitvoering: centrale versiegebonden instellingen in 13 categorieën,
  SQLite/FTS5-geheugen, bronbewust vergeten, lokale samenvattingen en begrensde
  gesprekscontext. Offlinebeleid geldt ook voor interne AI-aanroepen.
- Windows: instellingen-/geheugencentrum, expliciete sessieoverdracht en
  doorlopende spraakbeurten na bewuste activatie. Microfoon start niet vanzelf.
- Nederlandse tijdresolver en hervatbare taakreferenties gebruiken de bestaande
  AutomationEngine. Geen herstel van oude goedkeuringsgeheimen of auto-uitvoering.
- Audiohelper blijft geladen tussen aanvragen; Windows Natural Conversation
  Mode en Android delen dezelfde serverinference. Annulering sluit ook een
  lopende serveraanvraag af; beveiligingsheaders behouden via pure ASGI.
- Android: doorlopende voorgrondgesprekken met centrale sessie/epoch, timeouts,
  expliciete overname, audiofocusherstel en beschikbare platform-AEC/ruisfiltering.
  Tien opeenvolgende synthetische spraakbeurten getest.
- Optionele spraakonderbreking in Windows en Android: pauzeren, echo-/tekstguard,
  geverifieerde vervolguitspraak en annulering van oude audio/generatie met behoud
  van gesprek/taken. Softwareproeven geslaagd; echte echo-/microfoonacceptatie open.
- Android: centrale instellingen-/geheugeninterface, typed controls en CAS,
  import/export via Android-bestandsdialoog, lokale hardwarekeuze apart gehouden.
  Alleen ondersteunde/geïnstalleerde spraakkeuzes aangeboden. Drie nieuwe echte
  emulatorproeven dekken UI, geheugen/synchronisatie en expliciete audio-overdracht.

- Op gebruikersverzoek volstaat één gesproken/getypte ja na de volledige actuele
  mail-/agendapreview; nee weigert. Een mail wordt na het geverifieerde concept
  direct als verzendvoorstel klaargezet. Geen extra verstuur-opdracht of dubbele
  verzending; expliciet alleen-concept blijft behouden. Dezelfde approvalbinding.

- Agenda- en mailvoorstellen in dezelfde chat goedkeuren/weigeren, met volledige
  serverpreview, actuele approverrechten en eenmalige payloadbinding. Verlopen,
  gewijzigde of niet als laatste getoonde previews vragen opnieuw controle.
  Ontbrekende afspraakgegevens blijven bij de oorspronkelijke vervolgvraag;
  geen door het model verzonnen tijdstip. Geen nieuwe client of APK nodig.

- Spraakagenda: ‘Wat stond er voor vandaag in mijn agenda?’ en vergelijkbare
  complete dagvragen halen rechtstreeks echte toolresultaten op, met dezelfde
  rechtencontrole. ‘En morgen?’ behoudt de gekozen agenda; geen willekeurige
  modelontkenning van toegang bij een persoonlijke toolvraag.

- Windows 0.7.1: leesbare native agenda- en e-maillijsten, agenda-/periodekeuze,
  expliciete berichtinhoud, bescherming tegen late antwoorden en duidelijke
  rechtenmelding met eigenaarlink. Chat en spraak behouden dezelfde AI-tools.
- Eigenaarinterface: gekoppelde Windows-/Android-apparaten kiezen op naam/type,
  huidige rechten bekijken en afzonderlijk toekennen. Een deeplink is alleen een
  voorstel en verleent niets. Veilige terugkeer naar dat apparaat na eigenaarlogin.

- Agenda, Gmail en herinneringen bedienen vanuit dezelfde AI-chat en spraakroute,
  met gekozen provider, gevalideerde tools, actuele apparaatrechten en tijdelijke
  gespreksreferenties. Leesbare echte toolresultaten; externe wijzigingen blijven
  voorstellen met afzonderlijke goedkeuring. E-mailinhoud alleen op expliciet
  verzoek; ontvangen inhoud kan geen acties autoriseren. Nederlandse daggrenzen
  en numerieke relatieve herinneringstijden worden lokaal gecontroleerd.
- CalendarSummary-validatie hersteld en CalendarList als gesloten leestool toegevoegd.
- Geen herbevestiging voor een complete agenda-leesvraag; korte verduidelijkingen
  blijven in context en ‘wat staat er in de 1e’ leest de gekozen recente mail.

- Webmail: afzender/onderwerp en leesbare reader in E-mail, zonder bericht-ID's
  te kopiëren. Inhoud opt-in, veilige tekstweergave en begrensde metadata-opvraag;
  resultaten verschijnen niet meer bij Actie voorbereiden.

- Webagenda: agenda's selecteren op naam en afspraken leesbaar direct bij Agenda;
  standaard weekperiode en lokale laad-/fout-/leegmeldingen. Resultaten verschijnen
  niet langer als losse JSON bij Actie voorbereiden. Late antwoorden afgeschermd.

- Google-setup: herstel 404/MIME-fout voor automations.js in de bestaande
  assetallowlist, regressiecontrole op echte HTML-assets en Google-koppelen.bat
  voor veilige Desktop OAuth-JSON-configuratie en alle vier ondersteunde rechten.
  Na login terug naar de koppelpagina; Google-toestemming blijft expliciet.

- Fase 7: centrale SQLite-automatiseringen, herinneringen met lokale tijdzones,
  persistente workflows, apparaatrechten en eenmalige approvals. Officiële Google
  Calendar/Gmail OAuth-/REST-adapters met Windows DPAPI; echte accounts nog niet
  geconfigureerd of getest. Windows/Android 0.7.0 en webbediening, centrale inbox,
  metadata-prioriteit en veilige handmatige messaging. Geen externe FCM-bezorging,
  persoonlijke WhatsApp/SMS-automatisering, oproepen of productie geclaimd.

- Fase 6: native Android 0.6.0 met Compose/Material3, S256-ownerpairing,
  Keystore/Room/DataStore, chat/SSE/historie, foreground-spraak via bestaande
  centrale Whisper/Piper-helper en Android-notificatiekanalen. Geen publieke
  toegang, achtergrondmicrofoon, FCM-bezorgclaim of volledige internetoproepen.

- Windows-client 0.5.0: lokaal Nederlands spreken met expliciete toestemming,
  PTT/sneltoetsen, apparaten/volumes/stilte, faster-whisper en Piper/Ronnie,
  bestaande beveiligde chat/context/SSE, zinsaudio, onmiddellijke stop en
  generatie-/procesannulering. Geen audio-opslag of nieuwe API-routes.
- Experimentele lokale wakefrase, optionele vervolgvraagmodus, begrensde RAM-cache,
  CPU-fallback en licht profiel. Geen gevalideerd Nederlands wake-model, XTTS of
  gesproken barge-in. Geïsoleerde voice-runtime en complete portable build zonder
  impliciete modeldownloads. Handleidingen en hardwareloze regressietests toegevoegd.
- Spraakbediening toont live niveau en duidelijke luister-/verwerkings-/spreekstatus.
  Instructiealinea's ingeklapt; microfoontoestemming en apparaatkeuze worden op
  gebruikersverzoek onthouden. Ontbrekend Tiny is niet selecteerbaar; fouten
  verschijnen direct bij de status en een beschikbare Small-voorkeur wordt hersteld.

- Desktoplogin op verzoek gewijzigd naar gebruikersnaam/wachtwoord, zonder
  browsergoedkeuring. Bestaande Argon2id/rate limits, eigen apparaat zonder
  beheerrechten, 30-daagse desktopsessie en veilig automatisch sessieherstel.
  Wachtwoord wordt direct gewist en nooit op schijf bewaard.
- Veilige refreshcredential blijft behouden bij netwerkuitval vóór verzending;
  onzekere tokenrotatie blijft opnieuw inloggen vereisen. Installatie-UUID blijft
  behouden bij instellingen wijzigen en opnieuw inloggen.
- Vertraagde netwerkresponses van een vorige login kunnen de huidige sessie/UI
  niet overschrijven of gewiste persoonlijke geschiedenis terugzetten.

- Fase 4 / Windows-client 0.4.0: aparte PySide6-app met veilige S256-pairing,
  Windows Credential Manager, streaming/historie, systeemvak/meldingen,
  reconnect/profielen/instellingen, expliciete lokale system_info-capability en
  optionele per-user autostart. Portable PyInstaller-build en geïsoleerde tests/CI.
- Sessies kunnen via twee beperkte routes uitsluitend hun eigen apparaatstatus
  bekijken of de eigen koppeling intrekken; geen nieuwe beheerscopes.

- Fase 3 via PR #13 geïntegreerd naar develop (119bcdd); laatste PR-head met
  geslaagde repository-/Windows-/Linuxchecks, main ongewijzigd.

- Fase 3 / 0.3.0: lokale eenmalige eigenaarsetup, Argon2id, beveiligde webchat,
  HttpOnly-sessies/CSRF, korte opaque tokens, refreshrotatie/replay-intrekking,
  sessie- en wachtwoordbeheer, default-deny en afzonderlijke apparaatrechten.
- Veilige apparaatpairing met menselijk vergeleken code, expliciete goedkeuring
  en S256-bewijs; apparaat hernoemen/intrekken/verwijderen, begrensd auditlog.
- SQLite-schema 3 met pre-migratieback-up en behoud van gesprekken; aparte
  procescontrolstatus. 156 tests inclusief echte tijdelijke TCP/herstartflow.
- Serverinstaller/CI werkt pip bij naar vastgelegde 26.3; lokale dependencyaudit
  en Bandit zonder actuele bevindingen. Nederlandse auth-/pairing-/securitydocs.
- Alleen ontwikkeldesktop localhost:8765; geen nieuwe clients of externe toegang.

- Lokale herhalingsmelding: nieuwste-berichtregressie toegevoegd, Ollama-temperature
  0.2 en lokale Qwen2.5 3B-keuze. Twee echte gesprekken van vier beurten geslaagd;
  bestaande gebruikersgesprekken en lichte repositorydefaults behouden.

- Groq met GPT-OSS 120B toegevoegd als derde provider, met streaming, veilige
  sleutels, webchatkeuze en auto-voorkeur Groq → Ollama. Echte Groq-proef geslaagd;
  geen nieuwe dependency of database-migratie. 99 automatische tests.

- Lokale Gemini-modelkeuze op verzoek bijgewerkt naar stabiele Gemini 4 Hydrogen;
  server herstart en echt getest. Google gaf ook hier tijdelijk 503-overbelasting.
  Echte auto-fallback naar inmiddels beschikbare Ollama qwen3:0.6b geslaagd.
  Geen wijziging van repositorydefaults, sleutels of applicatiecode.

- Fase 2 via PR #9 naar develop; 90 tests, echte browser-/herstartcontrole en
  live Gemini-proef (503-overbelasting, nog geen live antwoord). Google-foutarrays
  ondersteund, duidelijke overbelastingsmelding en veilige Windows-envkopieën.

- Fase 2: gedeelde Gemini/Ollama-teksttransportlaag, centrale fallbackrouter,
  begrensde chat-API/SSE, annuleerbare antwoorden, SQLite-gesprekken en lokale webchat.
- Windows-instructies en Git-branchhelpers gebruiken de ingebouwde PowerShell
  5.1; geen verplichte pwsh-installatie. Windows-CI test beide PowerShell-edities.
- Fase 1: lichte localhost-headlessbasis met health/ready/status, .env-config,
  JSON-logrotatie, SQLite, gecontroleerd procesbeheer, Windows-scripts en pytest.
- Fase 1 via PR #5 geïntegreerd naar develop, met 39 geslaagde tests op Windows
  en Linux, verplichte serverchecks en lokaal gemeten prestatiecijfers.
- Fase-0-hercontrole: staged bestanden afzonderlijk op geheimpatronen controleren;
  CI-whitespacecontrole op de daadwerkelijke PR-/pushwijzigingen richten.
- Fase 0: projectstructuur, ontwikkelplan, blijvende Codex-instructies,
  geheimuitsluitingen, Git-workflowhelpers en minimale repository-CI voorbereid.
- Fase 0 wijzigde geen applicatiecode; fase 1/2 voegen de lokale server toe.
  Geen actieve accountintegraties of deployment.
- Origin/upstream en lokale branchhelpers ingericht; echte CI op main/develop
  geslaagd en branch protection ingeschakeld. Historische upstream-TLS-sleutel
  gedocumenteerd zonder de vereiste bronhistorie te herschrijven.
