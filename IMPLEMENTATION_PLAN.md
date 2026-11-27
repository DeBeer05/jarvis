# Persoonlijke butler — uitvoeringsplan

Opdracht 27 november 2026. Dit zijn de acht nieuwe productfases, niet de eerdere
versienummers 7/7.5. De eigenaar heeft implementatie van alle acht opgedragen.
Geen productie-/Oracle-migratie, nieuwe apparaatgrant, echte externe mutatie of
betaald abonnement wordt hierdoor automatisch geautoriseerd. Poort 8765,
Qwen2.5:3B en bestaande Windows-/Android-/upstreamcode blijven behouden.

## Onderzochte basis en werkwijze

- `server/natural/`: centrale instellingen, SQLite/FTS5-geheugen, contacten,
  brongebonden vergeten, gedeelde gesprekken, compacte context, TTS-router.
- `server/automation/`: gesloten tools, scheduler, persistente jobs, notificaties,
  approvals, idempotentie en Google Calendar/Gmail. Geen tweede taakengine bouwen.
- Native Windows en Android: gedeeld dynamisch instellingenschema, eigen veilige
  credentials, bestaande spraakhelper, gesprekslease/overname, echo- en barge-in.
- Upstream `core/tasks/`, `plugins/`, `gui/` is een aparte stack; geen imports
  hiervan in de headless backend. Externe pluginbestanden worden geen shellrechten.
- Bestaande eigenaarwijzigingen in mail_digest en bijbehorende tests blijven apart.
- Per fase: noodzakelijke delta, gerichte negatieve/integratietests, regressie,
  documentatie en eigen commit. Extern geblokkeerde acceptatie blijft zichtbaar;
  onafhankelijk werk gaat verder. Geen mock als werkende integratie presenteren.

## Fases en voortgang

| Fase | Bestaand | Ontbrekende delta / bewijs | Status |
|---|---|---|---|
| 1 Persoonlijkheid/geheugen | Butler, instellingen, contact-/voorkeurgeheugen, historie, bronvergeten | Gerichte episodische retrieval tussen gesprekken; toon op context, correctie zonder extra classifier; restart/apparaat/privacytests | Technisch afgerond; menselijke acceptatie open |
| 2 Aanwezigheid/modi | Gespreksstatus, clientstatus, meldingsbeleid | Acht modi, handmatig/automatisch, begrensde OS-signalen met opt-in, persistente transitions en eenmalige terugkomst | Technisch afgerond; echte apparaatacceptatie open |
| 3 Persoonlijke assistentie | Calendar/Gmail, conflictcontrole, follow-up, scheduler, quiet hours | Brongebonden briefings/routines/lijsten, connectorstatus, prioritering; actuele weer/nieuws/verkeer alleen echte bron | Kern technisch afgerond; verkeer/telefonie/bankkoppeling ontbreken extern |
| 4 Spraak | ElevenLabs, tekst-/zinsstreaming, lokale Whisper/Piper, echo/barge-in, foreground vervolg | Meetbare streaminggrenzen, hervatten en fallback audit; echte audioacceptatie apart | Technisch afgerond; menselijke audioacceptatie open |
| 5 Windows/Android | Native clients, apparaatpairing, Windows gesloten acties | Toegestane OS-acties/status, Android ondersteunde intents/toestemmingen en achtergrondsync; geen WhatsApp/Signal-API verzinnen | Nog niet gestart; grants/telefoon nodig voor echte tests |
| 6 Externe omgeving | Bestaande scherm-/apparaatrechtstructuur | Opt-in schermcontext, ondersteunde HA/Creality/navigatieadapters en capabilities | Nog niet gestart; endpoints/apparaatconfig extern |
| 7 Betrouwbare autonomie | Jobs, scheduler, approvals, audit, dedup, revoke, secretstore | Centrale events integreren, begrensde retries/prioriteit/deadlines, noodstop en expliciete undo-capabilities | Nog niet gestart; hergebruik engine |
| 8 Interface/instellingen | Dynamische gedeelde instellingen, taken/logs, usage en diagnose | Nieuwe fases zichtbaar op beide clients, ontbrekende configuratie tonen, testhandleiding en builds | Nog niet gestart; na voorgaande deltas |

## Afhankelijkheden en acceptatie

- Locatie en optionele briefingtijden zijn gevraagd; zonder antwoord geen
  locatie-inferentie of stille periodieke informatiepolling.
- HA/printer/auto/bericht-/telefoniediensten en apparaatmodellen zijn gevraagd.
  Secrets uitsluitend via veilige lokale invoer. Geen aanschaf of echte oproep.
- Automatische detectie vereist eigenaartoestemming per apparaat; appnamen,
  schermbeelden en locatie worden niet standaard verzameld.
- Elke actie behoudt actuele serverrechten en uitvoeringsbewijs. Externe tekst
  kan geen grant, opdracht of approval geven. Onzeker resultaat nooit blind retryen.
