# Ontwikkelvoortgang

## 28 november 2026 — hybride vervolgopdracht in uitvoering

Nieuwe opdracht verleent expliciet Oracle-installatie/gateway en een mini-pc-pakket;
de oudere fasegrenzen hieronder blijven historische context. Mini-pc ontbreekt:
geen persoonlijke migratie/cutover uitgevoerd. Geen nieuwe betaalde resources.

- Bevestigingen wachten direct op geverifieerde uitvoering; korte CalendarUpdate-
  vraag en succesmelding. Publieke weer/nieuws/NDW-reads zonder model; nieuwe
  onderwerpen verwijderen oude ja-bindingen. Expiratie/wijziging sluit voorstellen.
- Oracle ARM64: 2 CPU/12 GB; Ollama v0.40.19 met localhostbinding, beperkte resources,
  systemd-herstart; vier modellen werkelijk gemeten. Qwen2.5:3B blijft standaard;
  redeneernauwkeurigheid van kleine CPU-modellen blijft een aangetoonde beperking.
- Caddy met geldig openbaar HTTPS-certificaat; beperkte SSH-linkgebruiker, uitsluitend
  twee loopbackforwards. AI/databasepoorten niet publiek. Persoonlijke DB lokaal.
- Echte HTTPS/SSH/Oracle-proef met wegwerpaccount: TLS/CSRF/cookies/login/401/SSE
  geverifieerd. Eerste antwoord 62,74 s met volle context, 14,45 s met compacte
  stockcontext. Zie docs/HYBRID_BENCHMARKS.md voor omvang/beperkingen.
- SQLite v15: apparaat-heartbeats, gebonden opdrachtleases, eenmalige start,
  onzekere uitkomsten bij verlopen gestarte leases. Windows-worker hergebruikt de
  gesloten hostadapter en lokale receipts; ontvangst blijft expliciete owner-opt-in.
- Trage spraakaanvragen geven na 1,25 s een korte voortgangszin, zonder
  succesclaim; berichttekst en annulering blijven afzonderlijk geverifieerd.
- Windows-paneel voor toegestane programma's/mappen en verbindingsstatus; Android
  Oracle-keuze en bijgewerkt instellingencontract. Geen nieuwe Android-grants.
- Mini-PC-builder en lifecycle-scripts toegevoegd, inclusief DPAPI-machineopslag,
  back-ups, herstel dat oude sessies/taakapprovals intrekt en taken pauzeert,
  versioned updates met rollback, Nederlandse installatiegids en CI-artifact.
- Geïsoleerde Windows PowerShell 5.1-installatie: dependencies, venv, schema,
  DPAPI, readiness en gecontroleerd stoppen daadwerkelijk geslaagd. SYSTEM-taak,
  fysieke mini-pc en accounts zijn hiermee nog niet bewezen. Testvariant die de
  administratorcheck zou overslaan is door automatische review geblokkeerd;
  die wijziging is niet uitgevoerd en controles blijven behouden. Ook een
  voorstel voor automatische OpenSSH-/Microsoft-runtimeinstallatie werd geblokkeerd
  zonder nadere reden; officiële handmatige stappen staan in INSTALLATIE.md.

Tussenstand controles: 698 servertests + 1 Windows-skip; gerichte vervolgproeven
42 context/spraak, 35 hybride tests en 15 aanvullende cache/queue/package-proeven
zijn groen. CI-installatiepakket en Windows-build slagen. CI vond drie focus-/leesvraagregressies;
98 gerichte tests slagen na het herstel. De actuele volledige CI-uitkomsten en geteste artifacts staan bij
https://github.com/DeBeer05/jarvis/pull/33. Linux/ARM, Windows-client en de
geïsoleerde package-installatie hebben inmiddels echte geslaagde runs.
Windows 153 tests groen. Android unit/lint/debug/release gebouwd; nog niet als
nieuwe APK op fysieke hardware geverifieerd. Menselijke luisteracceptatie blijft open.
Backend op de ontwikkeldesktop gecontroleerd herstart op 8765: schema v15,
quick_check ok en automatische pre-v15-snapshot geverifieerd. Originele stem,
accountinstellingen en grants behouden. Gemeten backend-idle-RSS circa 70,6 MiB.
De herhaalde echte compacte HTTPS-proef varieerde van 14,45 tot 19,95 s; geen
algemene subsecond-claim voor vrije modelgesprekken. De twee bestaande
maildigest-eigenaarsdiffs blijven onveranderd en ongecommit.


## Huidige opdracht

### Acht productfases persoonlijke butler — 27 november 2026

Finale lokale verificatie: **670 servertests passed, 1 POSIX-skip**, **150 Windows-
clienttests passed**, Android 11 unit tests/lint/debug/release groen; contract,
Ruff/mypy, beide pip-checks, structuur, whitespace en gitleaks groen. De vier
browserregressies zijn hersteld en de volledige reeks opnieuw uitgevoerd.
Bronstart vanuit een andere werkmap mist niet langer providers.speech_format;
directe offscreen-startsmoke toont acht pagina's zonder netwerk/microfoon/helper.
CI-Windows-build en bundle-smokes op 806d421 geslaagd. De workflow bewaart voortaan
het geteste portable archief als artifact; actuele definitieve checks staan in PR33.
Lokale PyInstaller-append blijft door PermissionError geblokkeerd; geen security-
aanpassing. Bestaande snelkoppeling verwijst naar de geteste bronclient, originele
shortcut is lokaal bewaard. Er is na de gebruikers-Escape geen vensterbediening
meer uitgevoerd; echte zicht-/spraakacceptatie blijft open.
Backend gecontroleerd herstart op loopback:8765; SQLite v14, integriteit en pre-v14-
backup geverifieerd. Alleen expliciet opgegeven gewone briefingvoorkeuren lokaal
toegepast: twee dagelijkse inboxjobs geverifieerd, bestaande stem ongewijzigd,
geen calls/nieuwe grants/accounttest. APK gereed, geen aangesloten adb-apparaat.
Alle acht technische fases zijn verwerkt; externe/OS-consentgrenzen staan in de
praktische handleiding. Geen Oracle-/mini-pc-cutover. Eigenaarmaildiffs blijven apart.

Fase 8 geïmplementeerd: native ButlerPanel + getypeerde formulieren, Android Butler/
Beeldcontext/Apparaat, echte previewwiring, aparte OS-/apparaatconsents, schema-
gedreven autonomie met advies/profielregels en expliciete vraagplicht, prioriteit/
deadline/undo, taak-health/inboxgeschiedenis en eigenaarformulieren HA/Windows.
Native-queryallowlist uitgebreid met uitsluitend de benodigde begrensde routes.
Geen keys in clients of automatische grants. De bestaande topnavigatie blijft.
Windows 148 passed + finale query/core/windowreeks 41 passed. Android 11 unit/lint/
debug/release groen. Brede serverreeks 665 passed/1 POSIX-skip/4 JS-harnessfouten;
veroorzaakt door overbodige DOMContentLoaded-afhankelijkheid in reeds deferred
script, hersteld. Alle 12 web-/interfacechecks daarna groen; 20 eerdere API/
presence/stopchecks groen. Definitieve CI wordt na push gecontroleerd.
Lokale exe-verpakking tweemaal PermissionError bij PyInstaller append; geen
beveiligingsinstelling aangepast. Bestaande Python-client blijft beschikbaar.
APK gebouwd; adb ziet op dit moment geen aangesloten apparaat. Niet geïnstalleerd.
Lokale activatie/briefingconfiguratie en uiteindelijke CI-status volgen hieronder.

Fase 7 technisch gereed: SQLite v14, persistente eigenaarnoodstop/epochs,
taakprioriteiten/deadlines, advies/vragen/toestaan/blokkeren per functie,
begrensde leesretries en aparte hostgrants voor media/programmas. Geen nieuwe
runtimegrants. Herstel maakt verse CalendarDelete-/afsluitannuleringvoorstellen,
met event-ID/etagcontrole; geen blinde externe undo. Audit/inbox atomair gekoppeld,
stop-event op beide clients en annulering van lopende audio/beeldvragen.
Brede serverreeks: 662 passed, 1 POSIX-skip, 1 fout in overbodige handoffmelding;
die fout hersteld en alle 14 betrokken finale tests passed. 17 policy/geheugentests
en 60 chatregressies passed; Windows 143 passed; Android unit/lint/beide builds
groen. Ruff/mypy/pip/repository groen. Alle 12 CI-checks op 8507202 groen.
Volgende: fase 8 UI, finale volledige regressie, builds en lokale activatie.

Fase 6 technisch gereed: HA REST/HTTPS met allowlist/aliassen en echte status-
verificatie; ORS/geocodering/handmatige ritkosten via bestaande registry/vault.
Geen geverifieerde publieke Creality Hi-status-API, live verkeer/pompprijzen of
voertuigtelemetrie. Beeldcontext: expliciete opt-ins/previewrevision, gevalideerde
PNG, dagbudget, geen beeldopslag/tools; SQLite v13. Bestaande AI-router en Qt/
Android-componenten hergebruikt, geen modeldownload of nieuwe dependencies.
654 servertests/1 skip; laatste gerichte reeks 33 passed. Windows 142 passed +
3 finale previewtests; Android 11 tests/lint/debug/release groen. Niet live;
credentials, menselijke beeld-/apparaatacceptatie en fase-8-wiring nog apart.
Fase-5-head 1ce31cb alle 12 CI-checks groen. Volgende: betrouwbare autonomie.

