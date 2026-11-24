# Ontwikkelvoortgang

## Huidige opdracht

### Goedkeuren in chat en vervolggegevens — 24 november 2026

PR #23 met spraak-/dagvragen na tien groene jobs gemerged naar develop 436bb2b.
Gebruiker vraagt expliciet agenda- en mailacties in dezelfde chat goed te keuren.
Featurebranch feature/chat-approvals vanaf die basis. Het eerdere bevestigings-
loopje kwam doordat vervolggegevens (‘Maak hem van 11 tot 12’) buiten de planner
vielen. Eigen gebruikersgegevens blijven nu bij de direct voorafgaande vraag;
een onderbroken oude vraag kan niet door een losse ja worden hervat.

Volledige serverpreview met jaartal, datum/tijd/zone, titel, agenda, locatie,
genodigden/herhaling of volledige e-mail. Expliciet Goedkeuren/Weigeren gebruikt
de bestaande ApprovalManager, actuele scopes en nonce-digest. De modelplanner
heeft geen goedkeurtool. Fingerprint wordt ook binnen de beslistransactie
gecontroleerd; laatste voltooide assistantantwoord en vijfminuten-geldigheid
moeten overeenkomen. Geen korte ja als approval. Grote/onvolledige/niet volledig
toonbare voorstellen blijven in de bestaande eigenaarinterface. Toon mijn
voorstellen / Toon voorstel ID herstelt context na herstart of meerdere keuzes.
Resultaat wordt alleen na echte completed-engine-status als uitgevoerd gemeld.

Gerichte tests dekken aanmaken, weigeren, mailverzending, scopes, dubbele
bevestiging, veranderde/verlopen/onderbroken preview, race tijdens challenge,
ontbrekende tijden en vervolgcontext. Echte Groq/GPT-OSS 120B-proef met tijdelijke
SQLite en gesimuleerde executor geslaagd: vraag → gegevens → voorstel → Goedkeuren
→ completed. Geen echte afspraak of e-mail namens de gebruiker uitgevoerd.
Verificatie: 45 gerichte tests en 249 volledige servertests geslaagd; pip check,
repository-/whitespace-/indexgeheimcontrole geslaagd; Bandit nul middel/hoge
bevindingen. De server bleek bij activering niet meer actief; bestaande helpers
hebben hem gecontroleerd gestart. Health/ready 200 en anonieme automation-API 401.
Geen actieve chatvragen of externe taken bij de start; bestaande voorstellen en
credentials behouden. Remote CI en integratie via feature-PR naar develop.
GitHub-blokkade op PR #24: geen push-/PR-checks aangemaakt. Alle vier handmatige
workflow_dispatch-pogingen geweigerd met HTTP 422: ‘Actions has been disabled for
this repository’, terwijl permissions.enabled=true en workflows active melden.
Geen oorzaak als billing/policy aangenomen en geen instellingen of bescherming
gewijzigd. Code gepusht en lokaal actief; PR blijft open, niet gemerged zonder
groene CI. Eigenaar moet de Actions-/accountblokkade bij GitHub oplossen.
Windows 0.7.1/Android 0.7.0 gebruiken dezelfde chatroute; geen rebuild of APK nodig.
Stop na fase 7; accounts, main en private credentials behouden.

### Spraakagenda en Android-verbinding herstellen — 23 november 2026

Windows-/rechtenuitbreiding via PR #22 geïntegreerd naar develop 237b10c na tien
groene push-/PR-jobs. Tijdens die opdracht meldde de gebruiker dat spraak alsnog
geen agenda kon lezen en dat Android offline was. Nieuwe fixbranch vanaf deze
basis; bestaande gebruikersbestanden en sessies behouden.

Actuele rechtencontrole: zowel het bestaande Windows- als Android-apparaat heeft
inmiddels expliciet automation:read/write. De gesproken variant met ‘stond’ en
vraagteken bleek een gewone modelreactie zonder tool te krijgen, terwijl een
eerdere getypte variant wél las. Complete dagvragen worden nu rechtstreeks
gevalideerd gelezen, onafhankelijk van hoofdletters, leestekens en staat/stond.
‘En morgen?’ behoudt de werkelijk gekozen agenda, ook na een lege lijst. Dezelfde
actuele sessie-/rechten-/requestguards blijven gelden. Een persoonlijke toolvraag
kan niet meer via chat:true een verzonnen ontkenning van agendatoegang opleveren.

31 gerichte automatiseringschattests en de volledige suite van 235 servertests
geslaagd. De bestaande loopbackserver gecontroleerd herstart met de fix. Geen
echt Google-account namens de gebruiker bevraagd of externe mutatie uitgevoerd.

Android: aanvankelijk alleen de emulator via ADB zichtbaar. Na expliciete
gebruikersbevestiging werd de echte telefoon aangesloten. Ontbrekende reverse-
tunnel naar 8765 hersteld; HTTP 200 vanaf de echte telefoon naar /health bevestigd.
De eigen JARVIS-UI op de echte telefoon toont daarna Online; tijdelijke UI-dump
direct verwijderd. Geen APK-update, dataverwijdering, herpairing of publieke poort.
USB moet voor deze lokale ontwikkelopstelling verbonden blijven. Stop na fase 7.

### Windows-bediening en Windows-/Android-rechten — 23 november 2026

AI-chatuitbreiding geïntegreerd via PR #21 / develop 9b6f498 na tien groene
push-/PR-jobs. Nieuwe gebruikersopdracht op feature/windows-agenda-mail vanaf
die actuele basis: agenda/mail ook in Windows bedienen en Android rechten geven.
De echte Windows-app had nog uitsluitend standaard chat-/statusrechten; deze
zijn niet stilzwijgend verhoogd. De huidige Windows-sessie is behouden.

Windows 0.7.1 vervangt JSON-leesresultaten door eigen agenda-/mailweergaven:
agenda's op naam, datumperiode/snelkeuzes, afspraken/tijden/locatie, maximaal vijf
mailheaders en expliciet berichtinhoud lezen. Ontvangen tekst blijft plain text;
geen HTML/trackingafbeeldingen. Async werk via bestaande workers en guard op
sessie/origin/generatie plus request-/selectieversies. Uitloggen of intrekken
van rechten wist de privéweergaven. Queryallowlist uitsluitend uitgebreid met
de exacte e-mailbody-opt-in. Bestaande drafts worden niet overschreven door het
AI-voorbeeld. Geen netwerk-/Qt-werk op verkeerde thread of nieuwe dependencies.

Eigenaarinterface kiest gekoppelde apparaten op naam/type, waaronder Android en
Windows, met huidige rechten. Windows-knop opent het eigen apparaat als voorstel;
de eigenaar moet zelf opslaan en bevestigen. Geen automatische grant, reparing,
Google-consent of nieuwe Android-APK. Veilige UUID-allowlist voor login-return;
geen vrij redirectadres. Ingetrokken/eigen apparaten uitgesloten van de keuze.

Verificatie: 80 Windows-clienttests; 229 volledige servertests plus afzonderlijke
nieuwe Android-grant/revoke-test geslaagd. Echte native TCP-proef dekt login,
default deny, eigenaargrant, agenda, mailbody, AI-SSE en sessiebehoud. JS-gedragstest
dekt Windows-/Android-keuze zonder automatische POST en expliciete Androidgrant.
Build 0.7.1 inclusief spraakhelper geslaagd; synthetische agenda-/mailvensters
visueel gecontroleerd. Echte ontwikkelapp gecontroleerd afgesloten en herstart;
0.7.1 zichtbaar, ingelogd gebleven, duidelijke rechtenmelding. Geen echte Google-
accounttests, audioproef of externe mutaties. Bestaande server op 8765 behouden.
Resterend: eigenaar moet de bedoelde apparaten zelf rechten geven; remote CI en
PR-integratie worden afzonderlijk gecontroleerd. Main behouden; stop na fase 7.

