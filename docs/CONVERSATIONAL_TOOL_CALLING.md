# Gesprekstools — fase 7.5 in uitvoering

De bestaande `AutomationChat`, gesloten `REGISTRY`, Pydantic-modellen,
PermissionManager, AutomationEngine en ApprovalManager blijven de enige route
naar agenda/mail/automatiseringen. De NaturalConversationManager start geen
tweede executor. E-mailinhoud, afspraaktekst en geheugen zijn gegevens, nooit
opdrachten of toestemming. Geproduceerde code/shell/plugins worden niet uitgevoerd.

## Verwerking

1. Een geauthenticeerde chat- of voicebeurt bevat huidige gebruikersinstructies.
2. De planner krijgt alleen toegestane schemas en begrensde bestaande referenties.
3. Backendvalidatie controleert tool, types, apparaatrechten en zelfstandigheidsregels.
4. Nederlandse datum/tijd/duur voor een nieuwe afspraak worden tegen de echte
   gebruikerswoorden gecontroleerd. Modeldatums kunnen die woorden niet vervangen.
5. Leesresultaten worden rechtstreeks weergegeven. Schrijfopdrachten worden een
   idempotente taak of een exact gebonden voorstel in de bestaande database.
6. Pas na de geldige beslissing voert de bestaande scheduler de externe wijziging uit.

## Nederlandse afspraakgegevens

`natural/temporal.py` herkent relatieve/absolute datums, weekdagen, half-/kwarttijden,
relatieve tijden en duur. `natural/calendar.py` voegt afzonderlijke gebruikersbeurten
samen, waarbij nieuwe datum/tijd/duur alleen de genoemde velden vervangen. Bekende
gegevens blijven behouden. Onduidelijke dagdelen en DST-gaten/dubbele tijden vragen
verduidelijking. Configureerbare werktijden helpen bij het onderscheid 03:00/15:00.

Een complete zin zoals ‘Maak volgende week vrijdag om half vier een afspraak van
twee uur met Noah en herinner me er een dag van tevoren aan’ wordt 15:30–17:30,
met een popup 1440 minuten vooraf. De ingestelde agenda/duur/herinnering gelden
alleen wanneer daarvoor standaardwaarden zijn toegestaan. Een persoonlijke afspraak
met een naam verzint geen uitnodigingsadres; externe genodigden moeten expliciet
vermelde e-mailadressen hebben. De volledige preview toont genodigden en herinnering.

Google ondersteunt hiervoor `reminders.useDefault=false` en een `popup`-override
van 0 tot 40320 minuten. Zie [Events](https://developers.google.com/workspace/calendar/api/v3/reference/events)
en [Reminders](https://developers.google.com/workspace/calendar/api/concepts/reminders).

Bij verplaatsen komt het oorspronkelijke tijdstip/de duur uit de eerder werkelijk
opgehaalde afspraak met ID/ETag. Modelgissingen zijn geen bron voor het oorspronkelijke
tijdstip. De bestaande integratie bewaart niet gewijzigde velden en controleert ETag.

## Correcties en goedkeuring

‘Nee, toch vrijdag om vier uur’ kan een nog niet goedgekeurd CalendarCreate-voorstel
vervangen. De oude taak moet in dezelfde transactie nog `approval` zijn voordat
annulering is toegestaan; een inmiddels uitgevoerde taak wordt niet teruggedraaid.
De vervanging krijgt een eigen voorstel, volledige preview en nieuwe goedkeuring.

‘Ja’, ‘doe maar’, ‘dat is goed’ en ‘akkoord’ gebruiken dezelfde eenmalige binding aan
taak, payload, laatst volledig getoonde preview, chatbeurt, sessie, rechten en vervaltijd.
‘Nee’, ‘laat maar’ en ‘annuleer dat’ wijzen hetzelfde voorstel af. Een losse bevestiging
zonder actuele preview verleent geen nieuwe toestemming. De AI ontvangt geen nonce.
Meerdere open voorstellen worden niet gezamenlijk door een algemeen ja goedgekeurd.

Een concrete aanvulling op een ontbrekend taakveld kan na een tussenvraag worden
hervat; een kaal ‘ja’ na een ander gespreksonderwerp kan die taak niet activeren.
Taakreferenties overleven een herstart, goedkeuringsgeheimen en oude previewautoriteit
niet. Wijzigingen aan reeds aangemaakte afspraken blijven gewone nieuwe voorstellen.

## Samengestelde opdrachten

`natural/intents.py` gebruikt een strikt Pydantic-plan met maximaal het ingestelde
aantal stappen. Iedere stap moet een letterlijk, opeenvolgend en niet-overlappend
deel van de echte gebruikerszin zijn. Een model kan daardoor geen extra opdracht
of ontvanger toevoegen tijdens de decompositie. Iedere intentie beperkt bovendien
opnieuw de gesloten toolset. Afhankelijkheden mogen alleen naar eerdere stappen
wijzen; er zijn geen cycli of willekeurige code.

Stappen worden nu opeenvolgend uitgevoerd, zodat gedeelde verwijzingen betrouwbaar
blijven. Onafhankelijke stappen gaan verder bij een lokale fout. Een afhankelijke
stap wacht wanneer een eerder extern voorstel nog op goedkeuring wacht. Iedere
schrijfstap heeft een eigen idempotency-key. Een afspraakherinnering vooraf blijft
onderdeel van dezelfde kalenderactie. Geciteerde mailtekst wordt niet als een extra
opdracht ontleed. Meerdere voorstellen vragen eerst een specifieke selectie;
één voorstel plus leesresultaten bindt de goedkeuring aan het gehele parentantwoord.

## Bewijs en resterend werk

Deterministische tests dekken slotcorrecties, Nederlandse tijden/DST, modelgissingen,
persoonlijke versus externe afspraak, exact gebonden bevestigingen en de werkelijke
Google-requestbody via MockTransport. Er zijn geen echte accounts gewijzigd.
Zeven aanvullende intenttests controleren bronbinding, afhankelijkheden,
deelproblemen, gecombineerde leesresultaten, idempotency-keys en previews.
Alle conflict-/alternatiefvoorkeuren, automatisch vervolg van wachtende
afhankelijkheden en alle contextuele mailcorrecties zijn nog in uitvoering. Zie het actuele testrapport en
DEVELOPMENT_PROGRESS.md; deze module alleen voltooit fase 7.5 niet.