Fase 5 technisch gereed: gesloten Windows-hostacties en Downloads-events,
CPU/RAM en optionele bestaande NVIDIA NVML-sensoren; Android getypeerde
apphandoffs, opt-in WorkManager, meldingsaantallen en batterij/laatst bekende
locatie met afzonderlijke toestemmingen. SQLite v12/backup, bronrevisies,
approvals/policyfingerprint/eenmaligheid en onzeker resultaat blijven leidend.
642 servertests passed/1 POSIX-skip; na laatste SDK/expiry/parent-stopwijzigingen
13 gerichte tests passed. Android 11 unit tests, lint/debug/release en kwaliteit
groen. Geen echte oproep/bericht of automatische grant; nog niet live.
Fase-4-head 096b87a alle 12 CI-checks groen. Volgende fase: externe integraties.

Fase 4 technisch gereed: opt-in incrementele STT op beide clients met 500 ms
overlap, één request tegelijk, laatste audiodeel en uitsluitend finale uitvoering.
Voorlopige requests verlopen na acht seconden; late/cancelled tekst blijft weg.
Bestaande ElevenLabs/zinsstreaming/echo/leases hergebruikt, geen modeldownload.
140 clienttests, 28 gerichte server/ElevenLabs-tests, Android-tests/lint/beide builds,
Ruff/mypy, contract en dependency-/repositorychecks geslaagd. Nog niet live;
menselijke luisteracceptatie apart. Volgende fase: Windows-/Android-integratie.

Fase 3: brongebonden briefings, begrensd openbaar weer/nieuws, lokale lijsten,
gelegenheden/routines en sollicitatie-opvolging via bestaande engine; SQLite v11.
Brede regressie 629 passed/1 skip; laatste gerichte automation/briefingtests
37 passed, kalender/briefingreeks 60 passed. Kwaliteit/contract/dependencies groen.
Ochtend/avond voorlopig in JARVIS op verzoek; bellen/verkeer/bank niet beschikbaar.
Persoonlijke configuratie blijft buiten Git. Backend nog niet herstart voor deze
uitbreiding; apparaatacceptatie en fase-8-formulieren volgen. Volgende fase: spraak.

Fase 1 checkpoint 25410ad. Fase 2 voegt gedeelde modi, opt-in aanwezigheid,
persistente terugkomst en lokale/no-history privémodus toe. Windows WTS/idle/
procesclassificatie en Android foreground lock/idle; achtergrond volgt fase 5.
617 servertests/1 skip, 136 clienttests, Android-tests/lint/debug/release groen;
echte apparaatacceptatie apart. Nieuwe parameters, routes en SQLite v10 behouden
8765 en bestaande rechten. Verdere voortgang staat in IMPLEMENTATION_PLAN.md.

Nieuwe vervolgopdracht implementeert de productfases uit IMPLEMENTATION_PLAN.md.
AGENTS verduidelijkt scope zonder nieuwe grants of Oracle/productiemigratie.
Branch feature/personal-butler bouwt op ea09cb6/PR 32 omdat develop deze basis
mist; bestaande maildiffs blijven apart. Fase 1 gebruikt bestaande managers en
voegt opt-in episodische retrieval toe: FTS5, privacy-/apparaatisolatie,
bronvergeten en migratie v9 met automatische backup. Geen embeddings/modelcall.
Gerichte regressies en Ruff/mypy geslaagd; volledige regressie wordt gevolgd.
Fasevolgorde en externe afhankelijkheden blijven expliciet in het plan.

### Blijvende persoonlijke butlerstijl — 27 november 2026

Classic Butler gebruikt vloeiend, kalm Nederlands met u/uw, tact, bescheiden
Britse humor en contextueel initiatief binnen bestaande rechten. `always` maakt
meneer per antwoord instelbaar; off/occasionally blijven compatibel. Gesloten
voorkeurcommando kan deze keuze blijvend opslaan zonder modelcall/automatisering.
Vertrek/terugkomst vereisen beschikbare context en bewezen ontwikkelingen,
zonder verzonnen achtergrondbewaking of nieuwe bevoegdheden. Bestaande managers,
schema en clients hergebruikt. Voorkeur via aangemelde Windows-interface opgeslagen
en teruggelezen (revisie 8), stem-/privacy-/meldingsrechten ongemoeid gelaten.
39 gerichte regressies, Ruff, pip check en repositorycheck geslaagd. Volledige
tests/remote CI volgen; menselijke beoordeling van toon blijft afzonderlijk.
Vorige agenda-HEAD 50cd7f0: 602 passed/1 skip en alle 12 CI-controles groen.

### Structureel agendagesprek en Nederlands STT — 27 november 2026

`fix/calendar-dialogue` is gestapeld op e6bff7c/PR 31; develop mist nog deze basis.
Eigenaarmaildiffs zijn intact en blijven buiten commits. Expliciete vervolgopdracht
staat persoonlijke, deterministisch gevalideerde CalendarCreate/Update toe met
actuele read/write/approve-rechten. Ask/block-beleid blijft gelden; uitnodigingen,
series, verwijderingen en mail houden hun bestaande approval. AGENTS verduidelijkt
deze nieuwe uitzondering. Geen echte Google-acties of ElevenLabs-proeven uitgevoerd.

Oorzaken: activiteitrouter zag titels als planning; vragen/‘ja’ hingen aan laatste
chatberichten; kalendercontext verloor eventreferenties; VAD/decoderuitvoer kon
tijdwoorden interpunctie of samengeplakte titelmarkers geven. Herstel hergebruikt
TaskMemory, AutomationEngine, ApprovalManager en dezelfde speechhelper op 8765.
Datum/begintijd/titel volstaan; standaard 60 minuten/standaardagenda. Amsterdam
en serverklok bepalen relatieve dagen. Eigen event-ID/verse etag, PATCH en
geverifieerd API-resultaat bepalen wijzigingen en bevestigingen. Veranderde
payloads krijgen geen directe autorisatie; afgebroken externe acties blijven
onzeker en worden niet blind herhaald. Pending referenties bewaren geen nonces.

203 gerichte regressies en 18 nieuwe gesprekscontracten geslaagd; Ruff/mypy,
pip-, contract- en structuurcheck geslaagd. 130 clienttests geslaagd met sys-capture;
een eerdere offscreen-Qt-abort blijft als bestaande testbeperking gedocumenteerd.
Lokale Piper→Whisper-proef met vier synthetische Nederlandse uitingen uitgevoerd,
zonder download/API-kosten; geen bewijs voor menselijke microfoonacceptatie.
Laatste volledige lokale regressie: 598 passed/1 POSIX-skip; extra agendaselectie
geslaagd. Windows-build/helper-rooktest geslaagd; backend herstart (ok/ready),
snelkoppeling bijgewerkt. Remote CI volgt afzonderlijk.
Oracle-installatie/migratie blijft uitgesteld en vereist afzonderlijk akkoord.

### ElevenLabs premium stem en Oracle-voorbereiding

Vervolgopdracht 25 november: `feature/elevenlabs-voice`, gestapeld op de actuele
planningbranch c320d7a/PR 30 omdat develop de fase-7.5-basis nog niet bevat.
Origin gecontroleerd; eigenaarmaildiffs blijven buiten de wijziging, zonder
stash/reset. Nieuwe opdracht autoriseert ElevenLabs en read-only Oracle-inspectie/
ARM64-voorbereiding; §15/§16 vereisen goedkeuring vóór remote installatie en
productiemigratie. Die specifieke grens staat ook in AGENTS.md.

TTS-router, instellingen, zinsstreaming en native clients hergebruikt. Sleutel
via DPAPI buiten het project. De gekozen ontworpen stem is via de echte beveiligde
backendroute getest en door de eigenaar beluisterd/bevestigd: 73 tekens, 3,854 s
audio, 4,247 s tot volledige ontvangst, fallback uit. 33 gerichte/63 bredere
serverregressies, 128 clienttests en native builds geslaagd. De volledige
ElevenLabs-reeks telde 559 geslaagde tests. Premiumstem via de bestaande
geauthenticeerde app-API ingesteld; nieuwe Windows-build verbonden en de
bureaubladsnelkoppeling bijgewerkt. Zie ELEVENLABS_VOICE.md en
ELEVENLABS_TEST_REPORT.md. Telefoon is op 27 november niet via adb verbonden.

SSH-inspectie zonder hostwijzigingen: 2 OCPU, 12 GB RAM volgens IMDSv2, ARM64
Ubuntu 24.04.5, Python 3.12.3, circa 49 GB vrij, geen swap/Ollama/reverse proxy.
SSH-sleutel niet gekopieerd of rechten aangepast. Cloudconfiguratie, backups en
cutover worden afzonderlijk voorbereid. Geen productie, betaalde dienst, extra
cloudresource of telefonie geactiveerd.

