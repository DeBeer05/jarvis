# Testverslag fase 7

## Goedkeuringen in de chat — 24 november 2026

249 volledige servertests en 45 gerichte chat-/automatiseringstests geslaagd.
Nieuwe gevallen: volledige kalenderpreview met jaartal, eenmalige expliciete
Goedkeuren/Weigeren, geverifieerde mailpreview, ontbrekende approverrechten,
herhaalde beslissingen, meerdere voorstellen/selectie, verlopen/gewijzigde/
onderbroken preview, wijziging tijdens challenge en te grote/onvolledige preview.
Een afgebroken preview geldt nooit als volledig getoond. Payloadfingerprint
wordt in de beslissingstransactie opnieuw gecontroleerd. Nonce blijft buiten
chat/model/logs; alleen bestaande digestopslag. Geen schema-/clientwijziging.

Echte Groq/GPT-OSS 120B met tijdelijke database en gesimuleerde executor: eerste
afspraakvraag, aanvullende tijden, volledige preview, Goedkeuren en confirmed
completed geslaagd. Geen echte Google-accountmutatie. Server-pip check,
repository-/indexgeheim-/whitespacecontrole geslaagd; Bandit nul middel/hoge.
Gecontroleerde serverstart: health/ready 200, anonieme automation-API 401.
Windows 0.7.1 en Android 0.7.0 blijven dezelfde chatroute gebruiken.

## AI-chat en spraakbediening

26 nieuwe tests voor geregistreerde tools via de bestaande geauthenticeerde
chat/SSE, providerkeuze/fallback, actuele scopes, tokenrefresh/revoke, annulering,
concept-snapshots, externe goedkeuring, verval/isolatie van referenties, ongeldige
plannen en e-mailinhoud zonder executor. De synthetische mobiele spraakproef dekt
STT→toolchat→TTS; geen nieuwe echte microfoonproef of Google-accounttest.

Volledige serversuite: **228 geslaagd**. Windows-client: **75 geslaagd**.
Server pip check, repository-/whitespacecontrole geslaagd; Bandit nul middel/hoge
bevindingen. Echte lokale Ollama Qwen2.5 3B met tijdelijke SQLite en gemockte
Google geeft agenda-/mailresultaten en een opgeslagen herinnering. De proef vond
CalendarList/Read-verwarring: beschikbare tools zijn nu per vraag beperkt; een
ondubbelzinnig alternatief JSON-formaat wordt gevalideerd geaccepteerd. Nederlandse
daggrenzen worden serverzijdig berekend. Geen aannames over live Google-resultaten.

Gebruikersscreenshots reproduceerden onnodige agenda-bevestiging en een verloren
‘de 1e’-mailreferentie. Gerichte regressies dekken directe dagopvraag, ordinale
mailinhoud en behoud van een korte leesverduidelijking. Een echte Groq/GPT-OSS
120B-proef met tijdelijke database en gemockte Google slaagt met beide exacte
formuleringen en de vervolgverwijzing. Geen echte accountdata of berichten gebruikt.

De bestaande server is gecontroleerd herstart op 127.0.0.1:8765, met behoud van
accounts, config en Google-credentials. Geen clientwijziging, build of APK nodig.
Remote CI en integratie naar develop worden apart vastgelegd in de PR.

## Herstel Google-setup en webassets

Een gebruikersmelding ontdekte een ontbrekende allowlistvermelding: de algemene
/chat/assets/{name}-route ving automations.js af vóór de specifieke route. Dit
gaf JSON-404 en een correcte nosniff-weigering. De bestaande assetroute verzorgt
het bestand nu zelf; de onbereikbare dubbele route is verwijderd. Na echte
herstart bevestigd: 200 text/javascript, ready 200, anonieme automation-API 401.
De test volgt nu daadwerkelijk de scriptverwijzingen uit de HTML.

Google-koppelen.bat en helpers: zes gerichte tests geslaagd voor configbehoud,
ongeldig clienttype, alleen controleren, PowerShell-pad met spaties, vier
voorgeselecteerde rechten en redirect-allowlist. Volledige tussenronde: 199
servertests geslaagd; daarna de aanvullende JS-regressietest afzonderlijk.
Geen echte OAuth-credentials gekozen/gekopieerd, Google-consent of externe
accounttest uitgevoerd. De helper vereist expliciete selectie door de gebruiker.

