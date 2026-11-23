# Gmail

Volg eerst CALENDAR_INTEGRATION.md voor je eigen Desktop OAuth-client. Selecteer
Gmail lezen (gmail.readonly) en voor concepten/verzenden ook Gmail-concepten en
verzending (gmail.compose). Deze scopes hebben Google-privacy-/verificatie-eisen;
gebruik voor ontwikkeling je eigen toestemming/testaccount, geen publieke uitrol.
Er zijn geen echte mailboxgegevens opgehaald of echte e-mails verzonden in tests.

Web → E-mail: zoek bijvoorbeeld in:inbox of from:synthetic@example.com. Open een
bericht-ID. Standaard wordt alleen metadata gelezen; inhoud vereist een expliciete
keuze. Volledige ontvangen e-mails worden niet in de takenhistorie gekopieerd.
Samenvatten gebruikt de bestaande AI-router, met de tekst als onbetrouwbare data.
Die functie heeft geen tool-/rechtenpad. Stuur alleen inhoud naar je gekozen
provider die je daarmee wilt delen; kies Ollama wanneer je verwerking lokaal wilt.

EmailPriorityClassifier gebruikt gebruikersregels, afzender en tijdgevoelige
tekstsignalen. Reclame/nieuwsbrieven krijgen standaard low_priority. Een urgent-
label is een aanwijzing, geen bewezen urgentie. Configureer important_senders en
urgent_terms via eigenaar PUT /api/v1/automation/rules. EmailCheck controleert
maximaal dertig resultaten per gekozen query, alleen metadata, en dedupliceert
meldingen op message-ID. Nieuwe of terugkerende controles vereisen een expliciet
door jou ingediende taak.

EmailDraft slaat een tekstconcept bij Gmail op en retourneert draft_id,
message_hash en een leesbare preview met ontvanger, onderwerp en tekst. Gebruik
die drie ongewijzigd als input van EmailSend. Controleer ze vóór goedkeuring.
Cc/Bcc en niet-controleerbare HTML-concepten worden niet automatisch verzonden.
De executor haalt het concept opnieuw op en vergelijkt hash én preview. Hij
verstuurt de exacte gecontroleerde bytes via messages.send; wijzigingen aan het
concept kunnen geen andere ontvangers/inhoud laten meesturen. Daarna wordt het
verzonden bericht teruggelezen. Het oorspronkelijke concept blijft staan en kan
door jou handmatig worden opgeruimd. Onzekere verzendingen nooit automatisch
opnieuw uitvoeren: controleer eerst Verzonden bij Gmail.

Follow-ups bewaren alleen thread-ID's en bekende message-ID's. Op het gekozen
moment wordt op nieuwe ontvangen berichten gecontroleerd. Zonder antwoord komt
één gededupliceerde herinnering; daarna controle eenmaal per dag zolang de
workflow actief is. Een antwoord levert reply_review op, nooit automatische
toestemming om een afspraak te verzetten of een externe herinnering te sturen.

Bronnen: [Gmail-scopes](https://developers.google.com/workspace/gmail/api/auth/scopes),
[messages.send](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/send).