Op 27 november read-only hercontrole: zelfde machine, circa 48 GB vrij.
Opt-in oracle-production toegevoegd: één lokale HTTPS-proxy met exacte Host/
doorgestuurd client-IP; authenticatie, CSRF, apparaatrechten en interne loopback-
grens behouden. Beschermde Fernet-vault op Linux; Windows-DPAPI blijft standaard.
Nieuwe OAuth-cloudkoppeling vereist expliciete Web-client/callbackconfiguratie.
CPU/modelpad kan voor de bestaande inferencehelper worden ingesteld. Server en
spraakhelper hebben volledig resolveerbare ARM64-wheels (geen modellen geladen).
13 gerichte tests voor beveiliging, vault, CPU, WAL-backup, herstel en DPAPI-export
geslaagd. Windows-bestandsvergrendeling in het nieuwe backupprogramma is met
expliciet sluiten van SQLite-verbindingen opgelost en opnieuw getest.
ARM64 CI-matrix, systemd/Caddy-templates, afgeschermde configuratie en concreet
backup/cutover/rollbackplan staan in deploy/oracle. Geen automatische productie-
updates geactiveerd. Volledige regressie: 572 passed in 257,13 s; aanvullende
deploymentscripts: 3 passed/1 POSIX-skip op Windows. Zie
docs/ORACLE_PREPARATION_TEST_REPORT.md. Laatste volledige reeks: 577 passed /
1 POSIX-skip in 252,44 s. Functioneel checkpoint afd9586 heeft groene PR-CI
voor Windows/Linux/ARM64-server, Windows-client, Android en repositorystructuur.
Draft PR 31 blijft gestapeld op planning-PR 30; geen merge of cloudinstallatie.

### Natuurlijke activiteitenplanning — 25 november 2026

Actieve branch `feature/natural-activity-planning`, gestapeld op
`fix/calendar-and-outing-experience` (65ab65c / PR 29). Origin is opgehaald;
develop bevat deze fase-7.5-basis nog niet. De branchhelper vereist een schone
werkmap; de twee bestaande eigenaarmaildiffs zijn onderzocht en intact gehouden,
zonder stash/reset, tweede projectroot of opname in deze wijziging.

De nieuwe planninglaag houdt een bron-gelabeld concept bij vóór uitvoerende
toolvalidatie. Meerdere gegevens per beurt, wijzigingen, alternatieven, eigen
geautoriseerde agenda, bekende kosten/reistijd, extra activiteiten en eten
gebruiken bestaande context, instellingen en providerrouter. Windows en Android
delen het overzicht via de bestaande beveiligde chat/API op 8765. Calendar/Gmail
blijven gesloten bruggen met huidige rechten, exacte preview en eigenaarapproval.
Geen live reis-/zoek-/weer-/boekingsadapter of automatische deelnemersbevestiging
gesimuleerd. Openstaande gegevens en menselijke acceptatie staan in
`docs/PLANNING_TEST_REPORT.md`; architectuur en instellingen in de drie andere
nieuwe planningsdocumenten. Mastervisie en changelog bijgewerkt.

Volledige technische ronde na herstel: 544 servertests geslaagd in 256,14 s,
126 clienttests, native Windows-build/rooktest en Android-tests/lint/builds.
Na de laatste kleine spraakweergavewijziging 88 gerichte regressies geslaagd.
Qwen2.5:3B heeft tien echte synthetische
gesprekken van drie beurten uitgevoerd; JSON-validiteit is geen luisteracceptatie.
De oorspronkelijke snelle meting had geen werkende CPU-begrenzing. De aparte
vier-thread CPU-reeks leverde 12 geldige beurten (mediaan 24,942 s); latere
verlopen-sessie-antwoorden zijn uitgesloten en de benchmark vernieuwt nu tokens
via de bestaande refreshroute. Gemini weigert met HTTP 402/RESOURCE_EXHAUSTED.
Geen betaalde activatie, modelwisseling, echte accounttest of externe wijziging.
Eigenaardiffs blijven 695234ae1147/1f3b5515efc9. Fase 7.5 / desktop-development;
geen fase 8, permanente dienst, productie of mini-pc-deployment.

De herstelde kostenvervolgroute is met drie echte CPU-beurten herhaald en de
uiteindelijke beknopte weergave nogmaals met drie echte modelbeurten gecontroleerd.
Windows-build staat in `.local/client-build-activity-planning`; Android-APK in
`.local/android-build`. De telefoon is bij oplevercontrole niet via adb verbonden;
een nieuwe telefooninstallatie en luisteracceptatie zijn dus niet geclaimd.
Push naar de eigen fork is geverifieerd; PR/remote CI worden bij oplevering
apart vermeld. Niet naar develop/main gemerged zolang de gestapelde basis-PR's
open zijn en de volledige ervaringsacceptatie nog ontbreekt.

Concept-PR: https://github.com/DeBeer05/jarvis/pull/30. Laatste aanvullingen
herkennen een afgewezen restaurant en korte annulering; modelvoorstellen mogen
een uitgesloten restaurant niet terugplaatsen. Gerichte tegenproef en Ruff/mypy
geslaagd. De ontwikkelbackend is gecontroleerd herstart (health/ready 200,
persoonlijke planning zonder login 401). De snelkoppeling verwijst naar de nieuwe
geteste build; de bestaande actieve client is niet geforceerd afgesloten.
Voor de nieuwe overzichtsknop moet de eigenaar JARVIS via het systeemvak afsluiten
en opnieuw openen. Remote resultaten worden op de actuele PR-commit gecontroleerd.

### Aanvullende schermafbeeldingen: activiteitenvraag en standaardagenda

De twee nieuwe screenshots maakten nog twee te smalle herkenningsregels zichtbaar.
De activiteitvraag wordt nu ook herkend aan ‘leuk ... (te) doen’ als STT het woord
uitjes verkeerd transcribeert. Dit verandert alleen de scherm-/spraakpresentatie;
de oorspronkelijke tekst blijft intact en er worden geen actierechten verleend.
Een eenvoudige uitjesopdracht met de afsluiting ‘in mijn agenda zet’ mag de
ingestelde standaardagenda gebruiken. Genoemde agenda's blijven uitgesloten van
de snelle route en worden niet stilzwijgend vervangen door primary.

79 gerichte regressies voor agenda, dagdelen en presentatie geslaagd. Volledige
serverreeks vóór de laatste contextguard: 509 geslaagd (204,00 s); vervolgens
57 gerichte tests voor de definitieve routes en onderwerpwisselingen geslaagd.
Een nieuwe activiteitenvraag wordt niet aan een oude taakvraag vastgeplakt;
een nieuwe expliciete uitjesopdracht gebruikt haar eigen slots. Ruff/mypy,
pip-, repository- en diffchecks geslaagd; remote CI wordt apart bevestigd.
Bestaande eigenaarmaildiffs onveranderd (695234ae1147/1f3b5515efc9).
De actieve Windows-app is inmiddels de geteste outings-overview-build; geen
nieuwe clientwijziging of computerbediening nodig. Geen echte agenda-accounttest,
geen externe mutatie; alleen een gecontroleerd voorstel na de gebruikersopdracht.
Fase 7.5 / desktop-development blijft de grens; geen migratie of modelwisseling.
De bestaande bureaubladsnelkoppeling verwijst nu ook naar de geteste build;
de oorspronkelijke snelkoppeling is als lokale genegeerde backup bewaard.

### Agenda blijft doorvragen

Opdracht 25 november: herhaling van dagdeelvragen en onnodige plannerwachttijd
herstellen. Op `fix/calendar-and-outing-experience`, gestapeld op de nog open
latencybranch omdat develop deze fase-7.5-basis nog niet bevat. Origin opgehaald;
de branchhelper vereist een schone werkmap. De twee bestaande mailwijzigingen
zijn onderzocht en intact gehouden, zonder stash/reset of tweede projectroot.
Bekende STT-dagdelen en gebonden vervolgaanvullingen worden nu vóór de tijdcontrole
verwerkt. Eenvoudige uitjes gaan direct naar gevalideerde CalendarCreate-preview;
de bestaande rechten en exacte eenmalige eigenaarapproval blijven vereist.

### Uitjes kort zeggen, overzicht tonen

Uitjesvragen gebruiken één bestaande generatie: vroege gesproken aankondiging,
volledige genummerde lijst in de app/geschiedenis. Geen hele lijst automatisch
voorlezen, geen Word-/Kladblokproces, extra modelcall, modeldownload of extra
clientruntime. Windows en Android hergebruiken hun bestaande speechprotocol.
Laatste schermcontrole vond dat de Windows-spraakpagina alleen uitgesproken
tekst liet zien. Die toont nu ook alle geschreven delta's en het definitieve
antwoord; 124 clienttests slagen. Nieuwe Windows-build wordt lokaal uitgerold;
Android heeft deze scheiding al en behoeft geen nieuwe APK.
Zie `docs/CALENDAR_OUTING_EXPERIENCE.md`. Volledige lokale serverreeks vóór laatste
hardening: 493 geslaagd; daarna 50 gerichte ervarings-/taaktests en 34 definitieve
nieuwe regressies geslaagd. Ruff/mypy, pip check, repository-/diffcheck en Android-
settingscontract geslaagd. Definitieve collectie: 503 inclusief tien bestaande
eigenaarmailtests, die buiten de eigen commit blijven. CI/publicatie apart.
Echte luister-/gespreksacceptatie staat nog open. Eén Qwen-proef had een timeout;
CPU-only gaf eerste tekst na 13,64 s en totaal 30,10 s voor begrensde 240 tokens,
met taal-/prijsfouten. Prompt aangescherpt; geen kwaliteits- of hoorbare
latencyacceptatie geclaimd. Geen echte accounttest of externe
mutatie. Scope blijft fase 7.5 / desktop-development, geen fase 8 of migratie.

