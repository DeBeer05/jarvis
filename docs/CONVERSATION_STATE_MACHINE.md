# Centrale gesprekstoestanden

Implementatie: `server/natural/conversation.py`. De bestaande FastAPI-backend op
8765 bezit de sessie; clientaudio en AI-provider zijn vervangbare adapters.
Schema 5 slaat sessie, apparaat, authenticatiesessie, epoch, revision en lease op.

| Toestand | Betekenis |
|---|---|
| STANDBY | Geen actieve audiosessie |
| ACTIVATING | Bewuste activatie of expliciet hervatten |
| LISTENING | Klaar voor gebruikersspraak |
| USER_SPEAKING | Gebruiker spreekt |
| PROCESSING | Invoer wordt verwerkt |
| THINKING | De bestaande chatrouter verwerkt de beurt |
| ASSISTANT_SPEAKING | Antwoord wordt geleverd/uitgesproken |
| INTERRUPTED | Oude audiogeneratie ongeldig gemaakt |
| WAITING_FOR_INFORMATION | Gevalideerde taakcontext mist gegevens |
| WAITING_FOR_APPROVAL | Concreet backendvoorstel wacht op toestemming |
| EXECUTING_ACTION | Uitvoering binnen de bestaande AutomationEngine |
| RECONNECTING | Herstart/netwerkherstel vraagt expliciet hervatten |
| ENDING | Stoppen en vrijgeven van de lease |
| ERROR | Verwerkingsfout; geen verzonnen uitvoeringssucces |

De toegestane overgangen zijn expliciet vastgelegd in `TRANSITIONS`. Clients
kunnen geen `EXECUTING_ACTION` of andere vertrouwde backendstaat opgeven.
Chat met `channel=voice` en `session_epoch` controleert de actuele lease vóór
opslag, vóór generatie en vóór het afleveren van antwoorddelen.

## Sessies en races

`POST /api/v1/natural/conversations/start` activeert een nieuw gesprek of hervat
een bestaand gesprek van dezelfde gebruiker. Een actieve lease op een ander
apparaat geeft 409; uitsluitend `takeover=true` neemt haar expliciet over.
Overnemen en onderbreken maken oude callbacks ongeldig via een hogere epoch.
De gewone `conversation_id` en taak-/goedkeuringsgeschiedenis blijven behouden.

`POST /api/v1/natural/conversations/{id}/events` accepteert alleen de beperkte
clientevents met de actuele epoch. De lease duurt maximaal 60 seconden en wordt
door native clients met heartbeats vernieuwd. Een heartbeat geldt niet als
gebruikersactiviteit en omzeilt geen inactiviteits- of maximale sessieduur.
`GET /api/v1/natural/conversations/{id}/state` toont toestand en actief apparaat.

Alle mutaties zijn asynchroon geserialiseerd en SQL-transacties duren alleen
tijdens databasewerk. Netwerk- en inferencewerk houdt geen DB-lock vast.
De bestaande ChatService reserveert daarnaast maximaal één generatie per gesprek.
Onderbreken stopt audio/generatie; uitgevoerde externe acties worden niet ongedaan
gemaakt. De bestaande idempotency keys en exact gebonden approvals blijven leidend.

Na serverherstart worden actieve sessies `RECONNECTING` en oude epochs ongeldig.
Taken blijven opgeslagen. Hervatten creëert een nieuwe audiolease, geen nieuwe
automatische taakuitvoering.

## Windows-adapter

`voice/session.py` gebruikt bestaande geauthenticeerde workers voor claims,
events en heartbeats. Late antwoorden kunnen een uitgelogde/gewijzigde sessie
niet opnieuw openen. Een overname wordt alleen via de expliciete knop gestart.
Een centrale instelling opent nooit zelf de microfoon: lokale toestemming en
PTT-/wakeactivatie blijven vereist.

Een geconfigureerde doorlopende modus behoudt de activatie over meerdere
beurten. Afsluitzinnen moeten de hele uitspraak zijn: ‘Bedankt JARVIS, maar …’
is geen afscheid. Wakefraseherkenning is momenteel transcriptiegebonden,
geen apart getraind wakewordmodel. Windows en Android ondersteunen nu centrale
leases en onderbreking van spraak/generatie met behoud van duurzame taken.
De optionele duplexmonitor is in software getest; zie VOICE_STREAMING.md voor
echo- en hardwarebeperkingen. De 14 waarden alleen bewijzen geen hardwareacceptatie.
