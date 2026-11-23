# Google Calendar koppelen en testen

1. Maak in Google Cloud je eigen project. Activeer Google Calendar API en Gmail
   API indien gewenst. Stel het OAuth-toestemmingsscherm in en voeg je eigen
   **testaccount** toe. Publiceer de app niet voor deze ontwikkelproef.
2. Maak een OAuth-client van type **Desktop app**. Bewaar de gedownloade JSON als
   C:\Users\beren\Desktop\J.A.R.V.I.S\secrets\google-desktop.json. secrets/ wordt
   door Git uitgesloten. Deel het bestand niet in chat of GitHub.
3. Zet lokaal in .env:

```dotenv
JARVIS_ENABLE_AUTOMATIONS=true
JARVIS_GOOGLE_CLIENT_FILE=secrets/google-desktop.json
```

4. Installeer de gewijzigde serverrequirements en herstart gecontroleerd vanuit
   C:\Users\beren\Desktop\J.A.R.V.I.S:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-server.txt
powershell.exe -NoProfile -File scripts/Stop-Server.ps1
powershell.exe -NoProfile -File scripts/Start-Server.ps1 -Background
```

5. Open http://127.0.0.1:8765/automations op de computer en log zelf in. Selecteer
   onder Gekoppelde accounts alle gewenste rechten en klik Google koppelen.
   Open de getoonde Google-link in dezelfde computerbrowser en geef toestemming.
   Gebruik voor deze Desktop OAuth-flow de computer, niet de telefoonbrowser.
6. Via Agenda’s ophalen zie je agenda-ID's. Zoek een afgebakend tijdvak. De
   zoekroute retourneert maximaal honderd occurrences met eventuele nextPageToken;
   verklein het tijdvak bij een onvolledig resultaat. Terugkerende afspraken
   worden door Google naar afzonderlijke occurrences uitgebreid.

Calendar lezen gebruikt calendar.readonly, wijzigen calendar.events. Tokens
blijven op Windows via gebruikersgebonden DPAPI versleuteld; refresh wordt
automatisch vernieuwd. Geen plaintext fallback op Linux. Een nieuwe koppeling
vervangt de vorige; selecteer dus alle toegang die je wilt behouden.

Voor verzetten: selecteer een exact event-ID, nieuwe start/eindtijd met offset en
tijdzone, en vraag /api/v1/automation/reschedule om analyse. De API zoekt overlap
en buren, bewaart de deelnemers en ETag, vermeldt dat reistijd onbekend is en
retourneert een CalendarUpdate-voorstel. De eigenaar kan buffertijd instellen via
PUT /api/v1/automation/rules. Geen kaartdienst of verzonnen reistijden.

Controleer voorstel, deelnemers, tijden en of het een occurrence of serie betreft.
Alle CalendarCreate/Update/Delete-acties vragen hier veilig standaard approval,
ook een eigen afspraak. Google ontvangt If-Match bij wijzigen/verwijderen.
Een ondertussen gewijzigde afspraak vereist een nieuw voorstel. Wijzigingen
worden na uitvoering teruggelezen; een succesvolle conditionele DELETE geldt
als providerbevestiging. Een onzekere actie wordt niet opnieuw verstuurd.

Test eerst met een apart testaccount/testagenda. Er is geen echte Google-
integratietest uitgevoerd of toestemming gegeven om jouw afspraken te wijzigen.
Google-toegang intrekken kan in JARVIS of via je Google-account. Bij ontbrekende
clientconfiguratie, scopes of verlopen toestemming moet je opnieuw koppelen.

Bronnen: [Desktop OAuth/PKCE](https://developers.google.com/identity/protocols/oauth2/native-app),
[conditionele Calendar-wijzigingen](https://developers.google.com/workspace/calendar/api/guides/version-resources),
[Events update](https://developers.google.com/workspace/calendar/api/v3/reference/events/update).