### Windows-audio

Eigenaar bevestigde hoorbare JARVIS-spraak via de HyperX nadat Windows die headset
als standaarduitgang kreeg en de Windows-client die standaard na herstart volgt.
Alleen lokale audio-instellingen gewijzigd; diagnose blijft in genegeerde .local.

Telefoonupdate op expliciet verzoek uitgevoerd: bestaande Android-app via
`adb install -r` bijgewerkt met de geteste latency-APK 0.7.5/708. Installatie
Success, geïnstalleerde base.apk SHA-256 exact gelijk aan het lokale artifact
(984DDB3E2072…), oorspronkelijke installatiedatum behouden, MainActivity-start
Status=ok en app als hervat bevestigd. Geen clear/uninstall, reset of grants.
USB reverse 8765→8765 ingesteld; backend lokaal health/ready=200. Tijdens de
laatste verbindingscontrole verdween het USB-apparaat; geauthenticeerde
appverbinding en fysieke audioacceptatie zijn daarom niet als geslaagd geteld.
Voor deze lokale ontwikkelverbinding USB aangesloten houden. Geen fase 8,
netwerkpublicatie of mini-pc-migratie. Bestaande gebruikersmailwijzigingen intact.

Reactiesnelheid verbeteren met toekomstige **8 GB RAM als randvoorwaarde**, op
`fix/voice-latency-8gb`, afhankelijk van de bestaande PR27-code (5b015b5).
Origin/develop opnieuw opgehaald en actueel. Twee bestaande mailwijzigingen
inhoudelijk gecontroleerd en intact gelaten; geen stash/reset/tweede projectroot.
Scope blijft fase 7.5 / desktop-development; geen mini-pc-deployment.

Verbeterd: eerste lange spreekclausule eerder beschikbaar; beide clients
herbufferen gereed servermateriaal niet tot een hele zin. Maximaal één WAV
voorbereiden naast playback, uit bij barge-in; Stop wist oude generatie/audio.
CUDA-negatieve probe/inferencefallback wordt per helper onthouden; oude
STT-gewichten vrij vóór nieuwe allocatie. Licht profiel behoudt devicecache.
Geen nieuw model, grotere cache, GPU-installatie of automatische stemwisseling.
CPU-fallback komt hier door ontbrekende cuBLAS; GPU is geen toekomstige vereiste.
Greedy-decodering en timestampwijziging leverden maar tientallen ms op; greedy
herkende een annuleringszin slechter. Beide productie-defaults zijn behouden.

Bewijs: server **469 geslaagd** (200,40 s; inclusief tien ongestagede
gebruikersmailtests), Windows **123 geslaagd**, Android unit/lint/debug/release
geslaagd, portable smoke acht pagina's zonder mic/netwerk/helper, verpakte
voice-helper-smoke geslaagd. Ruff/mypy, drie pip checks, contract/repo/diffchecks
geslaagd. CPU-only Ollama bevestigd met 8192 contexttokens en nul VRAM; actieve
getelde set Ollama/helper/testbackend circa **3,30 GiB**, exclusief Windows/client.
Dit is geen opgelegde 8-GB-limiet en geen bewijs van mini-pc-snelheid. Warme live-
PCM-reacties nieuwe route 5,46/6,05 s; baseline 7,00/9,18 s maar verschillende
antwoordteksten, dus geen gecontroleerd winstpercentage. Koude opwarmbeurt 20,46 s.
Zie `docs/VOICE_LATENCY_8GB.md` voor bronnen, meetgrenzen en resterende acceptatie.

Geen Android-device aangesloten; APK wel gebouwd, geen telefooninstallatie of
fysieke microfoon-/luisteracceptatie geclaimd. Windows-focusprobleem blijft open.
Lokale uitrol, push/PR en echte CI worden afzonderlijk bevestigd. Geen merge van
open afhankelijkheden, geen fase 8 of migratie.
Aanvullende racecontrole: barge-in tijdens een prefetchbeurt inschakelen opent
geen concurrerende STT; de keuze geldt vanaf de volgende beurt. Beide clients
gebruiken daarvoor dezelfde beurtgebonden keuze; extra Windows-regressie slaagt.

Master Vision / Experience Overhaul op `feature/jarvis-experience-overhaul`.
Volledige visie (32 hoofdstukken), architectuurreview/gap analysis, UX-eisen,
scenario's A–H en geprioriteerd plan vastgelegd; AGENTS verwijst er blijvend naar.
Eerste incrementele correcties: gesprekroute bij domeinverhalen, gebonden oude
leesvragen, context-/stijlbehoud en streaming bij planner-chat, één routeselectie,
persoonlijkheidswaarden ook in tekst, beginonderwerpen in bronnotities behouden.
Verouderde 'alleen tekst/geen tools'-basisinstructie vervangen door servergrenzen.
Echte Ollama-proef vond 4096 runtimecontext tegenover 6000 aangeboden inputtokens.
Headless gebruikt nu opt-in native Chat in het bestaande gedeelde transport met
expliciete input/output-contextreserve; desktop-/clouddefaults blijven compatibel.
Qwen2.5:3B behouden en repositorydefault gelijkgetrokken; geen lokale .env gewijzigd.
Geen nieuw model, framework, SQL-migratie, nieuwe rechten, accounttest of fase 8.

Validatie: volledige serverregressie **465 geslaagd** (184,00 s), inclusief tien
reeds aanwezige ongestagede gebruikersmailtests; eigen commit sluit die bestanden
uit. Windows **114 geslaagd**. Gerichte providers/ervaring/mail **67 geslaagd**;
Ruff/mypy, settingscontract, pip-, repository-/diffchecks geslaagd. Echte lokale
20/50-beurtproeven, 42 TTS-zinnen, drie STT-WAV's en synthetische STT→AI→eerste
antwoordzin-PCM uitgevoerd zonder microfoon, playback of gebruikersdatabase.
Na contextallocatiecorrectie: 50-beurt-beginverwijzing goed en nul exacte
antwoordduplicaten (eerste 4096-proef: verwijzing fout en 27 duplicaten).
Nederlands, roltoeschrijving en onnodige vragen blijven onvoldoende voor volledige
acceptatie. Zie `docs/EXPERIENCE_TEST_REPORT.md` voor alle cijfers en beperkingen.
De echte Windows-focus-/microfoonacceptatie blijft open. Ook algemene vrije
gesprek-naar-taakverwijzingen en melding-naar-gesprek zijn nog niet volledig af.

Git: origin/develop gecontroleerd actueel. Fase-7.5-afhankelijkheid staat nog in
PR25/26; deze branch behoudt PR26-head 3643cb0. Standaardbranchhelper kon niet op
de twee bestaande gebruikerswijzigingen worden toegepast; geen stash/reset of
tweede projectroot gebruikt. Publicatie/CI worden afzonderlijk bevestigd; geen
merge van de afhankelijkheden of main. Stop blijft na fase 7.5.

Aanvullende stijlvoorkeur: afzender meteen noemen, in gespreksvorm. De bestaande
gevalideerde mailgroepen worden nu geformuleerd als ‘Van [afzender] heeft u ...
en van [afzender] ... , meneer.’ Geen nieuwe AI-aanroep, rechten of clientbuild.
Scope blijft fase 7.5; het afzonderlijke Windows-focusprobleem blijft open.
Validatie: **430 servertests geslaagd** (163,14 s), daarnaast alle 13 mailtests,
Ruff/mypy, repository-/diffcheck en server-pip-check geslaagd. Backend herstart;
geen echte mailbox gelezen, geen clientupdate nodig.

Gebruiker vraagt zeer korte mailoverzichten zoals twee PayPal-betaalbewijzen samen
en één Google Cloud-voorwaardenwijziging. Samenvattingsinstructie aangepast naar één
zin met aantallen per afzender én doel, zonder kop/opsomming; u/meneer volgens verzoek.
Geen verzonnen doel bij ontbrekende informatie. Kritieke deadlines blijven behouden.
Hergebruikt dezelfde backend-/AI-route; geen clientbuild, migratie of fase 8.
Een prompt alleen bleek bij het lokale model onvoldoende: de synthetische proef
gaf soms een verkeerde telling. Het model levert nu alleen gevalideerde groepen
met bronindices en korte doelzinnen. De backend controleert volledige dekking,
geen duplicaten en gelijke afzenders per groep en maakt zelf de zin/aantallen.
Letterlijke bronnotities behouden noodzakelijke deadlines; extra modelmetadata
wordt niet gebruikt als opdracht of telling. Echte lokale synthetische proef gaf
in 1,44 s correct twee PayPal-betaalbewijzen en één Google Cloud-voorwaardenmail.
Geen echte mailbox gelezen. Windows-focusprobleem blijft afzonderlijk open.
Volledige serverregressie: **430 geslaagd**, 188,36 s; laatste kleine formatter-
correcties daarnaast met alle **13 mailtests geslaagd** gecontroleerd. Ruff/mypy,
repository-/diffcheck en server-pip-check geslaagd. Alleen backendherstart nodig.