### AI-bediening binnen fase 7 — 23 november 2026

Gebruiker bevestigt werkende integraties en vraagt expliciet bediening via AI.
Branch feature/ai-automation-chat vanaf actuele develop 062fec2. De bestaande
chat/SSE-route geeft de geauthenticeerde principal door aan een gesloten
AutomationChat-controller; transcripties gebruiken dezelfde route. Geen nieuwe
client, APK, modellen, dependencies of schema. Gewone gesprekken behouden hun
bestaande providerroute. De planner en samenvattingen respecteren de gekozen
provider en bestaande fallbacklimieten. Tools/inputs worden gevalideerd; actuele
sessie-/apparaatrechten worden vóór en na planning en vlak vóór Google-verzoeken
opnieuw gecontroleerd, ook na tokenrefresh. Geen automatische scopeverhoging.

Agenda's/afspraken, mailmetadata/expliciete inhoud, herinneringen en gecontroleerde
concepten werken via geregistreerde tools. Externe mutaties blijven voorstellen
voor de bestaande goedkeuringspagina; een kort ja autoriseert niets. Referenties
zijn begrensd tot dezelfde sessie/apparaat/gesprek en vijftien minuten. Geen
mailbody naar de planner; samenvatting zonder executor. Nederlandse daggrenzen
en numerieke relatieve herinneringen gecontroleerd. CalendarSummary-validatie
hersteld; CalendarList toegevoegd zonder opslag van accountdata in jobresultaten.

26 gerichte tests geslaagd, inclusief echte geauthenticeerde SSE met gemockte
Google, synthetische STT→toolchat→TTS, revoke/refresh/cancel, ongeldige/injectie-
plannen, metadata/bodykeuze, concept-snapshot en externe approval. Echte lokale
Qwen2.5 3B-proef met tijdelijke database en gemockte Google: agenda, mail en
herinnering geslaagd; modelverwarring CalendarList/Read gevonden en afgeschermd.
Geen echte accounttests of microfoonproef uitgevoerd. Volledige regressiesuite:
228 servertests en 75 Windows-clienttests geslaagd; pip check, repository-/
whitespacecontrole schoon; Bandit nul middel/hoge bevindingen. De server is met
de bestaande helpers gecontroleerd herstart op loopback:8765; accounts, settings
en Google-credentials behouden. Geen nieuwe APK nodig. Remote CI en integratie
via feature-PR naar develop; main blijft ongewijzigd. Stop na fase 7.

Aanvullende screenshots: onnodige leesbevestiging en verlies van ‘de 1e’ als
mailreferentie. Planner vraagt geen herbevestiging voor expliciete leesvragen;
complete dagopvraag heeft een gevalideerde fallback. Korte verduidelijkings-
antwoorden blijven bij de oorspronkelijke leesvraag. Ordinale mailverwijzingen
worden vanuit de echte recente lijst opgelost, niet met verzonnen IDs. Drie
regressietests en echte Groq/GPT-OSS 120B-proef met exact de screenshotzinnen,
synthetische Google en tijdelijke SQLite geslaagd. Geen echte accountdata opgehaald.

Aanvullende melding e-mail meegenomen in dezelfde weergavefix: zoekresultaten
tonen nu afzender/onderwerp onder E-mail, met leesknoppen en een lokale reader.
Alleen metadata wordt automatisch opgehaald (maximaal tien, batches van vijf).
Berichttekst vereist de expliciete Inhoud lezen-keuze. UTF-8/base64url-tekst wordt
leesbaar; HTML en externe afbeeldingen worden niet geladen. HTML-only mail toont
een duidelijk benoemde korte weergave. Geen handmatig kopiëren van bericht-ID's
nodig. Nieuwe gedragstest dekt reader, opt-in, Unicode/injectietekst en late data.

Agendaweergave hersteld na gebruikersmelding: CalendarList en zoekresultaten
kwamen onterecht als JSON onder Actie voorbereiden terecht. Agenda's vullen nu
een keuzelijst met namen/hoofdagenda; afspraken staan leesbaar onder Agenda met
tijden, hele dagen en locatie. Standaardperiode vandaag tot over een week,
lokale laad-/fout-/leegmeldingen, waarschuwing voor onvolledige resultaten en
afscherming van late antwoorden na agenda- of zoekwissel. Ontvangen tekst wordt
alleen via textContent getoond. Geen accountdata opgehaald tijdens ontwikkeling.
Gerichte Node-gedragstest gebruikt synthetische data, inclusief HTML-injectie,
de gekozen agenda, fouten, lege/pagineresultaten en verouderde antwoorden.

Herstel Google-setup na gebruikersmelding: de bestaande /chat/assets/{name}-route
ving automations.js af, maar de allowlist miste het bestand. Daardoor 404 met
JSON-contenttype en terecht geweigerde uitvoering door nosniff. De algemene
assetroute is hersteld; de dubbele onbereikbare route is verwijderd. Regressietest
controleert nu alle scripts die de echte automations.html noemt én hun MIME-type.
Google-koppelen.bat met PowerShell-/Python-helper toegevoegd: expliciet gekozen
Desktop OAuth-JSON, behoud bestaande config/overige .env-waarden, gecontroleerde
serverherstart, assetcontrole en selectie van alle vier ondersteunde Google-
rechten. Geen automatische Google-consent, accounttest of externe mutatie.
Veilige terugkeer na login naar de koppelpagina; geen vrije redirect-URL.
Verificatie: volledige serversuite 199 geslaagd vóór de aanvullende JS-test;
zes gerichte setup-/asset-/redirecttests geslaagd. PowerShell-syntax en echte
-CheckOnly-uitvoering met spaties in het pad geslaagd. Na gecontroleerde echte
herstart: automations.js 200 text/javascript, ready 200 en anonieme API 401.
Geen clientbestand namens de gebruiker gekozen of Google-account gekoppeld.

