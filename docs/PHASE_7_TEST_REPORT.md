# Testverslag fase 7

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