Geïmplementeerd op feature/smart-automations vanaf develop c405304 (fase 6/PR #17).
Alle automatische functionele tests gebruiken tijdelijke synthetische accounts/
databases. Daarna is de echte server afzonderlijk gecontroleerd herstart. Schema
4, een voorafgaande backup en behoud van het eigenaaraccount zijn bevestigd.
Health/ready/webscherm geven 200, anonieme automation-API's geven 401. Er zijn
nul echte automatiseringstaken en geen Google-accountkoppelingen aangemaakt.
Lokale fase-/schedulerflags zijn bijgewerkt zonder credentials te wijzigen.

Bevestigd: 194 servertests, waarvan 22 nieuwe automatiseringstests;
75 Windows-clienttests. Remote CI wordt op dezelfde featurehead gecontroleerd
vóór integratie naar develop; main blijft ongewijzigd.
Integratie via [PR #18](https://github.com/DeBeer05/jarvis/pull/18).

Gedekt: SQLite-persistentie/idempotentie, herstel van reads en onzekere externe
acties, workflowstappen/pauzeren/annuleren, expliciete devicegrants/intrekking,
approvalverval/replay, echte Windows-DPAPI-ciphertext, OAuth-state/PKCE/refresh/
intrekking met MockTransport, afgewezen cross-site writes en toegestane maar
state-gecontroleerde callback, Calendar-conflict/recurrence/ETag, Gmail-concept-
hash/preview en immutable verzendbytes, metadata-prioriteit, handmatige messaging,
follow-updeduplicatie en prompt-injection die geen executor kan aanroepen,
zomertijd en stille/gelimiteerde meldingen, Windows-scherm en wissen bij uitloggen.

Android: nieuwe native automationtest met echte TCP naar uitsluitend de eigen
synthetische fixture, minimale testgrant, reminder/idempotentie en geweigerde
eenmalige approval. De eerste volledige emulatorsuite vond een UX-probleem:
het nieuwe scherm deed zonder automatiseringsrechten direct een API-verzoek,
waardoor de loginredirect het scherm verving. Nu blijft het scherm zichtbaar met
uitleg over de benodigde eigenaargrant. De suite wordt opnieuw uitgevoerd.

Geen echte Google OAuth-, Calendar- of Gmail-accounttest, geen externe FCM-
bezorging, geen WhatsApp/SMS-transport of fysieke telefoonproef geclaimd. Echte
spraakregressie op de emulator gebruikt de reeds goedgekeurde Piper/Whisper-
modellen en synthetische spraak; hostmicrofoon staat uit. Geen testmail verzonden.

## Handmatige acceptatie

1. Installeer serverrequirements, zet lokaal de scheduler aan en herstart de server.
2. Open /automations, verleen alleen gewenste rechten aan jouw native apparaat.
3. Maak een herinnering voor over twee minuten. Controleer op beide clients;
   herstart de server vóór het tijdstip en controleer dat precies één melding komt.
4. Test pauzeren/hervatten/annuleren, een dagelijks tijdstip, stilteuren en uitval.
5. Configureer je eigen Desktop OAuth-client volgens CALENDAR_INTEGRATION.md.
   Gebruik eerst een apart testaccount/testagenda. Koppel lezen; controleer dat
   schrijven zonder die scope niet doorgaat. Trek de toegang weer in.
6. Na eigen expliciete testtoestemming: maak een testafspraak/-concept, controleer
   alle gevolgen, weiger eerst, keur daarna een nieuw voorstel goed. Controleer
   bij Google het echte resultaat en test een ondertussen gewijzigde afspraak/
   concept. Controleer replay-/onzekere uitkomsten zonder opnieuw te versturen.
7. Test een workflow met veilige lokale stappen en daarna met een approvalstap.
   Herstart tijdens wachten, trek apparaatrechten in en controleer dat uitvoering
   stopt. Een ontvangen e-mail met instructies mag geen acties activeren.

## Bevestigde resultaten voor oplevering

- Volledige serversuite: **194 geslaagd**, één bestaande Starlette/httpx-warning.
  Daarvan 22 nieuwe gerichte automatiseringstests; laatste reviewwijzigingen
  aanvullend op die suite gecontroleerd.
- Windows: **75 tests geslaagd**. Native bronvenster visueel gecontroleerd met
  synthetische lege gegevens. Qt-offscreen had eerst geen Windows-font geladen;
  testfixture laadt nu de reeds aanwezige Segoe UI zodat de screenshot leesbaar is.
- Portable Windows 0.7.0 start echt: acht pagina's, venster zichtbaar, netwerk en
  microfoon/inferencehelper niet gestart in de geïsoleerde rookproef. De complete
  Windows-/spraakhelperbuild is geslaagd, inclusief laatste clientwijzigingen.
- Android: **5 JVM-tests en 7 instrumented tests geslaagd** op Android 16/API 36.
  Na een weggevallen ADB-tunnel is de suite rechtstreeks met de geïnstalleerde
  AndroidJUnitRunner herhaald op de definitieve APK: OK (7 tests), 19,205 seconden.
  Geen test overgeslagen.
  Debug-APK en unsigned releasebuild/lint geslaagd; lintregels niet uitgeschakeld.
- Debug-APK: .local/android-build/JARVIS-Android-0.7.0-debug.apk. SHA256:
  dff22d7158bab889c32e19b87283cf2077e951f1c82f96c7e893093bdbefafd1.
- Server-runtime-audit: nul bekende kwetsbaarheden. Bandit-server: drie lage
  bestaande subprocess-signalen, nul middel/hoge en geen suppressies.
- Repository-/whitespace-/geheimcontrole en echte PR-/merge-CI worden afzonderlijk
  gecontroleerd. Geen full-history geheimvrijverklaring: oude upstreamhistorie
  wordt behouden en niet herschreven.

STOP na fase 7. Geen volledige oproepen, productie of mini-pc-deployment.