- Tests gebruiken synthetische accounts/fixtures en transportmocks. Daarbovenop
  afzonderlijke echte apparaat-/luisteracceptatie; geen productieclaims uit mocks.
- Laatste basis: ea09cb6, 604 tests + 1 skip, 12 CI-checks groen; bekende incidentele
  Qt-testabort is niet als opgelost bestempeld. `docs/PROGRESS.md` is het hervatpunt.


### Fase 1 — testbewijs

Migratie/restart/privacy/FTS-regressies geslaagd (12 tests), finale gerichte
geheugen/context/instellingenreeks 24 passed. Brede reeks 608 passed/1 skip;
alleen een oude backupbestandsnaamassertie faalde en is afzonderlijk hersteld
en geslaagd. Ruff/mypy (39 modules), pip check, contract, repository en
geheimcontrole geslaagd. Geen echte accounts, TTS of modeldownloads gebruikt.

### Fase 2 — testbewijs en grenzen

- Acht handmatige modi, opt-in automatische signalen, persistente transities en
  apparaatgebonden events/ontvangstbewijzen. Privé forceert nieuwe beurten lokaal,
  zonder opgeslagen gesprekstekst; geen nieuwe grants of uitgevoerde acties wissen.
- Windows: WTS-lock/unlock, initiële sessiestatus, idle en optionele lokale
  procesclassificatie. Android: lock/idle zolang app vooraan staat; opt-in
  achtergrondservice volgt in fase 5. Geen Android-appgebruik of locatie verzameld.
- Volledige serverreeks: 617 passed/1 POSIX-skip; finale gerichte reeks 15 passed.
  Windows-client 136 passed; Android 8 unit tests, lint, debug/release builds groen.
  Ruff/mypy, contract, dependencies en repositorycheck groen. Echte toestemmingen,
  lock/unlock en telefoon niet gesimuleerd als gebruikersacceptatie.
- Fase-1-CI: 11 groen, één bekende offscreen-Qt-abort op test_window.py:130.
  Niet als opgelost gemeld; nieuwe head wordt opnieuw volledig door CI getest.
- Locatie, briefingtijden en bestaande koppelingen zijn ontvangen. Persoonlijke
  configuratie blijft buiten Git. Ondersteunde mogelijkheden van Phone Link en
  Creality Cloud worden vóór connectorimplementatie geverifieerd. Een geplande
  melding is geen echt ochtendtelefoontje; daarvoor moet een oproeproute bestaan.

### Fase 3 — testbewijs en externe grenzen

- Brongebonden ochtend-/avond-/terugkomstbriefings, voorbereiding tijdens afwezigheid,
  bestaande agenda-/Gmailrechten, conflictvoorstellen, Open-Meteo en NOS. Geen LLM
  voor periodieke verwerking; begrensde caches en bronfouten zichtbaar.
- SQLite v11: lokale boodschappen, abonnementen, gelegenheden, routines en
  sollicitaties. Revisions/idempotentie, maand-/jaarherhaling en gekoppelde
  bestaande reminders/reply-watches; bewerken/verwijderen annuleert oude jobs.
- Brede serverreeks 629 passed/1 skip; daaropvolgende kalender/briefingregressies
  60 passed en finale briefing/automationreeks 37 passed na follow-upcorrecties.
  Ruff/mypy (44 modules), pip check, structuur en Android-contract groen.
- Echte openbare weerproef geslaagd; Google/ElevenLabs uitsluitend mocks. Geen
  echte mail-/agenda- of telefoonactie. De eigenaar kiest voorlopig appbriefings;
  geen ondersteund oproepkanaal, live verkeer, bank- of locatiegrant beschikbaar.
- Nieuwe backendcode nog niet live geactiveerd; clientformulieren volgen fase 8.

### Fase 4 — incrementele STT

- Bestaande tekst-/zins-TTS-streaming, ElevenLabs, lokale fallback, echo, barge-in
  en apparaatleases hergebruikt. Geen nieuwe spraakdienst, model of download.
- Opt-in incrementele STT op Windows/Android: tijdens spreken maximaal één
  request tegelijk, nieuwe PCM-delen met 500 ms overlap, tekstsamenvoeging en
  laatste restaudio bij beurt-einde. Voorlopige tekst activeert nooit chat/tools.
  Opnamen/transcripten blijven capture-lokaal; bestaande geauthenticeerde route.
- Standaard uit voor compatibiliteit; geen belofte van woord-voor-woord vendor-
  streaming. De CPU verwerkt segmenten, geen groeiende hele opname per pauze.
- Voorlopige herkenning begrensd op acht seconden; geen late publicatie na
  annuleren/verlopen. Normale herkenning blijft beschikbaar bij mislukte proef.
- 140 Windows-clienttests, 28 gerichte server/ElevenLabs-tests, lint/types groen.
  Android unit/lint/debug/release ook na laatste timeoutaanpassing geslaagd.
  Menselijke microfoon-/luisteracceptatie nog afzonderlijk.
