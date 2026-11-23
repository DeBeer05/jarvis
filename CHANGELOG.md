# Changelog

Wijzigingen van deze fork; oorspronkelijke geschiedenis en licentie blijven behouden.

## Unreleased

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