Vervolgmelding: AI-mailsamenvatting valt terug. Twee codepaden hersteld: gevoelige
inhoud sloeg de AI over, en ASCII-escaping kon het bronpakket onnodig vergroten.
Nu uitsluitend lokale Ollama voor gevoelige inhoud, geen cloudretry, compacte
Unicode en een concrete terugvalreden. Werkelijke aanleiding van de specifieke
gebruikersmail is niet vastgesteld door diens privéberichten te lezen.
Synthetische proef op het echte lokale Ollama-model: eerste koude aanvraag liep
tegen de bestaande providerdeadline; warme herhaling leverde binnen 3,49 s een
samenvatting met behoud van de deadline. Geen privémail of cloudaanroep gebruikt.
Koude-startlatency blijft dus een beperking; de terugvalmelding noemt de reden.
Volledige serverregressie op deze wijziging: **429 geslaagd**, 180,77 s.
Ruff/mypy, repository-/diffcheck en server-pip-check geslaagd. Geen clientwijziging
of nieuwe APK nodig voor deze backendcorrectie; Windows-focusonderzoek blijft open.
Gebruiker meldt dat Windows na vensterwissel nog blijft luisteren zonder reactie;
eerdere heartbeatfix loste dit niet volledig op. Microfoon-/focusacceptatie blijft open.

Aanvullende herstelopdracht: gebruiker bedoelt met wegklikken een ander venster/
programma openen. Geen focusgebonden stop gevonden; wel een reproduceerbare race
waarbij een oude heartbeatfout na een epochwissel de nieuwe spraakbeurt stopte.
Callbacks zijn nu aan hun sessie/epoch gebonden; 401/403 blijven stoppen. Een late
vervolgtimer mag na Stop geen microfoon openen. Synthetische deactivatieproef en
raceproef toegevoegd; echte achtergrondmicrofoonproef blijft nodig.
Recente mailvragen lezen nu zelf maximaal twintig geverifieerde berichtinhouden en
vragen één gezamenlijke samenvatting via de bestaande AI-router. Geen ID-vraag,
extra goedkeuring, nieuwe rechten of echte accounttest. Zoekfilters blijven behouden.
Geen SQL-migratie, fase 8, productie of mini-pc-migratie.
Herstelvalidatie: volledige serverregressie 426 geslaagd (178,13 s), daarna alle
tien mailgerichte tests inclusief extra privacyproef geslaagd; Windows 114 geslaagd.
Ruff/mypy, repositorycheck, diffcheck en server-/client-pip-check geslaagd.
Windows-build mail-resume zichtbaar geopend en verbonden, snelkoppeling bijgewerkt;
portable smoke-test opent acht pagina's zonder netwerk/microfoon/helper. Tweede
echte start eindigt met code 0 en behoudt hetzelfde proces. Schema 7/quick_check ok,
acht herinneringen behouden; favoriete stem M3 bevestigd vóór de appwissel.
Werkelijke focus-/microfoonproef blijft nodig; geen echte mails namens gebruiker gelezen.

Intelligent Response Engine & Dutch Butler Voice geïmplementeerd op
feature/intelligent-response-butler-voice, voortbouwend op b2948b1/PR25 omdat develop
fase 7.5 nog niet bevat. Nieuwe antwoordmodi/profielen, apart speech-SSE-protocol,
conservatieve brongebonden samenvattingen, contextgebonden mailvervolgvragen,
Classic Butler en gesloten tijdelijke/permanente gesproken instellingen.
Centrale lokale Supertonic/Piper-router, vaste provider per antwoord, begrensde
sessie-/geheugenversiegebonden audiocache, native Voice Studio op beide clients.
Geen SQL-migratie (schema 7), tweede backend, nieuwe rechten, online TTS of cloning.
Eigenaar gaf toestemming voor circa 400 MB Supertonic 3 M1–M5. ONNX-checksums
geverifieerd; modelbestanden blijven buiten Git. Licenties en primaire bronnen in
TTS_PROVIDERS.md; vendored helper met MIT-copyright en licentie.

Definitieve serverregressie **417 geslaagd**, 221,34 s; Windows **112 geslaagd**,
7,03 s; Android unit/lint/debug/release en **18 instrumentatietests geslaagd**
(ook herhaling met nieuw contract). Ruff/mypy en drie pip checks geslaagd.
Echte 42-zinsbenchmark: mediaan warm Supertonic 1,467 s / Piper 0,213 s;
Supertonic-helperpiek 518,6 MiB. Echte generatieannulering circa 0,051 s en
verse inference daarna geslaagd. Verpakte Supertonic produceert geldig WAV.
Geen fysieke microfoon-/luisterkwaliteit, mini-pc of GPU-TTS als geslaagd geclaimd.
Rapport: docs/RESPONSE_AND_VOICE_TEST_REPORT.md. Subjectieve luisteracceptatie vereist.

Windows-opstartmelding onderzocht: eigen verborgen gestart proces draaide zonder
zichtbaar venster. Zichtbaar herstart en venster daadwerkelijk teruggevonden.
Nieuwe build bevat same-user/profile IPC-activatie voor dubbelstart, getest met
apart proces. Windows 0.7.5 uit .local/client-build-butler zichtbaar gestart;
bestaande snelkoppeling bijgewerkt, aangemeld/verbonden en Voice Studio-catalogus
daadwerkelijk opgehaald. Tweede echte start activeert hetzelfde proces en eindigt
met code 0. Echte telefoon 0.7.5/708, install -r en USB reverse 8765→8765 bevestigd,
geen datareset/grants. Draft PR26 naar develop, afhankelijk van PR25; actuele CI
via PR, geen merge. Menselijke luisterproef gevraagd; nog geen geslaagd resultaat.
Backend blijft localhost 8765, desktop-development. Geen fase 8, migratie of productie.


Adresboekuitbreiding lokaal uitgerold op bestaande server/Windows en Android
0.7.5/707: persoonlijke contactnamen en aliassen, exact e-mailadres, revisiecontrole,
geen adreswijziging van bestaande voorstellen, lokale verduidelijking bij dubbelzinnigheid.
Serverregressie **403 geslaagd**, 181,35 s; Windows **108 geslaagd**; Android
**17 instrumentatietests geslaagd**, unit/lint/debug/release-build geslaagd.
Schema 6→7 met pre-v7-back-up, quick_check=ok, eigenaarrecord en herinneringen
behouden. Acht expliciet gevraagde herinneringen lokaal opgeslagen; geen inhoud
of persoonsgegevens in Git. Laatste twee ook na herstart aanwezig. Computerbediening
werd bij eindcontrole door Escape gestopt; geen volledige echte luisterproef geclaimd.

Nieuwe gebruikersopdracht: Intelligent Response Engine en Nederlandse butlerstem.
Inspectie/onderzoek gestart; hergebruik bestaande Context/Settings/AI/SpeechBridge.
Geen telefonie, migratie of publieke deployment. Fase 7.5-acceptatie blijft open.


Acceptatieblokkers gemeld door eigenaar hersteld en lokaal uitgerold (Android
**0.7.5/706**): natuurlijke aanmaakvormen ‘een afspraak maken’ en vrije titel-/
persoonsantwoorden blijven aan de bestaande taak gekoppeld. Oude verkeerd als
leesvraag opgeslagen opdrachten worden herkend. ‘Wat kan je allemaal doen?’
gebruikt serverfuncties/rechten en geen generieke modelontkenning.
Een dubbele disconnect kon finalisatie onderbreken en de actieve chat permanent
bezet houden. Dat is met een falende vooraf-/geslaagde achteraftest gereproduceerd;
volledige opruiming loopt nu in een afgeschermde, getrackte taak. Overname wacht
begrensd op de vorige generatie, buiten het statemachineslot. Android negeert
verouderde foutcallbacks en kan een reeds afgesloten spraaksessie veilig loslaten.
Volledige regressie **381 geslaagd**, 172,76 s; Android **16 instrumentatietests
geslaagd** op dezelfde herstelde backend, plus unit/lint/debug/release-build.
Eigenaar meldde algemene gesprekken als goed, maar agenda en Android-herstel
als onvoldoende vóór reparatie. Nieuwe echte acceptatie is aangevraagd, nog
niet als geslaagd geteld. Fase 7.5 blijft open; geen fase-8-vrijgave.