Fase 7 expliciet opgedragen op feature/smart-automations vanaf develop c405304
(fase-6-PR #17 is gemerged; alle mergechecks waren groen). Geïmplementeerd:
SQLite-schema 4 met voorafgaande backup, centrale AutomationEngine/scheduler,
gesloten tools, eenmalige goedkeuringen, persistente workflows en herinneringen,
Google Desktop OAuth/PKCE met DPAPI-tokenopslag en officiële Calendar/Gmail REST.
Windows-/Android-/webbediening in dezelfde bestaande clients. Rechten voor
bestaande native apparaten uitsluitend na eigenaargrant. Externe mail/agenda-
wijzigingen altijd met exacte preview/ETag en goedkeuring; onzekere resultaten
worden niet automatisch herhaald. Geen echte Google-accounttests uitgevoerd.
Volledige regressiesuite: 194 servertests geslaagd, waarvan 22 nieuwe
automatiseringstests. Windows: 75 tests; Android: vijf JVM-tests en zeven echte
instrumented emulatortests. Beide appbuilds/unsigned Android release en lint
geslaagd, Windows portable 0.7.0 echt gestart. Server-pip check/audit schoon;
Bandit drie lage bestaande signalen, geen middel/hoge of suppressies.
Repository-/whitespace-/indexgeheimcontrole geslaagd. Git-afhandeling via eigen
featurebranch en PR naar develop, uitsluitend na groene checks en inhoudelijke
review; main blijft ongewijzigd. Android 0.7.0-APK staat in .local/android-build.
De echte server is daarna afzonderlijk gecontroleerd herstart op dezelfde
loopback:8765. Schema 4, migratiebackup en behoud van het eigenaaraccount zijn
bevestigd; health/ready/automations geven 200 en anonieme automation-API's 401.
Alleen lokale fase-/schedulerflags zijn bijgewerkt; credentials zijn behouden.
Er zijn nul automatiseringstaken aangemaakt en geen Google-account gekoppeld.
Integratie via [PR #18](https://github.com/DeBeer05/jarvis/pull/18), na groene CI.
FCM externe bezorging is nog
niet ingericht; de engine levert een geauthenticeerde inbox en bestaande lokale
notificaties. Geen volledige oproepen, productie, mini-pc of fase 8.

## Voorgeschiedenis fase 6

Fase 6 expliciet opgedragen: native Android-app, branch feature/android-client
vanaf develop a78257e. Bestaande loopbackserver:8765 en Windows-client blijven
behouden. AGENTS-fasegrens aangepast naar STOP na fase 6. Geen publieke toegang,
firewall/routerwijziging, mini-pc, integraties of volledige oproepen.

Kotlin/Compose/Material3-app met tien schermen, Keystore, Room/DataStore,
geauthenticeerde SSE/context, S256-ownerpairing en lokale audio-client gebouwd.
SDK/Gradle geïsoleerd voorbereid; debug-APK daadwerkelijk gestart op API-36-
emulator. Nieuwe beveiligde mobile speechroutes hergebruiken fase-5-helper;
Android-wachtwoordlogin start alleen pairing, nooit een ongekeurde sessie.
Vijf JVM-tests, zes echte emulatortests, Android-lint zonder fouten en debug- plus
unsigned releasebuild geslaagd. Windows-regressies: 74 tests; serverregressies
165 bestaand plus zeven nieuwe mobieltests. Keystore, refresh/pairing/context,
TLS-afwijzing, echte Piper/Whisper en Android-audio-API's daadwerkelijk getest.
APK: .local/android-build/JARVIS-Android-0.6.0-debug.apk (circa 19,2 MB).
Implementatie gepusht naar de eigen fork; [PR #17](https://github.com/DeBeer05/jarvis/pull/17)
naar develop. Eerste CI bevestigt servermatrix en Windows-clientbuild; Android-
SDK-bootstrap en licentie-EOF zijn hersteld na de eerste CI-bevindingen. Alle
checks op de definitieve head zijn vereist vóór veilige merge. Main blijft intact.
Races bij uitloggen/refresh en late cachewrites zijn afgeschermd. Alleen expliciet
goedgekeurde chatrechten activeren Android-chat/microfoon/verwijderknoppen.
Pythondeps schoon; Bandit zeven lage beoordeelde subprocess/abort-signalen,
geen middel/hoge of suppressies. Geen persoonlijke data/geheimen in artefacten.
Activering op echte server: gecontroleerde herstart nog door gebruiker nodig;
automatische review blokkeerde de gecombineerde herstart/emulatoropdracht zonder
nadere reden. De eigen synthetische testfixture is wel veilig gestopt.
FCM is zonder configuratie een lokale testimplementatie; geen externe bezorging
of echte telefoonspraak geclaimd. Zie docs/PHASE_6_TEST_REPORT.md voor status.

## Voorgeschiedenis fase 5

Fase 5 is expliciet geautoriseerd: Nederlandse spraak in dezelfde Windows-app,
geen tweede backend, bestaande localhost:8765/auth/chatcontext behouden. Branch
feature/dutch-voice-assistant vanaf develop d6e1b83; fase-4-PR #15 is gemerged en
de echte repository-/server-/client-CI was groen. Main blijft c995834.
Gebruiker heeft downloads van Whisper Small (~486 MB), Piper MLS (~77 MB) en
aanvullend Piper Ronnie (~63 MB) afzonderlijk goedgekeurd. Alle bestanden lokaal
buiten Git gedownload, pinned revisies/groottes/hashes gecontroleerd.

Geïmplementeerd: onthoudbare microfoontoestemming/microfoon uit bij start, spraakpaneel,
hardwarekeuze, PTT/sneltoetsen/expliciete globale opt-in, stiltepoort/Silero,
faster-whisper Nederlands met CPU-fallback, Piper-stem/snelheid/voorbeeld,
zinsgewijze bestaande SSE/context, begrensde queues/RAM-cache, directe audiostop
en annulering van de eigen inferenceprocesboom. Geen audio naar de server.
74 clienttests en 165 servertests geslaagd; portable build/start en echte
ingepakte Whisper/Piper-inferentie geslaagd. Laatste Windows-GUI-/helperrookproef
geslaagd op implementatiehead 63826ee. Volledige client-/voice-dependencyaudits:
0 bekende kwetsbaarheden. Bandit: 4 lage beoordeelde subprocess/abort-signalen,
0 middel/hoge bevindingen, geen suppressies. Index/nieuwe range met Gitleaks schoon.
Twaalf echte synthetische enginebeurten: STT mediaan 1,983 s, TTS 0,137 s warm;
CPU-fallback, piek helper-RAM circa 869 MiB. Dit is geen fysieke audioproef.
Eigenaar bevestigt de echte audioproef met 'Alles werkt, inclusief stoppen'. Op zijn verzoek zijn
instructiealinea's vervangen door grote luister-/verwerkings-/spreekstatus,
live niveaumeter, duidelijk transcript en ingeklapte instellingen. Toestemming
en gekozen microfoon worden onthouden; globale shortcuts blijven per sessie opt-in.
Een daaropvolgende fout bleek geselecteerd maar niet geïnstalleerd Whisper Tiny;
Small hersteld, apparaten behouden, ontbrekende modellen onselecteerbaar en
concrete foutmelding direct bovenaan. Geen extra download of opname uitgevoerd.

Git: implementatie e9c9d7e en UX/herstel 63826ee gepusht naar de eigen fork.
Integratie via [PR #16](https://github.com/DeBeer05/jarvis/pull/16) naar develop,
uitsluitend na alle geslaagde checks op de laatste head, inclusief Windows-client-
build, plus inhoudelijke review. E9c9d7e had reeds groene echte remote CI.
Owneracceptatie en technische fase-5-basis zijn geleverd; uitgebreide wake-/ruis-
en hardwarewisselproeven blijven optioneel volgens het testverslag. Geen verdere
verplichte handmatige installatie voor deze ontwikkeldesktop. Geen main-release.

Beperkingen: wakefunctie is experimentele Whisper-fraseherkenning na een uiting,
geen bewezen Nederlands wake-wordmodel. XTTS/licentiereferentie/runtime ontbreken;
geen gesproken barge-in/AEC of bewezen hybride voordeel. RTX 4060 gedetecteerd,
maar benodigde CUDA-libraries ontbreken; CPU werkt. Licht profiel voorbereid,
geen 8-GB-mini-pc getest. STOP na fase 5; geen Android/fase 6.
Zie docs/PHASE_5_TEST_REPORT.md en de vier VOICE-handleidingen.

## Voorgeschiedenis fase 4 en eerder

Actuele bijsturing: eigenaar wil in de Windows-app rechtstreeks met gebruikersnaam
en wachtwoord inloggen, zonder browsergoedkeuring, en na appherstart ingelogd blijven.
Geïmplementeerd via bestaande Argon2id-/rate-limitservice, cookie-vrije desktop-
loginroute, dezelfde Windows-apparaatidentiteit en Credential Manager. Geen
wachtwoordopslag. Nieuwe desktoplogin maximaal 30 dagen; refresh bij gebruik,
ongebruikte refresh standaard 7 dagen. Andere apparaten/pairing blijven beveiligd.
Getest: 165 server- en 38 clienttests geslaagd, inclusief directe login via echte
TCP-server en herstel na clientherstart zonder nieuwe wachtwoordinvoer. Geen
secret in settings. Bandit en beide dependency-audits zonder actuele bevindingen.
De native-login portable build start lokaal succesvol na fix voor build-PATH/ICU-
vervuiling. Eigenaaraccount/chatdata behouden; geen database-migratie nodig.
De eerdere vraag om eigenaarpairing is hiermee voor deze Windows-app vervallen.
Late antwoorden van oude netwerkverzoeken worden na uitloggen/profielwissel
genegeerd; persoonlijke historie kan daardoor niet terugverschijnen.

Fase 4 expliciet opgedragen op 23 november 2026: afzonderlijke Windows-client,
beveiligde pairing/chat, systeemvak/meldingen/instellingen, portable Windows-build.
In uitvoering op feature/windows-desktop-client vanaf develop 19f3e27.
Geïmplementeerd: afzonderlijke PySide6-client, Credential Manager, S256-pairing,
chat/SSE/historie, provider/modelinformatie, veilige profielen/reconnect,
systeemvak/meldingen/instellingen, lokale expliciete systeeminformatiedemo.
34 clienttests en 159 servertests geslaagd, inclusief echte native TCP-pairing/chat/
refresh/historie/intrekking. Bandit/pip-audit/index/Gitleaks/repository schoon.
Bronclient zichtbaar en rookproef geslaagd;
portable onedir-build gemaakt. Fase-4-docs en client-Windows-CI toegevoegd.
De gebruiker droeg tijdens dit werk fase 5 expliciet op: voice bovenop deze
bestaande client. Modeldownloadtoestemming en echte eigenaarpairing gevraagd;
geen modellen of microfoon zonder de gevraagde toestemming.
Alleen ontwikkeldesktop en bestaande localhost:8765; geen externe blootstelling,
mini-pc-deployment, Android, volledige spraak of autonome acties. STOP na fase 4.
De fase-3-sectie hieronder is de gecontroleerde uitgangssituatie.

Fase 3 expliciet opgedragen: authenticatie, apparaatbeheer/pairing en beveiliging.
Afgerond en via PR #13 geïntegreerd naar develop, mergecommit 119bcdd.
Ontwikkeld op feature/security-device-pairing vanaf develop 5b6960c.
156 tests geslaagd, inclusief 57 nieuwe security-/procesgevallen, echte tijdelijke
TCP-pairing en sessie/historiebehoud na herstart. De eigenaar heeft zelf via de
interactieve CLI het account aangemaakt en in Chrome ingelogd; beveiligde webchat,
bestaande historie en een Groq-antwoord daadwerkelijk waargenomen.

Argon2id; default-deny; korte opaque access/refresh met rotatie/replay-intrekking;
HttpOnly/SameSite/CSRF; sessie/wachtwoordbeheer; S256-pairing met expliciete
codevergelijking en minimale rechten; apart chat:delete; apparaatintrekking én
verwijdering; begrensd auditlog; schema 3 met pre-v3-back-up en behouden chatdata.
Installer/CI-pip bijgewerkt naar 26.3 na dependencybevindingen. Nieuwe Nederlandse
handleidingen/testverslag en schone login-screenshot; persoonlijke credentials en
chatdata blijven uitsluitend lokaal. Geen echte apparaten ingetrokken of echt
wachtwoord gewijzigd door de agent.

Lokale tests: 156 passed, 1 bekende Starlette/httpx-deprecatiewaarschuwing, 51,36 s.
Pip-audit en Bandit opnieuw uitgevoerd: 0 kwetsbaarheden/0 bevindingen; geen
onderdrukking. JS/pip/repository/whitespace geslaagd. Echte server gecontroleerd
herstart op 8765: health/ready 200, anonieme private routes/controlstatus 401;
schema 3, 9 gesprekken/26 beurten/back-up behouden, geen foreign-key-fouten.
Index-/Gitleakscontrole en nieuwe commitrange schoon, geen geheimen/data in Git.
Implementatiecommit ee2f687 is gepusht naar de eigen fork. Integratie via
[PR #13 naar develop](https://github.com/DeBeer05/jarvis/pull/13).
Alle drie verplichte checks voor de definitieve head 7422bf9 daadwerkelijk geslaagd:
[repository](https://github.com/DeBeer05/jarvis/actions/runs/45082049075) en
[Windows/Linux-servermatrix](https://github.com/DeBeer05/jarvis/actions/runs/45082049033).
Ook Windows PowerShell 5.1 en 7 zijn daarin getest. Inhoudelijke review van gate,
sessietransacties, pairing/rechten, migratie en frontend uitgevoerd; geen open
kritieke bevinding. PR-head exact gecontroleerd en met --match-head-commit
gemerged, zonder bypass/force-push. Develop is lokaal fast-forward bijgewerkt,
alle commits gepusht en werkmap schoon gecontroleerd. Main blijft c995834.
Ook de echte CI op mergecommit 119bcdd is geslaagd:
[repository](https://github.com/DeBeer05/jarvis/actions/runs/45082287960) en
[Windows/Linux](https://github.com/DeBeer05/jarvis/actions/runs/45082287966).
Alleen ontwikkeldesktop, 127.0.0.1:8765. Geen Tailscale/firewall/proxy/clientapps,
integraties/automatiseringen of mini-pc-deployment. STOP na fase 3.
Zie docs/PHASE_3_TEST_REPORT.md, AUTHENTICATION.md, DEVICE_PAIRING.md en SECURITY.md.
Fase 3 is afgerond. Deze afrondingsnotitie volgt via een eigen documentatie-PR
met dezelfde verplichte checks. Geen verplichte handmatige stap meer voor lokaal eigenaargebruik.
Optioneel: eigen synthetische pairingproef volgens docs/DEVICE_PAIRING.md.
Gemini-antwoordacceptatie blijft een eerder providerpunt; Groq/Ollama werken.
De fase-2-/fase-0-secties hieronder zijn bewaarde voorgeschiedenis.

Aanvulling fase 2: op verzoek Groq als derde cloudprovider toegevoegd. Groq
GPT-OSS 120B live geslaagd; lokale auto-voorkeur Groq → Ollama. Herhaling door
het kleine lokale model aangepakt met Qwen2.5 3B/temperature=0.2; twee echte
vierbeurtgesprekken geslaagd. Details onderaan.

Fase 2 — AI-engine en webchat geïmplementeerd en via PR #9 naar develop
geïntegreerd (`40c2452`). 90 lokale tests geslaagd; oorspronkelijke PR- en merge-CI
op Windows/Linux/repository geslaagd. Aanvullende live-foutafhandeling en
configuratiekopiecontrole via fix/phase-two-verification, met dezelfde CI-eisen.
Lokale modelkeuze op verzoek bijgewerkt naar Gemini 4 Hydrogen (zie onderaan).
Live antwoordacceptatie nog open: Gemini geconfigureerd door de eigenaar, maar
Google gaf bij Hydrogen modeloverbelasting/een technische fout. Ollama qwen3:0.6b
is inmiddels door de eigenaar beschikbaar gemaakt; echte auto-fallback naar
Ollama leverde een volledig gestreamd antwoord en opgeslagen beurt op.
Alles op de ontwikkeldesktop; poort 8765 behouden. Main blijft ongewijzigd.
STOP na fase 2; geen desktop-/Android-app, spraak, koppelingen of automatiseringen.
De onderstaande fase-0-secties vormen de bewaarde voorgeschiedenis.

## Uitgangspunt — 22 november 2026 (Europe/Amsterdam)

- Bestaande werkmap `J.A.R.V.I.S` was volledig leeg, inclusief verborgen bestanden.
- Mark-LVII rechtstreeks gecloned; geen extra projectmap aangemaakt.
- Upstream: <https://github.com/FatihMakes/Mark-LVII>, standaardbranch `main`.
- Basiscommit: `752ff618a4e6a4bf2e675866b993071d739cfce2`.
- Alle 56 oorspronkelijke commits behouden; geen shallow clone of herschreven historie.
- Eigen publieke fork: <https://github.com/DeBeer05/jarvis>.
- Licentie: CC BY-NC 4.0; naamsvermelding/licentie behouden, uitsluitend niet-commercieel.
- Upstream-applicatiecode en dependencybestanden blijven ongewijzigd.

## Omgeving

| Onderdeel | Gecontroleerd resultaat |
| --- | --- |
| Windows | Windows 11 Home, 10.0.26300, 64 bits |
| Git | 2.49.0.windows.1 |
| GitHub CLI | 2.105.0, aangemeld als DeBeer05 via Windows keyring |
| Python | 3.13.3; upstream setup noemt 3.11 t/m 3.13 |
| Java | 17.0.12 LTS; Android SDK/Gradle nog niet gecontroleerd of geïnstalleerd |
| Vrije ruimte | Circa 41,23 GB op C: bij aanvang; momentopname |
| Aanvang Git-status | Geen repository, bestanden of gebruikerswijzigingen aanwezig |

GitHub CLI stond al geïnstalleerd en in het permanente PATH. De lopende shell
had een ouder PATH; hiervoor is het bestaande absolute programmapad gebruikt.
Winget bevestigde de bestaande installatie; geen nieuwe dependencies geïnstalleerd.
Commits gebruiken lokaal het GitHub noreply-adres in plaats van een privé-e-mailadres.

## Voorbereidingsresultaat

- `origin` is de eigen fork; `upstream` haalt alleen de oorspronkelijke bron op.
  De lokale push-URL voor upstream is bewust geblokkeerd.
- `main` behouden; `develop` vanaf upstream `main` gemaakt.
- Aanvullende lege mappen met `.gitkeep`; bestaande `config/`, GUI, dashboard,
  providers, acties, geheugen en agents behouden.
- Uitsluitingen aangevuld, veilig `.env.example`, projectdocumentatie,
  blijvende agentinstructies, Git-hulpscripts en minimale structuur-CI toegevoegd.
- Initiële controle van 109 gevolgde upstreambestanden: geen treffers met de
  gebruikte geheimpatronen. Dit is een patrooncontrole, geen volledige securityaudit.

## Controle op gevoelige gegevens

Historische scan: 415 unieke blobs onderzocht (binaire inhoud overgeslagen).
Eén treffer: oude upstream privé-TLS-sleutel `config/certs/jarvis.key`, blobprefix
`b7b1138042e5`, toegevoegd in `067f528` en verwijderd in `8a79f40` op
25 augustus 2026. Niet aanwezig in de huidige tree. De oorspronkelijke historie
blijft volgens opdracht behouden; daarom blijft deze bekende blootstelling in de
forkhistorie bestaan. Sleutel niet hergebruiken; vervangen waar die nog gebruikt wordt.
`--history` blijft dit als fout rapporteren, zonder sleutelinhoud te tonen.

De gitignorepadcontrole is gecorrigeerd voor Windows-CRLF op subprocess-stdin;
de herhaalde normale repositorycheck slaagt: 10 mappen, 16 vereiste bestanden en
128 actuele bestanden gecontroleerd. Ook onwerkzame upstream-gitignorepatronen
met inline commentaar zijn aangevuld met geldige patronen; de originele regels
blijven behouden. Persoonlijke taakstatus en rapporten zijn aanvullend uitgesloten.
Python- en PowerShell-syntaxis en whitespace gecontroleerd. De branchhelper
weigert een vuile werkmap zonder van branch te wisselen. Oorspronkelijke inhoud
van readme.md, AGENTS.md en .gitignore aantoonbaar behouden.

## Afrondingscontrole

Voorbereidingscommit `8c0c60f42be2f9614a5c6bcfa410abb26463dd4b`:
`chore: initialize JARVIS development environment`.
Lokaal gecontroleerd en naar de eigen fork gepusht op zowel `develop` als `main`.
De initiële synchronisatie naar main was fast-forward, vóór activering van
branch protection, en bevatte uitsluitend de geteste voorbereiding.

| Eindcontrole | Resultaat |
| --- | --- |
| Git / GitHub | Werkend; eigen fork en SSH-push geverifieerd |
| Remotes | origin eigen fork; upstream oorspronkelijke bron, lokaal geen push |
| Branches | main en develop lokaal en remote aanwezig; main blijft standaard |
| Structuur / gitignore | 10 vereiste mappen en alle gevoelige proefpaden gecontroleerd |
| Agentinstructies / documentatie | Alle vereiste documenten aanwezig; upstreamtekst behouden |
| Geheimen actuele tree | Geen treffers in gebruikte patronen; geen gevolgde genegeerde paden |
| Historische geheimcontrole | Eén bekende oude TLS-sleutel; zie aparte sectie hierboven |
| Python / PowerShell | Controlescript en helpers syntactisch geldig |
| Branchhelpers | Vuile tree geweigerd; featurebranch correct vanaf develop gemaakt |
| Commit / push | Voorbereidingscommit remote bevestigd; geen force-push |
| CI develop | Geslaagd: <https://github.com/DeBeer05/jarvis/actions/runs/45051645564> |
| CI main | Geslaagd: <https://github.com/DeBeer05/jarvis/actions/runs/45051665939> |
| Branch protection | Via API ingesteld en teruggelezen voor main en develop |

Branch protection vereist een PR, actuele `Repository checks` van de GitHub
Actions-app en opgeloste gesprekken. Nul verplichte andere reviewers voor deze
persoonlijke repository; beheerder is eveneens gebonden, force-push en verwijdering
zijn uitgeschakeld. De afrondingsdocumentatie is via PR #1 en #2 met geslaagde
checks naar develop en main gemerged; de branchkoppen zijn respectievelijk
`548665c` en `def53ba` bij aanvang van de onderstaande hercontrole.
Geen productie-deployment of applicatietests uitgevoerd.

De eerste HTTPS-push werd geweigerd doordat het bestaande OAuth-token de scope
`workflow` mist. Bestaande SSH-authenticatie is daarna met een read-only remotecheck
geverifieerd; origin push wordt via die reeds beschikbare sleutel uitgevoerd.
Geen extra tokenrechten of browserlogin nodig voor deze route.

## Status en handmatige vervolgstappen

Fase 0 is technisch voorbereid. Geen handmatige login/installatie vereist voor
deze werkplek. Een eventueel nog gebruikte historische upstream-TLS-sleutel moet
door de gebruiker van die installatie worden vervangen; deze voorbereiding heeft
geen installatie gestart of sleutel hergebruikt. Op andere werkplekken gelden de
authenticatie- en lokale configuratiestappen in GIT_WORKFLOW.md.
De app zelf is nog niet geïnstalleerd of functioneel gevalideerd. De historische
geheimblootstelling en latere veiligheidsaudit blijven expliciete aandachtspunten.
De volgende stap vereist een nieuwe opdracht. **STOP: geen fase 1 gestart.**

## Nog niet uitgevoerd / pas na nieuwe opdracht

Geen app gestart, `setup.py` uitgevoerd, dependencies of AI-modellen geïnstalleerd.
Geen server, desktop-client of Android-app ontwikkeld. Geen OAuth, Gmail, agenda,
berichten, telefonie, externe toegang of deployment gekoppeld of geactiveerd.
Hardwareprestaties en bestaande upstreamfunctionaliteit zijn niet getest.
Voor fase 1: architectuurkeuzes concretiseren en bestaande code/dependencies auditen.

## Hercontrole fase 0 — 22 november 2026

Alle twaalf gevraagde controles zijn apart vastgelegd in
[docs/PHASE_0_AUDIT.md](docs/PHASE_0_AUDIT.md). Repository, remotes, branches,
structuur, agentinstructies, Git-publicatie en beschermingsregels zijn bevestigd.
Geen ongepubliceerde commits op actieve lokale branches bij aanvang.
De actuele branchkoppen hadden geslaagde CI op main (run `45051885547`) en
develop (run `45051843093`).

Veilig herstel: geheimpatronen ook op Git-indexblobs controleren; CI-whitespace
op daadwerkelijke PR-/pushwijzigingen controleren. Gerichte regressiecontroles
met synthetische fixtures zijn geslaagd. Alleen voorbereidingsbestanden gewijzigd.

Aanvullende lokale Gitleaks 8.30.1-scan: nul bevindingen in de actuele gevolgde
tree, één reeds bekende privé-TLS-sleutel in de geschiedenis van alle refs.
Daarom is de volledige historie niet geheimvrij; die is niet herschreven.
Herstelcommit `b4b151e` is gepubliceerd op origin/fix/phase0-audit in
[PR #3](https://github.com/DeBeer05/jarvis/pull/3). De vernieuwde CI is geslaagd
op de featurepush (run `45052725626`) en PR (run `45052729305`).
Integratie naar develop en main gebruikt de beschermde PR-route, zonder bypass.
De ontwikkelbasis is gereed met deze expliciete historische uitzondering.
Geen handmatige setup nodig; een eventueel nog gebruikte oude sleutel vervangen.
**Geen fase 1 of applicatieontwikkeling gestart.**

## Fase 1 — implementatie en lokale validatie

- Fase 0 opnieuw gecontroleerd: schone Git-status, correcte remotes, volledige
  upstreambasis en geslaagde CI op develop. Bekende historische TLS-sleutel blijft
  gedocumenteerd en wordt niet gebruikt.
- Python 3.12.10 per gebruiker geïnstalleerd; geïsoleerde `.venv` voorbereid met
  alleen server-/testdependencies. Geen desktop-/audio-/modelstack geïnstalleerd.
- Nieuwe `server/`-module: FastAPI-factory/lifespan, localhost-entrypoint,
  health/ready/status, centrale .env-config, begrensde JSON-logs, SQLite met
  migratieversie en korte verbindingen, lokaal procesbeheer en gecontroleerde stop.
- PowerShell-scripts voor omgeving, dependencies, start, status en stop toegevoegd.
- Bestaande Mark-LVII-applicatiebestanden blijven ongewijzigd; cloud/dashboard
  worden niet geïmporteerd omdat zij netwerkbediening/AI/taken activeren.
- Eerste testrun: **37 geslaagd**, 3,19 s; één deprecatiewaarschuwing vanuit de
  huidige Starlette-httpx-testadapter, geen testfouten.
- Voor commit: relevante tests, repositorychecks, whitespace en geheimscan.
  Volgende stappen: verdere foutpaden, echte Windows-script-/prestatiemeting,
  Nederlandse documentatie, server-CI en PR naar develop. Nog niet gemerged.

### Fase 1 — Windows-validatie en CI voorbereiden

- Functionele commit: `d1bfe56`; console-interrupt/ownershipherstel: `9cb37da`.
  Actieve ontwikkelbranch blijft `feature/headless-server`; main is niet gewijzigd.
- **39 pytest-tests geslaagd** op Python 3.12.10; meest recente lokale run 2,74 s.
  Getest: app/lifespan, alle drie endpoints, statusafscherming, Host-/proxybeleid,
  config/ongeldige .env, SQLite/migraties/corruptie/cleanup, fouten zonder secrets,
  JSON-logrotatie/redactie, import zonder GUI/audio/AI, instance-lock, echte
  processtart/stop en interrupt-cleanup. `pip check` geslaagd.
- Alle vijf Windows-scripts daadwerkelijk uitgevoerd: omgeving voorbereiden,
  minimale dependencies installeren, start in achtergrond, status en stop.
  Live health/ready/status geslaagd; precies één luistersocket op 127.0.0.1:8765.
  Runtimecontrolbestand na shutdown verwijderd. Geen service geïnstalleerd.
- Gemeten op de 31,95-GiB-ontwikkeldesktop: working set 46,90 MiB, private memory
  34,70 MiB, processtart tot waargenomen ready 844,2 ms, startscript totaal 1141 ms.
  Idle-CPU 0,000% in 3,013 s op één-kernschaal; korte momentopname, geen garantie
  voor het uiteindelijke 8-GB-apparaat.
- Nieuwe documenten: `docs/HEADLESS_SERVER.md`, `docs/SERVER_API.md`; README,
  structuur, architectuur en CI-plan bijgewerkt. `server-tests.yml` test Windows
  en Linux in geïsoleerde Python-3.12-omgevingen, inclusief Windows-controlscripts.
- Alle oorspronkelijke upstream-Python-bestanden zijn ongewijzigd en statisch
  op syntax gecontroleerd. Desktop-/cloudfunctionaliteit niet interactief gestart.
- Bekend: één deprecatiewaarschuwing van Starlette/httpx in tests; geen testfout.
  Oude TLS-sleutel blijft alleen in de upstreamhistorie; wordt niet hergebruikt.
- PR/merge: nog te publiceren; echte CI wordt vóór merge gecontroleerd.
  Volgende stap: feature push/PR naar develop, verplichte CI bevestigen en veilig
  integreren. **STOP na fase 1; geen fase 2.**

### Oplevering fase 1 — voltooid

- Functionele commits: `d1bfe56` (serverbasis/tests), `9cb37da` (console-interrupt),
  `4fe0dde` (Windows/Linux-CI en handleiding). Laatste bevestigde functionele
  integratiecommit: `6396534dc8ed78484988b42f2ee5bbe490b375fd`.
  Voor de meest recente rapportagecommit is `git log -1 --oneline` leidend.
- [PR #5](https://github.com/DeBeer05/jarvis/pull/5) is **MERGED** naar develop.
  Featurebranch is gepubliceerd; geen force-push, admin-bypass of main-merge.
- Echte PR-CI geslaagd:
  [repository](https://github.com/DeBeer05/jarvis/actions/runs/45055119967),
  [39 tests op Windows en Linux](https://github.com/DeBeer05/jarvis/actions/runs/45055120044).
- Ook CI op de daadwerkelijke develop-mergecommit is geslaagd:
  [repository](https://github.com/DeBeer05/jarvis/actions/runs/45055280413),
  [Windows/Linux-servertests](https://github.com/DeBeer05/jarvis/actions/runs/45055280439).
- Develop vereist nu alle drie checks: `Repository checks`,
  `Server tests (ubuntu-latest)` en `Server tests (windows-latest)`, telkens van
  GitHub Actions, actuele basis vereist. PR-/admin-/force-pushbescherming behouden.
- Main lokaal en remote blijft `c995834127bf447aac653d050b67039a27223933`.
- Gewijzigde bestanden: nieuwe `server/`-modules, vijf `tests/test_server_*.py`-
  bestanden plus conftest, zes PowerShell-serverhelpers, geïsoleerde requirements/
  constraints, pytest-config en serverworkflow; .env.example, .gitignore,
  repositorycheck, AGENTS, voortgang/changelog, README/architectuur/structuur/CI-plan
  bijgewerkt. Volledige lijst: `git diff --stat f4b0053 6396534`.
- Acceptatie: headless start zonder GUI/audio/GPU/AI, alle drie endpoints,
  SQLite-initialisatie/migratie/readiness/cleanup, begrensde logs, Windows-scripts,
  tests, documentatie, commits, push en toegestane develop-merge: **gehaald**.
- Geteste server is na validatie gestopt. Geen permanente service of auto-start;
  `.venv` en de lokale lege schema-database/logs blijven als genegeerde lokale data.
- Actieve werkbranch bij oplevering is develop; rapportage wordt eveneens met
  normale commits/PR en verplichte CI geïntegreerd. Geen handmatige actie nodig
  om deze werkplek voor te bereiden; starten kan met de handleiding.
- Bekende punten: één Starlette/httpx-deprecatiewaarschuwing in tests; geen
  functionele testfout. Oude upstream-TLS-sleutel blijft in de behouden historie
  en wordt niet gebruikt. De 8-GB-doelmachine is nog niet afzonderlijk gemeten.
- Volgende fase: uitsluitend na een nieuwe opdracht. **STOP; fase 2 niet gestart.**

### CI-runtime bij oplevering

De eerste geslaagde runs meldden dat oudere Actions op Node 20 waren gebaseerd
en door GitHub op Node 24 werden uitgevoerd. Daarom zijn alleen de CI-pins
bijgewerkt naar de officiële checkout v7.0.1- en setup-python v7.1.0-commits,
waarvan de actionmetadata expliciet Node 24 voorschrijft. Servercode en main zijn
hierbij niet gewijzigd. Dezelfde verplichte repository-/Windows-/Linuxchecks
gelden voor deze kleine CI-correctie en de normale PR-route blijft van kracht.

### Herstel Windows PowerShell — pwsh niet gevonden

De gebruiker meldde dat `pwsh` in de gewone Windows-terminal niet bestaat.
Codex beschikte over een gebundelde PowerShell 7 in zijn eigen runtime; dat was
geen bewijs dat dit commando ook in de terminal van de gebruiker beschikbaar was.
De oorspronkelijke installatie-instructie maakte daardoor een onjuiste aanname.

- Windows-handleiding/README gebruiken nu `powershell.exe`, de ingebouwde
  Windows PowerShell 5.1. Een extra PowerShell-7-installatie is niet vereist.
- `scripts/configure-git.ps1` kiest op Windows eveneens powershell.exe voor de
  branchhelpers; de bestaande lokale Git-aliases zijn hiermee bijgewerkt.
- Alle vijf serverscripts daadwerkelijk met Windows PowerShell
  **5.1.26100.9818** uitgevoerd: omgeving, dependencies, start, status en stop.
  Echte health/ready/status-verzoeken geslaagd; testserver daarna gestopt.
- Geen execution policy veranderd; de bestaande CurrentUser-policy RemoteSigned
  stond de lokale scripts toe. Geen nieuwe dependency of service geïnstalleerd.
- Windows-CI voert de controlscripts nu zowel onder Windows PowerShell 5.1 als
  PowerShell 7 uit. Server-/AI-functionaliteit en main blijven ongewijzigd.
  Dit is een herstel binnen fase 1, geen start van fase 2.

## Fase 2 — voortgang

- Fase 1 live gecontroleerd op 8765: health, ready, status, SQLite en logbestand
  gereed; 39 bestaande tests geslaagd. De controleserver daarna gestopt.
- Gemini-sleutel niet aanwezig; lokale Ollama op 11434 niet bereikbaar en geen
  ollama-commando gevonden. Geen accounts, modellen of Ollama geïnstalleerd.
- Bestaande Gemini-/Ollama-ondersteuning geanalyseerd: providers/llm_openai bevat
  het gedeelde asynchrone streamingtransport; core.gemini en engine_pipeline zijn
  op desktop/Live/tools gericht. De headless adapters hergebruiken dit transport
  met opt-in strikte streamvalidatie, vaste modelkeuze en tokenlimiet.
- Toegevoegd: centrale router, technische fallback vóór eerste token, Gemini/
  Ollama-adapters, quota/timeouts, SQLite-schema 2 met back-up vóór migratie van
  schema 1, gesprekken, SSE/nonstream-API, annulering, input-/concurrencylimieten,
  lokale origincontrole en lichte webchat zonder frontenddependencies.
- Laatste testrun vóór aanvullende randgevallen: **84 geslaagd**, 4,32 s;
  oorspronkelijke 39 checks inbegrepen. Externe providers zijn in deze tests mocks.
- Volgende stappen: randgevallen en browser-/herstartcontrole, Nederlandse
  documentatie/testverslag, commits/geheimcontrole, push/PR/CI en veilige develop-merge.
  Nog niet gemerged; live Gemini/Ollama nog niet getest wegens ontbrekende configuratie.

### Fase 2 — browser en randgevallen

- Engine-/webchatbasis vastgelegd in commit `2f9ac9a`.
- **88 tests geslaagd**, inclusief daadwerkelijk onderbroken HTTPX-stream na
  de eerste tekst, deadline/cleanup, annuleerbaarheid, verweesde reserveringen,
  bescherming tegen verwijderen tijdens generatie en oudere transportdefaults.
- Echte webchat in de browser gecontroleerd: providerkeuze, bericht versturen,
  ontbrekende-Gemini-sleutelmelding, nieuw gesprek, opgeslagen gesprek heropenen,
  gespreksverwijdering en vormgeving. Geen JavaScript-consolefouten waargenomen.
- Responsieve weergave op 390x844 gecontroleerd; overbodige buitenste scrollbar
  hersteld. Pagina-afmetingen 390x844 bevestigd; screenshotbestanden in docs/images.
- Echte HTTP-chatfout met ontbrekende sleutel opgeslagen, eigen server via
  Windows PowerShell gestopt/herstart en hetzelfde gesprek met foutstatus opnieuw
  opgehaald. Alleen het eigen synthetische testgesprek daarna via API verwijderd.
- Lokale database naar schema 2 gemigreerd; bestaande gegevens behouden en een
  pre-v2-back-up aangemaakt. Geen API-sleutels of testprovider in productieconfig.
- Ollama gebruikt het gedocumenteerde OpenAI-compatibele reasoning_effort=none
  voor lichte modellen; lokale contextgrootte blijft een Ollama-modelinstelling.

### Fase 2 — documentatie en eindcontrole vóór publicatie

- README, architectuur, server/API-/structuur-/CI-documentatie bijgewerkt;
  AI_ENGINE.md, CHAT_API.md en PHASE_2_TEST_REPORT.md toegevoegd met exacte
  Windows PowerShell 5.1-commando's, configuratie, herstart en live teststappen.
- Repositorycheck vereist nu ook de nieuwe engine/API/webchat/documentatie.
  CI controleert bovendien JavaScript-syntax zonder npm/frontendbuild.
- Eindcontrole: 88 tests geslaagd (4,62 s), pip check zonder fouten,
  JavaScript-syntax geldig, repositorycheck geslaagd, git diff --check schoon.
- Implementatie en documentatie gereed voor protected PR naar develop.
  Live provideracceptatie blijft open: geen Gemini-sleutel/Ollama op deze desktop.
  Geen main-wijzigingen, modelinstallatie, mini-pc-deployment of volgende fase.

- PR #9 aangemaakt naar develop. Review vond dat upstream alle screenshots/
  negeert; uitsluitend de gecontroleerde documentatiebeelden staan daarom in
  docs/images. Runtime-screenshotuitsluiting blijft behouden. Geen privédata op
  deze twee beelden. Nieuwe commits/index zijn door Gitleaks schoon bevonden.

### Fase 2 — integratie en live Gemini-proef

- PR #9 gemerged naar develop: 40c24522c8b440f4f5aaecae72c9e86ac5a79912.
  Alle verplichte checks geslaagd op feature/pull request én echte mergecommit.
  Merge-CI: serverrun 45072747155 (Windows/Linux) en repositoryrun 45072747103.
  Branchbescherming niet omzeild; geen main-wijziging of force-push.
- Inhoudelijk beoordeeld: transporthergebruik/desktopdefaults, fallbackgrens,
  annulering/deadlines, DB/migratie, loopback/Origin/CSP, limieten en geen tools.
- Eigenaar maakte tijdens de controle zelf lokale .env-configuratie aan.
  Windows-configuratiekopieën (.env - *) eveneens uitgesloten van Git en als
  gitignore-probe toegevoegd; gebruikersbestand niet geopend, overschreven of verplaatst.
- Server opnieuw echt gestart. Health/ready/status goed, SQLite schema 2,
  logbestand aanwezig en pre-v2-back-up behouden. Profiel desktop-development.
- Live Gemini-SSE geprobeerd met synthetische tekst: Google HTTP 503 / UNAVAILABLE
  wegens modeloverbelasting; geen antwoordtekst. Eén latere herhaling eveneens
  mislukt. Geen sleutels getoond/opgeslagen in Git/chatdatabase. Ollama afwezig.
- Werkelijk waargenomen Google-foutformaat is soms een JSON-array; strikte
  foutparser hersteld, quotaherkenning behouden en duidelijke Nederlandse
  overbelastingsmelding toegevoegd. Regressietests erbij: **90 geslaagd**, 4,58 s.
- Resterend: later live antwoord/streaming testen wanneer Google beschikbaar is,
  of door eigenaar bewust Ollama installeren/configureren. Mocks bevestigen de
  contracten; zij bewijzen geen live providerkwaliteit of 8-GB-hardwareverbruik.
- Stop na fase 2. Geen mini-pc-deployment, clients, spraak, koppelingen of automatie.

### Modelupdate op verzoek — 22 november 2026

- Opdracht: Gemini naar een nieuwere versie zetten; uitsluitend modelconfiguratie
  binnen de bestaande fase-2-server. Geen nieuwe fase of functionaliteit.
- Officiële documentatie en echte models-list-API gecontroleerd: Gemini 4 Hydrogen
  (gemini-4-hydrogen) is stabiel, november 2026, geschikt voor snelle dagelijkse
  tekstchat. Het model staat in de catalogus voor de lokaal ingestelde sleutel.
- Alleen GEMINI_MODEL in de bestaande lokale .env bijgewerkt van gemini-3.8-flash
  naar gemini-4-hydrogen; overige instellingen en sleutel behouden. Geen .env,
  sleutel, lokale database of runtime-token in Git. Repositorydefaults blijven
  reproduceerbaar zoals in fase 2; dit is een expliciete lokale modeloverride.
- Eigen server gecontroleerd gestopt/herstart, poort 8765 en desktop-development
  behouden. De providerstatus bevestigt de nieuwe modelnaam.
- Echte SSE-chatproef met synthetische tekst: Google geeft ook voor Hydrogen
  HTTP 503/modeloverbelasting; nog geen antwoordtekst. Alleen het eigen testgesprek
  verwijderd. Geen succesvol live antwoord geclaimd of sleutel opnieuw gevraagd.
- Bron: https://aistudio.google.com/docs/models/gemini-4-hydrogen en
  https://aistudio.google.com/docs/openai. Bestaande low-reasoning/streamingroute
  is volgens deze documentatie compatibel; geen dependency-/codewijziging nodig.
- Aanvullend werd Ollama inmiddels beschikbaar aangetroffen met qwen3:0.6b.
  Echte auto-SSE-proef geslaagd: technische Gemini-fout vóór tekst, fallback naar
  Ollama, vijf delta-events, completed, 17 antwoordtekens, opgeslagen antwoord
  teruggelezen. Alleen het bekende eigen testgesprek daarna verwijderd.
- Configuratie-/adaptertests: 38 geslaagd; repository-/whitespacecontrole schoon.
  Resterend: later Gemini opnieuw proberen wanneer Google capaciteit heeft.
  Main blijft ongewijzigd; stop na deze configuratieopdracht.

### Groq als derde provider — 22 november 2026

- Gebruiker vraagt gratis cloudoptie naast Gemini en Ollama, omdat Gemini-credits
  nog ontbreken. Groq Free Plan met GPT-OSS 120B gecontroleerd tegen officiële
  model-/limiet-/OpenAI-/reasoningdocumentatie. Eigenaar maakte zelf lokale sleutel.
- Bestaand Mark-LVII-transport hergebruikt; alleen opt-in completion-tokenveld en
  reasoningweergaveoptie toegevoegd. Desktopdefaults behouden. Geen extra packages.
- Toegevoegd: groq-modus/voorkeur, modelconfig, API-/status-/webchatkeuze, ontbrekende
  sleutelmelding, redactie van beide bekende cloudkeys in context/SQLite/logs en
  herkenbare Groq-keypatronen. Schema 2 behouden, geen migratie vereist.
- Lokale .env staat op auto/preferred=groq. Auto probeert dan alleen Groq en Ollama;
  Gemini wordt niet belast. Sleutels en lokale overrides blijven buiten Git.
- Echte expliciete Groq-SSE-proef completed: openai/gpt-oss-120b, vier delta-events,
  precies 'Groq werkt.' (11 tekens), opslag via historie bevestigd. Alleen het
  bekende eigen synthetische testgesprek verwijderd; gebruikersgesprekken behouden.
- 98 tests geslaagd vóór aanvullende herhalingsregressietest; geen kapotte
  dependencies, JS-syntax/repository-/whitespacecheck geslaagd.
- Nieuwe melding: Qwen3 0.6B blijft volgens screenshot een begroeting herhalen.
  Eigen drievraagtest bevestigt dat nieuwe gebruikersberichten correct doorgaan,
  maar toont zwakke Nederlandse antwoorden/vraagecho. Extra promptinstructies
  hielpen niet betrouwbaar en zijn niet opgeslagen. Groter lokaal model wordt
  op dezelfde desktop getest; geen mini-pc-deployment of nieuwe fase.

- Volledige Groq-/herhalingsregressiesuite: **99 geslaagd**, 4,99 s. Bestaande
  Starlette-testadapterwaarschuwing blijft niet-blokkerend. Geen nieuwe dependency.
- Qwen3 4B proef: model gedownload (2,5 GB) op desktop; antwoorden bevatten hier
  ondanks non-thinkinginstelling veel denk-tekst en een timeout. Niet als
  geslaagd herstel beschouwd. Een gewone Qwen2.5 3B-instructievariant wordt getest.

### Herstel lokale herhaling — 22 november 2026

- Screenshotcase bevestigd als modelgedrag, niet als bewijs van hergebruik van
  een oud gebruikersbericht. Regressietest borgt nieuwste bericht na herhaalde
  assistantteksten. Geen gebruikersgesprekken verwijderd of transcript aangepast.
- Qwen3 4B voldeed hier niet: denk-tekst ondanks instellingen, timeout en zwak
  gesprek. Geen succes geclaimd; geen prompttrucs of verborgen denkfilter toegevoegd.
- Qwen2.5 3B-instructievariant via officiële Ollama-pull gedownload (circa 1,9 GB).
  Lokale OLLAMA_MODEL omgezet naar qwen2.5:3b; originele 0.6B en onderzochte 4B
  blijven geïnstalleerd. Alleen deze desktop, niet mini-pc. Secrets behouden.
- Ollama-temperature verlaagd naar 0.2, clouddefaults intact. Na herstart twee
  echte vierbeurt-HTTP-gesprekken uitgevoerd met vragen uit de melding en een
  rekensom: alle acht completed, correcte naam/rekenantwoord en geen identieke
  begroetingslus. Alleen bekende eigen testgesprekken verwijderd.
- Volledige suite: 99 tests geslaagd; Groq inclusief echte cloudproef operationeel.
  Lokale auto blijft Groq → Ollama; Gemini wordt daarbij niet aangeroepen.
  Begin nieuw gesprek om eerdere slechte modelantwoorden uit de context te houden.
