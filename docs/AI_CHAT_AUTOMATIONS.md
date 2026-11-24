# Agenda, e-mail en herinneringen via AI

Gebruik de normale chat in de bestaande web-, Windows- of Android-app. Spreek
dezelfde opdrachten via de bestaande spreekknop. De transcriptie gaat naar
dezelfde beveiligde chatroute; je hoeft geen nieuwe app of APK te installeren.
De server moet draaien en Google moet gekoppeld zijn voor agenda en e-mail.

Voorbeelden:

- `Wat staat er morgen in mijn agenda?`
- Spraakvariant: `Wat stond er voor vandaag in mijn agenda?`
- Na een agenda-opvraag: `En morgen?`
- `Welke agenda's heb ik?`
- `Toon de afspraken morgen in agenda "Werk".`
- `Toon mijn laatste e-mails.`
- Daarna in hetzelfde gesprek: `Lees de inhoud van de eerste e-mail.`
- Kort kan ook: `Wat staat er in de 1e?`
- Of: `Vat de inhoud van de eerste e-mail samen.`
- `Herinner me morgen om 18:00 aan planten water geven.`
- `Herinner me over 5 minuten aan pauze.`
- `Toon mijn herinneringen.` Vervolgens: `Annuleer die herinnering.`
- `Verzet mijn afspraak Tandarts van 14:00 naar 16:00 op 25 november 2026.`
- `Schrijf een conceptmail aan naam@example.com met onderwerp Test en tekst Hallo.`
- Na controle van het aangemaakte concept: `Verstuur die conceptmail.`

Geef ontbrekende datums, tijden, ontvangers of een onduidelijke afspraak concreet
aan. De AI kan om verduidelijking vragen. Grote of ingewikkelde afspraken en
workflows met schrijfacties moeten via de bestaande Automatiseringen-bediening
worden gecontroleerd. De lokale kleine AI is minder betrouwbaar in het plannen
dan grotere modellen; een ongeldig plan geeft een melding en wordt niet uitgevoerd.

## Rechten en goedkeuring

Als de AI meldt dat dit apparaat geen toegang heeft: open als eigenaar
http://127.0.0.1:8765/automations → Apparaatrechten. Geef het bedoelde apparaat
`automation:read` (bekijken) en voor herinneringen/concepten/voorstellen ook
`automation:write` (taken maken). Bestaande apparaten krijgen deze rechten nooit
automatisch. Alleen goedkeuren als het apparaat dat ook werkelijk nodig heeft.
Google-consent en de apparaatrechten zijn twee afzonderlijke controles.

Agenda aanmaken/wijzigen/verwijderen en e-mail verzenden leveren eerst een
voorstel op. Open **Automatiseringen → Goedkeuringen**, controleer exacte inhoud,
ontvangers en gevolgen en keur het daar goed. Een getypt of gesproken `ja` geeft
geen goedkeuring. Een concept wordt wel in Gmail aangemaakt, maar niet verzonden.
Een opgeslagen taak is pas uitgevoerd wanneer de engine dit heeft bevestigd.

## Gegevens en grenzen

Alleen de huidige expliciete gebruikersopdracht kan tools autoriseren. De planner
krijgt beperkte recente berichtgegevens/afspraakreferenties, geen e-mailbody.
E-mailzoeken toont maximaal vijf afzenders en onderwerpen; inhoud wordt alleen
bij een expliciet lees-/samenvattingsverzoek verwerkt. Een samenvatting gebruikt
de gekozen AI-provider; bij een cloudprovider gaat die opgevraagde inhoud dus
naar die provider, zoals chattekst. Ontvangen instructies krijgen geen executor.

Referenties zoals ‘de eerste’ gelden maximaal vijftien minuten binnen dezelfde
sessie, hetzelfde apparaat en hetzelfde gesprek. Na serverherstart of sessiewissel
vraag je de lijst opnieuw op. Resultaten/antwoorden worden via de bestaande
chatgeschiedenis opgeslagen. Geen willekeurige code of plugins vanuit AI.

Voor vandaag/morgen/overmorgen zonder specifieke kloktijd gebruikt een agenda-
opvraag de hele lokale dag in Europe/Amsterdam. Numerieke relatieve herinneringen
en ‘morgen om 18:00’ worden door de server berekend. Controleer het teruggegeven
tijdstip, vooral bij andere formuleringen of tijdzones. Houd de server aan voor
aflevering van herinneringen. De bestaande spraaktoestemming en spreekknop blijven
gelden; deze uitbreiding schakelt geen permanente opname in.

Complete dagvragen worden rechtstreeks naar de gecontroleerde agendaleestool
geleid. De AI hoeft niet eerst toestemming te bedenken of te zeggen of toegang
mogelijk is. Hoofdletters, een vraagteken en ‘staat’/‘stond’ veranderen de toegang
niet. Bij een complexere onduidelijke persoonlijke vraag volgt verduidelijking.

Ontwikkeltests gebruiken tijdelijke databases, synthetische accounts en gemockte
Google-antwoorden. De Ollama-proef gebruikt het werkelijk geïnstalleerde lokale
model, maar ook synthetische Google-data. Er zijn geen echte berichten namens de
gebruiker verzonden of accountwijzigingen getest. Stop na deze fase-7-uitbreiding.