Lokale gebruikersserver gecontroleerd herstart op **0.7.5/8765**. Schema **5→6**
met automatische pre-v6-back-up; eigenaarrecord exact behouden, herinneringenaantal
behouden, quick_check=ok. Health/ready=200 en persoonlijke instellingen zonder
login=401. Windows portable gestart; snelkoppeling ‘JARVIS 0.7.5’ op bureaublad.
Echte telefoon: 0.7.5/705 via install -r geïnstalleerd en geopend; alleen USB
reverse 8765→8765, geen rechten toegekend of gegevensreset. De gebruiker heeft
aangegeven de Windows-proef te gaan doen; dat is nog geen geslaagd resultaat.
Hardwareacceptatie en resterende functionele punten blijven expliciet open.

Afrondingsbuild **0.7.5** gemaakt voor server, Windows en Android (versionCode705).
Toegevoegd: blijvende opt-in mailopvolging, brongebonden antwoordstatus in chat,
openstaande-takenopdracht, persoonlijkheidsvoorbeeld zonder opslag/toolrechten,
apparaatgebonden geheugen bij synchronisatie uit, schema-6-migratie met back-up,
en geen resourceprobes bij diagnostiek uit. Externe schrijfacties behouden hun
exacte goedkeuring; opvolging kan alleen lezen en controleert actuele rechten.
Laatste volledige serverregressie **373 geslaagd**, 144,88 s; Windows **107
geslaagd**, 4,90 s; Android **14 instrumentatietests geslaagd**, unit/lint/debug/
release-build geslaagd (154 s). Windows portable- en speechhelper-smoke geslaagd:
geen netwerk/model/microfoon bij start; geen downloads. APK-handtekening komt
overeen met de bestaande lokale 0.7.0-debug-APK. Beide artifacts staan in .local.
Fase 7.5 is nog geen volledige acceptatie van alle 50 specificatieonderdelen:
overige runtime-instellingen, automatisch vervolgen van afhankelijke intenties,
uitgebreide mailconceptcorrecties en echte hardwareacceptatie blijven open.
Geen fase 8, publieke toegang, echte accountmutaties of mini-pc-migratie.

Handmatige spraakactivatie reserveert op Windows en Android de centrale
gesprekslease vóór microfoonopname. Bij conflict wordt geen opname gestart;
annuleren negeert late activatiecallbacks. Dezelfde conversation_id blijft
behouden voor de daaropvolgende transcriptbeurt. Windows **106 geslaagd**, 4,69 s;
Android **14 instrumentatietests geslaagd**, unit/lint/debug-build geslaagd
(99 s), uitsluitend emulator-5556. Python-lint/typechecks geslaagd.
De laatste backendregressie blijft 365 geslaagd; deze stap wijzigt alleen clients.
Fase 7.5 blijft open voor overige instellingen, vervolgtaaklogica, definitieve
builds/installatie en menselijke spraak-/echoproeven. Geen fase 8 gestart.

Brongebonden samenvattinginvalidatie hersteld: vergeten/corrigeren behoudt
onverwante notities en volgt bronbeurten en werkelijk gebruikt geheugen.
Agenda-alternatieven en hun buffertijd blijven binnen het opgehaalde bereik.
Android-instellingencontract bijgewerkt, generator en CI-driftcontrole toegevoegd.
Volledige serverregressie **365 geslaagd**, 157,06 s; Windows **105 geslaagd**,
4,41 s; Android **14 instrumentatietests geslaagd**, unit/lint/debug-build geslaagd
(84 s), uitsluitend emulator-5556. Lint/typechecks, pip/repository/diffcontrole
geslaagd. Geen gebruikersservermigratie, echte accounttest of telefooninstallatie.
Fase 7.5 blijft in uitvoering; overige instellingen, vervolgtaaklogica,
definitieve builds/installatie en echte audioacceptatie blijven open.

Optionele lichte trefwoordverwantschap aangesloten op geheugenretrieval. Kleine
Nederlandse woordenlijst, maximaal 24 zoektermen; geen embeddings/modeldownloads
of algemene semantische claims. Menu hernoemd naar ‘Verwante trefwoorden (licht)’.
Gebruikers-, status-, verval- en gevoeligheidsfilters blijven ongewijzigd.
Volledige serverregressie **363 geslaagd**, 174,39 s; Windows **105 geslaagd**,
6,38 s. Lint/typechecks, pip/repositorycontrole geslaagd. Algemene semantische
retrieval en overige resterende fase-7.5-onderdelen blijven expliciet open.

Streaminginstellingen aangesloten: AI-streaming uit buffert begrensd tot een
succesvolle generatie; mislukte deeltekst wordt niet zichtbaar en fallback blijft
vóór zichtbare tekst. Interne providerstream blijft annuleerbaar. Spraakstreaming
is apart op Windows/Android instelbaar: uit wacht op succesvolle voltooiing en
spreekt geen geannuleerd/mislukt deelantwoord. Keuze is per beurt vastgezet.
Volledige serverregressie **361 geslaagd**, 206,12 s; Windows **105 geslaagd**;
Android unit/lint/debug-build geslaagd. Lint/typechecks, pip/repositorycontrole
geslaagd. Geen echte telefooninstallatie/accounttest. Fase 7.5 blijft open voor
overige instellingen, definitieve builds/installatie en hardwareacceptatie.

Meldingsvoorkeuren aangesloten op nieuwe automatiseringsmeldingen: aan/uit,
rustige uren/tijdzone en uitschakelen/begrenzen van proactieve suggesties.
Expliciete herinneringen blijven apart van proactiviteit; bestaande inboxberichten
worden niet verwijderd. Jobgebonden meldingen vinden voorkeuren via het bestaande
apparaat/gebruikersverband. Geen nieuwe pushdienst, accounttest of oproep.
Volledige regressie **359 geslaagd**, 172,98 s; gerichte meldings-/automationtests
25 geslaagd. Lint/typechecks, pip check en repositorycontrole geslaagd.
Fase 7.5 blijft in uitvoering; overige instellingen, definitieve builds/installatie
en echte microfoon-/echoacceptatie blijven open.

Agenda-instellingen aangesloten op bestaande reschedule-analyse: gebruikersgebonden
buffertijd, werkdagen/werktijden, alternatieven en naburige afspraken. De uitvoerder
leest dezelfde voorkeuren; echte overlapcontrole en exacte approvals blijven intact.
UTC-rekentijd voorkomt verkeerde duur/gapberekening bij zomer-/wintertijd.
Gerichte API-regressie plus volledige serverregressie: **357 geslaagd**, 170,08 s.
Lint/typechecks, dependency- en repositorycontrole geslaagd. README/forkroadmap
verwijzen nu naar fase 7.5 en houden deze expliciet in uitvoering. Definitieve
builds/installatie, overige instellingen en menselijke audioacceptatie blijven open.

AI-prestatieprofielen daadwerkelijk aangesloten op contextbudget, antwoordlimiet
en request-time-out. Eigen tegelijk gewijzigde waarden blijven behouden; geen
modeldownloads/-vervanging of beveiligingswijziging. Gerichte policytest plus
volledige serverregressie: **356 geslaagd**, 189,65 s. Lint/typechecks en pip check
geslaagd. Instellingenhandleiding bevat nu de exacte presets. Overige instellingen,
definitieve builds/installatie en hardwareacceptatie blijven open voor fase 7.5.

Android adaptieve opname aangesloten op speculatieve STT: normale stilte start
herkenning terwijl opname doorgaat; nieuwe spraak maakt het fragment ongeldig.
Een geldige transcriptie wordt hergebruikt; voorlopige tekst voert niets uit.
Pure Kotlin-beurttest toegevoegd. Unit/lint/debug-build geslaagd. Emulatorregressie
geslaagd: 14 instrumented tests zonder fouten. Dit test de bestaande gespreksflow,
niet menselijke pauzes of akoestiek. Eerste apparaatrun stopgezet omdat een inmiddels aangesloten echte
telefoon ook werd geselecteerd; herhaling expliciet met ANDROID_SERIAL=emulator-5556.
Geen geslaagde hardwareacceptatie geclaimd. Fase 7.5 blijft in uitvoering.

Windows adaptieve beurtanalyse uitgebreid: tijdens de normale stilte begint
speculatieve STT terwijl de microfoon blijft opnemen. Een complete uitspraak
kan eerder afronden; onafgemaakte tekst wacht tot de maximale denkpauze. Nieuwe
spraak maakt de oude transcriptiesnapshot ongeldig. Voorlopige tekst verschijnt
alleen als transcript, niet als opdracht. Geldige herkenning wordt hergebruikt
zonder een tweede modelkopie. Vier deterministische tests toegevoegd; Windows
**103 tests geslaagd**, 5,37 s. Lint/typechecks schoon. Android-adaptatie en echte
spraak-/pauzeacceptatie blijven open; fase 7.5 nog niet voltooid.

### Fase 7.5 — inspectie en implementatie gestart — 24 november 2026

Volledige specificatie (50 onderdelen) ontvangen. Structuur, architectuur,
server/chat/router, SQLite, upstream JSON-geheugen/taken, automatiseringen,
goedkeuringen, native clients en bestaande voicepipeline onderzocht.
Technisch plan: docs/NATURAL_CONVERSATION_IMPLEMENTATION_PLAN.md.
Featurebranch natural-conversation-engine vanaf actuele develop 436bb2b;
werkende PR-24-afhankelijkheid fast-forward meegenomen, zonder develop/main-
merge of protection-bypass. Bestaande werkboom was schoon. GitHub Actions-
blokkade blijft bij afronding te controleren. Port 8765, bestaande gegevens,
credentials en componenten behouden. Fase is nog niet voltooid.

