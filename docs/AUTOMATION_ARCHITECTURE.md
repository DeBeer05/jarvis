# Fase 7 — automatiseringen

Eén bestaande FastAPI-server, loopback **127.0.0.1:8765**. Geen tweede backend,
publieke binding, Windows-service, mini-pc of oproepen. Bron: server/automation/.

| Component | Verantwoordelijkheid |
|---|---|
| AutomationEngine | Gesloten toolregistratie, validatie, uitvoering en herstel |
| TaskScheduler / TriggerManager | Eén asyncio-taak, elke vijf seconden maximaal tien lokale vervallen taken |
| WorkflowManager | Persistente reeks stappen; volgende stap pas na geslaagde vorige |
| ActionExecutor | Vaste Python-handlers, nooit eval, shell of gegenereerde code |
| PermissionManager | Expliciete apparaatrechten bij indienen en opnieuw bij externe uitvoering |
| ApprovalManager | Eenmalige, apparaatgebonden challenge, vijf minuten geldig |
| NotificationManager | Centrale inbox, categorieën, stilte, limiet en deduplicatie |
| FollowUpManager | Gmail-thread-ID's vergelijken; antwoord altijd ter beoordeling |
| AuditLogger | Begrensde gebeurtenissen zonder berichtinhoud of geheimen |
| IntegrationManager | Officiële Google OAuth/REST, begrensde requests en tokenvernieuwing |

SQLite-schema 4 behoudt bestaande accounts en gesprekken en maakt vóór migratie
een .pre-v4-*.bak naast de database. Er worden geen eigen herinneringen of
automatiseringen aangemaakt bij installatie. JARVIS_ENABLE_AUTOMATIONS=true
activeert de scheduler; false pauzeert het uitvoeren globaal. API's blijven
authenticatie en rechten vereisen.

Tools: CalendarRead/Create/Update/Delete, EmailSearch/Read/Draft/Send,
ReminderCreate/List/Cancel, NotificationSend, WorkflowCreate/Status. Aanvullend:
CalendarSummary, EmailCheck en WaitForReply. Dagelijkse CalendarSummary bepaalt
het dagvenster opnieuw, in plaats van steeds dezelfde oude dag op te halen.
Read-fouten krijgen begrensde exponential backoff. Externe wijzigingen nooit
automatisch opnieuw na een onzeker HTTP-resultaat. Zie WORKFLOW_ENGINE.md.

De bestaande AI-router krijgt summarize_untrusted en propose_tool. Een model
maakt alleen een schema-gevalideerd voorstel; de gebruiker dient dat afzonderlijk
in. Ontbrekende afspraak/ontvanger vereist verduidelijking. Externe inhoud komt
uitsluitend in samenvattingen, zonder toegang tot een executor. Er wordt geen
nieuwe modelprovider of desktop-Gemini/GUI-stack in de server geïmporteerd.

Bediening: web /automations, Windows → Automatiseringen, Android →
Automatiseringen. Complexe actiegegevens zijn in deze versie ook als JSON
beschikbaar; herinneringen en agenda/inbox-zoekacties hebben eigen bediening.
De lijst toont twintig taken, goedkeuringen eerst; API ?offset=20 pagineert.

Meldingen worden in een geauthenticeerde inbox bewaard. Windows controleert die
elke dertig seconden zolang het proces draait; Android alleen op de voorgrond.
Externe FCM-bezorging ontbreekt nog. Op een vergrendelscherm staat alleen een
generieke melding. Een nieuwsprovider en urgent-calltrigger zijn interfaces voor
later; er is geen actieve nieuwsbron of oproeptransport.