Eerste fundament: schema-5-migratie met backup, centrale strikt gevalideerde
instellingen in 13 categorieën, revision/CAS/import/export/reset en gescheiden
apparaatinstellingen; settings/memory-API achter bestaande chatrechten, zonder
credential-/authinstellingen of uitschakelbare hoogrisicogoedkeuringen.
SQLite/FTS5 MemoryManager met bronmetadata, correcties, expiry, gevoelige expliciete
toestemming en bron-/samenvattinginvalidatie bij vergeten. NaturalConversationManager
met alle 14 staten, leases, epochbeveiliging, expliciete overdracht en timeouts.
Nieuwe API's en tien tests: volledige regressiesuite 265 geslaagd. Alleen tijdelijke
testdatabases gemigreerd; de echte server/database is nog niet omgezet naar fase 7.5.
Contextintegratie: bestaande ChatService/AIRouter gebruikt begrensde bronbewuste
ContextManager, aparte Nederlandse voiceprompt/persoonlijkheid, lokale extractieve
samenvattingen met wijzigbare versies en expliciete onthoud-/vergeetopdrachten.
Offline en provider/modelvoorkeuren zijn request-local, ook voor interne
toolplanner-/samenvattingsaanroepen; geen gedeelde providermutaties. Geheugen
gaat alleen met opt-in naar cloud; gevoelig geheugen uitsluitend naar een
lokale-only route. Vergeten invalideert samenvattingen en bron-/afgeleide beurten;
lopende gewone generaties stoppen bij een geheugenwijziging. Regels toegepast
op de bestaande chatroute, geen tweede router/database/pipeline.
Volledige regressiesuite na contextintegratie: **272 geslaagd**, 105,04 s.
Aanvullende tests: echte geauthenticeerde API met synthetische providers,
herstartpersistentie, cloud/offline, afgeleid vergeten, samenvattings-CAS,
budgetfouten en gelijktijdige request-local providerconfiguratie.
Nog te doen: uitgebreidere intent-/taakcontext, audio/streaming, beide client-GUI's,
overige geheugen-/samenvattingsflow, metingen, builds en acceptatietests.

Nederlandse TemporalResolver toegevoegd: relatieve dagen/weken, weekdagen,
half-/kwarttijden, relatieve minuten/uren, duur en tijdcorrecties op een bekende
anchor. Ambigue dagdelen en werk-eindtijden vragen verduidelijking. Zomer- en
wintertijdgaten/dubbele tijden worden afgewezen; relatieve duur rekent in UTC.
CalendarRead/ReminderCreate hergebruiken deze resolver; uitgebreide afspraak-
slotextractie volgt nog. TaskMemory bewaart begrensde gevalideerde referenties,
onafgeronde vragen en job-ID's in bestaande SQLite-tabellen. AutomationEngine
blijft de enige uitvoerder. Goedkeuringsnonces/previewtijd/decision-authority
worden nooit hersteld. Geen externe accountmutaties uitgevoerd.
Volledige regressiesuite na tijd-/taakcontext: **301 geslaagd**, 110,93 s.
Windows-instellingenmenu toegevoegd aan Instellingen → Gesprekken en geheugen:
13 categorieën uit de serverschema's, typed invoer, zoeken, opslaan/annuleren,
CAS-conflicten, reset/import/export, geheugen-CRUD/export/wissen en wijzigbare
samenvattingen. Privégegevens verdwijnen bij uitloggen. Volledige schemaweergave
visueel gecontroleerd met synthetische gegevens; 83 Windows-clienttests geslaagd.
Instellingen die de nieuwe voice-/intentlagen nodig hebben worden in de volgende
implementatiestappen aangesloten; het menu alleen bewijst die werking niet.
Blokkeerregels/read-propose worden nu gecontroleerd bij lezen, indienen en vóór
uitvoering; instellingen verlenen geen apparaatrechten of approval-bypass.
Offline geldt ook voor de bestaande losse automation-summary/planner-API.
Volledige serverregressiesuite: **303 geslaagd**, 108,32 s.
Nog geen nieuwe clientbuild/installatie; fase 7.5 blijft in uitvoering.

Audioproceshergebruik: gedeelde stdlib OwnedVoicePipe voor bestaande Windows-
en serverhelpers. Server start niet meer per aanvraag een nieuw inferenceproces;
geladen modellen blijven begrensd beschikbaar en worden na inactiviteit vrijgegeven.
Annulering, protocolfouten, overlapweigering en frisse verwerking na stoppen zijn
met een echt synthetisch pipe-subprocess getest. Windows idle/outputstop behoudt
warme modellen; volledig afsluiten ruimt het eigen proces op.
Serverregressie **307 geslaagd**, 108,63 s; Windows **83 geslaagd**, 4,17 s.
Echte lokale synthetische audio op bestaande modellen: Piper koud/warm 1,004/0,098 s,
Whisper Small CPU 3,321/1,975 s; piek helper-RAM 877,6 MiB. Geen echte microfoon,
accountmutaties of downloads. Dit is nog geen totale gesprekslatency.
Zie docs/CONVERSATION_PERFORMANCE.md. Doorlopende modus/AEC/barge-in en Android
worden hierna aangesloten; geen fase-8- of mini-pc-werk gestart.

Windows-doorloop aangesloten op de centrale audiosessie: één conversation_id,
epoch op voice-chat, automatische backend-thinking/antwoord-/wachtstatus,
heartbeat zonder activiteit te vervalsen en expliciete overnameknop. Oude audio
van een ander apparaat wordt vóór het aanmaken van een nieuwe beurt afgewezen.
Doorloop vereist bewuste lokale PTT-/wakeactivatie plus de ingestelde vervolgmodus;
microfoon blijft bij opstart uit. Afsluitzinnen en inactiviteit stoppen de sessie.
Globale instellingen worden na authenticatie opgehaald en wijzigen geen lokale
toestemming/apparaatkeuze. Wakefrase kan worden aangepast (transcriptiegate).
Server **310 tests geslaagd**, 114,34 s; Windows **87 tests geslaagd**, 4,15 s.
Inclusief tien synthetische doorlopende beurten, daadwerkelijke serverlevenscyclus,
idle-heartbeat, oude overgenomen invoer en late native callbacks. Geen echte
microfoonacceptatie geclaimd. Native Android-koppeling is de volgende stap;
barge-in/DSP, uitgebreidere intentlaag, overige GUI/diagnostiek en documentatie
blijven open. Zie docs/CONVERSATION_STATE_MACHINE.md.

Android-instellingencentrum aangesloten: dezelfde servercategorieën/labels,
typed invoer/sliders, zoeken, dirty-state/CAS, annuleren/reset/import/export en
geheugen-CRUD/filter/gevoelige toestemming/verouderd/wissen/samenvattingen.
Privégegevens verdwijnen bij originwissel/uitloggen; echte audioapparaten blijven
in lokale DataStore. Niet-ondersteunde TTS-providers zijn niet beschikbaar;
ontbrekende Whisper-/Piperkeuzes zijn uitgegrijsd en server-side geweigerd.
Android unit/lint/debug/release-build geslaagd; uitsluitend afzonderlijke
nieuwe headless AVD met hostaudio uit gebruikt. Drie instrumented tests werkelijk
geslaagd (JUnit XML: 3, fouten 0): volledig instellingencontract/typen, echte Compose-
invoer/annuleren, en echte TCP met synthetische auth voor globale voorkeuren,
apparaatisolatie, geheugen wissen en expliciete sessieoverdracht/stale-audioafwijzing.
Tijdelijke fixture op 127.0.0.1:18765 via adb reverse in alleen deze test-AVD;
de echte server:8765, telefoon, accounts en gesprekken zijn niet vervangen.
Volledige serverregressie **311 geslaagd**, 135,16 s. Windows-regressie 87 geslaagd.
Resterend: Android-spraaklus/foregroundherstel, barge-in/echo/adaptieve detectie,
uitgebreidere intent-/slotlaag, overige instellingen/retentie/diagnostiek, definitieve
builds/meting/documentatie/CI en hardwareacceptatie. Geen fase-7.5-voltooiing geclaimd.

Gedeelde audio en Android-doorloop aangesloten. Windows Natural Conversation
Mode gebruikt nu geauthenticeerde server-STT/TTS met een annuleerbare HTTP-pool,
zodat beide clients dezelfde geladen modellen hergebruiken. De bestaande lokale
Windows-adapter blijft behouden. Enginewisseling gebeurt op een veilige beurtgrens.
Android heeft dezelfde centrale sessie/epoch, heartbeat, timeouts, afscheid,
expliciete overname en automatische vervolgbeurten na bewuste activatie. Verlaten
van de app/audiofocusverlies stopt opname; OS-microfoontoestemming blijft vereist.
Beschikbare platform-AEC en ruisonderdrukking worden gekoppeld, zonder claims
over echte echo-/microfoonkwaliteit. Een spraakinterruptie verwijdert geen
duurzaam extern concept of reeds uitgevoerde taak.

Echte TCP-test vond dat BaseHTTPMiddleware disconnect maskeerde. SecurityHeaders
is naar pure ASGI omgezet met behoud van headers/CSRF/auth. De regressie bewijst
serverannulering vóór responseheaders en een daarna succesvolle aanvraag.
Laatste volledige serverregressie: **312 geslaagd**, 114,16 s. Windows: **90
geslaagd**. Android unit/lint/debug/release plus **11 instrumented tests geslaagd**
in afzonderlijke headless AVD met hostaudio uit. Eén test doorloopt tien beurten
via echte Whisper/Piper-serverinference met synthetische WAV-input en testoutput;
geen menselijke luister-/spreek-/barge-inacceptatie geclaimd. Alleen testfixture
18765 en tijdelijke databases gebruikt; echte 8765-server nog niet gemigreerd.
GitHub draft-PR #25 naar develop bestaat. Actions-dispatch retourneert HTTP 422
“Actions has been disabled for this repository”; geen CI-succes of merge geclaimd.
Open blijven barge-in, adaptieve beurtanalyse, uitgebreide intent/slots,
resterende runtime-instellingen/privacy/diagnostiek, documentatie en hardwaretests.

Optionele spraakgestuurde onderbreking aangesloten in beide native clients:
VAD pauzeert uitvoer, STT bevestigt een nieuwe uitspraak, oude audio/generatie/
wachtrij worden gestopt en hetzelfde gesprek blijft behouden. Echo/lege tekst
hervat de uitvoer. Windows gebruikt een begrensde PCM-referentiefilter; Android
vereist beschikbare en geactiveerde platform-AEC. Tekstguards voorkomen gebruik
van herkenbare eigen output/approvalwoorden. Geen sprekeridentificatie of garantie
tegen akoestische echo geclaimd; standaard uit en hardwareacceptatie vereist.
Geserialiseerde audiostreams en gescheiden STT/TTS-annulering bewaken late callbacks.
Windows **97 tests geslaagd**; Android unit/lint/build en **12 instrumented tests,
0 fouten**, inclusief echte STT/TTS met gesimuleerde onderbrekingsaudio/AEC. Geen
gebruikersmicrofoon geopend. Zie docs/VOICE_STREAMING.md. Uitgebreidere Nederlandse
afspraakvalidatie en runtime-instellingen worden hierna verder aangesloten.

Afspraakvalidatie en samengestelde opdrachten uitgebreid: Nederlandse absolute/
relatieve datum, half-/kwarttijd, duur, herinnering vooraf en correcties worden
tegen eigen gebruikerswoorden gecontroleerd. Onbekende uitnodigingsadressen worden
niet verzonnen. Een correctie vervangt alleen een nog niet goedgekeurd voorstel;
eenmalige payload-/preview-/sessiebinding blijft intact, ook voor natuurlijke
bevestigingen. Nieuwe reminder_minutes gaat als gecontroleerde Google popup mee.
Geverifieerde afspraakgegevens ankeren verplaatsingen; duur/genodigden blijven behouden.
Gesloten intentplannen gebruiken letterlijke gebruikersdelen, eerdere afhankelijkheden
en een afzonderlijke idempotency-key per stap. Deelproblemen blokkeren onafhankelijke
stappen niet; algemeen ja kan niet meerdere voorstellen goedkeuren.

Diagnostiek in Windows/Android toegevoegd: geauthenticeerde numerieke telemetry,
AI-/STT-/TTS-/audio-latency, geschatte context, sessie-/geheugen-/integratiestatus,
proces-RAM/CPU en optionele begrensde NVIDIA-probe. Geen conversatie-inhoud/geheimen
in export. Instellingen-RPC gebruikt een onveranderlijke snapshot en bewaart invoer
bij fouten. Nieuwe Ruff/mypy-devtools met pins en reproduceerbare kwaliteitscheck;
CI voert serverlint/typechecks uit, zonder desktopstack of modellen te importeren.
Volledige serverregressie **346 geslaagd**, 194,89 s; Windows **99 geslaagd**;
Android unit/lint/debug/release en **13 instrumented tests, 0 fouten**. Alle tests
gebruiken synthetische accounts/gegevens; echte 8765-server nog niet gemigreerd.
GitHub Actions is inmiddels weer actief: server Windows/Linux, Windows-build,
Android-build en structuurchecks voor commit 242ffa4 geslaagd. Oudere melding
over Actionsblokkade is daarmee achterhaald; nieuwe commits krijgen nieuwe checks.
Nog in uitvoering: overige runtime-instellingen/bewaarbeleid, rijkere geheugen-
en taakflows, adaptieve beurtanalyse, definitieve builds/documentatie/hardwareacceptatie.

CI voor 3e8f0dc: Windows-server, Windows-build, Android en structuurchecks geslaagd.
Linux stopte bij mypy: ctypes.WinDLL bestaat niet in Linux-typestubs, hoewel de
uitvoering al door os.name wordt afgeschermd. Windows-only loader wordt nu pas
binnen die platformtak opgezocht. Zowel Linux- als Windows-typeprofiel lokaal
gecontroleerd; nieuwe remote run volgt. Geen applicatie- of beveiligingscheck omzeild.

Bewaarbeleid aangesloten: nieuwe beurten bij geschiedenis uit bevatten geen
gewone tekst in SQLite; actieve context blijft begrensd in RAM met eigen TTL en
verdwijnt bij herstart. Exacte approval en request-idempotentie blijven werken;
open taakparameters zijn afzonderlijk. Android wist de offline Room-cache en
cachet privébeurten niet opnieuw. Eén lichte onderhoudstaak ruimt begrensd oude
inhoud/verlopen herinneringen op; actieve gesprekken en open taakgegevens blijven
behouden. Automatisch onthouden is opt-in en gebruikt alleen een positieve
grammatica voor gewone plannings-/programmeertaalvoorkeuren; bij altijd-vragen
ontstaan niet opgehaalde voorstellen. Profielkeuze past echte presetwaarden toe.

FTS-kandidaten worden vóór de limiet op relevantie gerangschikt. ‘Onthou dit’ en
‘vergeet dat’ binden één duidelijke eigen uitspraak/geheugenversie. Ook expliciete
geheugenlijst-antwoorden worden als afgeleide bron gevolgd, zodat vergeten feiten
niet via een oud lijstantwoord terugkomen. Algemene ambiguïteit vraagt een keuze.
Negen nieuwe privacy-/referentietests; laatste volledige serverregressie **355
geslaagd**, 141,84 s. Windows **99 geslaagd**, Android **14 instrumented tests,
0 fouten** plus unit/lint/debug/release. Alleen eigen test-AVD/fixture gebruikt.
Architectuur-, context-, geheugen-, security-, persoonlijkheids- en handmatige
testdocumentatie toegevoegd; PHASE_7_5_TEST_REPORT.md houdt beperkingen expliciet bij.
Remote checks voor 084baad inmiddels allemaal geslaagd. Nieuwere privacywijzigingen
krijgen nog hun eigen CI-run. Fase 7.5 blijft in uitvoering; echte 8765-server nog
niet gemigreerd, geen fase-8-/productie-/mini-pc-werk.

### Eén gesproken ja voor mail en agenda — 24 november 2026

Nieuwe expliciete opdracht vervangt de eerdere beperking op een korte ja:
mail/agenda voorbereiden en voorlezen, één ja voert het actuele voorstel uit;
nee weigert. Op bestaande feature/chat-approvals / PR #24 voortgezet, omdat de
onderliggende wijziging nog door GitHub Actions geblokkeerd is. Geen merge of
omzeiling van checks. Alle bestaande preview-/sessie-/payload-/vervalguards en
actuele automation:approve blijven gelden. De bevestiging komt niet bij de AI.

Mailopdracht maakt een geverifieerd Gmail-concept en automatisch een afzonderlijk
verzendvoorstel. De sendjob heeft een eigen idempotencykey; dezelfde geverifieerde
snapshot hergebruikt een bestaande sendjob. Geen dubbele verzending bij herhaling.
‘Alleen een concept’ of ‘niet versturen’ blijft concept-only. Ja zonder voorstel
in hetzelfde gesprek bevestigt niets; een dubbele ja na succes leest de status.

51 gerichte tests geslaagd, inclusief synthetische STT→chat→TTS→STT ‘Ja, graag’
→eenmalige executor voor zowel mail als agenda; nee, ontbrekend approverrecht,
ander/onderbroken gesprek en alleen-concept. Geen echte accountmutatie uitgevoerd.
Volledige regressiesuite: 255 servertests geslaagd. Echte Groq/GPT-OSS 120B met
tijdelijke SQLite en gemockte Google: mail maken→preview→één ja→eenmalig verzonden,
en afspraak→preview→één ja→aangemaakt geslaagd. Extra ja voert niet opnieuw uit.
Geen echte accountmutatie. Pip check, repository-/whitespacecontrole geslaagd;
Bandit nul middel/hoge signalen. Geen actieve chat-/externe taken bij de
gecontroleerde serverherstart op loopback:8765; credentials/voorstellen behouden.
Windows/Android gebruiken dezelfde spraak-/chatroute; geen client-/APK-rebuild.

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
