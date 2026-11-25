# Taken, herinneringen en workflows gebruiken

Deze functies zijn ook bereikbaar via de normale AI-chat en spraak.
Zie [voorbeelden, rechten en goedkeuring](AI_CHAT_AUTOMATIONS.md).

Op gebruikersverzoek kun je agenda- en mailvoorstellen ook direct in de chat
goedkeuren. Controleer/beluister de volledige preview en zeg één keer **Ja** of **Nee**.
**Goedkeuren** en **Weigeren** typen mag ook. Het apparaat moet expliciet het recht
Goedkeuren hebben. Een ja zonder voorafgaand voorstel voert niets uit;
een gewijzigd of verlopen voorstel wordt eerst opnieuw getoond. Openstaande
voorstellen terugvinden kan met **Toon mijn voorstellen**.

Open de bestaande Windows- of Android-app → Automatiseringen. De webbediening
staat op http://127.0.0.1:8765/automations. Log daar als eigenaar in. Geef onder
Apparaatrechten de UUID van je bestaande Windows-/Android-apparaat op. Kies
afzonderlijk bekijken, taken maken en eventueel goedkeuren. Geef accounts beheren
alleen aan een apparaat dat OAuth-toegang mag beheren. Bestaande apparaten krijgen
deze rechten niet stilzwijgend. Hun sessiestatus wordt opnieuw opgehaald.

De eigenaarinterface toont nu een keuzelijst van gekoppelde apparaten op naam en
type, inclusief Windows en Android. Je hoeft geen UUID over te typen. Kies eerst
het juiste apparaat, controleer de huidige rechten en bevestig zelf de wijziging.
In Windows 0.7.1 opent **Apparaatrechten instellen als eigenaar** het eigen apparaat
als voorstel; alleen openen wijzigt niets. Daarna **Rechten vernieuwen** in de app.

Herinneringen: vul tekst en tijd in, kies eenmalig/dagelijks/wekelijks en stel in.
De server accepteert alleen tijden met offset plus een IANA-tijdzone. Herhaling
behoudt de lokale kloktijd. Een niet-bestaande zomertijd wordt overgeslagen; bij
de dubbele herfsttijd wordt de eerste occurrence eenmaal gebruikt. Gemiste
herhalingen worden niet allemaal tegelijk ingehaald. Windows gebruikt voor de
herhalingszone voorlopig Europe/Amsterdam; web/Android gebruiken de ingestelde
systeemtijdzone. Sluit de server niet af wanneer je aflevering op tijd verwacht.

Automatiseringen kunnen in de lijst worden gepauzeerd, hervat en geannuleerd.
De verwijder-API bewaart een minimale idempotency-tombstone, zodat een replay
niet opnieuw verstuurt. Een al verstuurde externe wijziging kan niet door
annuleren ongedaan worden gemaakt. Een onzekere externe actie blijft zichtbaar
voor controle en kan niet blind worden hervat/verwijderd.

Geavanceerde taken gebruiken een UUID idempotency_key en gevalideerde toolinput:

```json
{"tool":"CalendarSummary","input":{"calendar_id":"primary","timezone":"Europe/Amsterdam","day_offset":0},"idempotency_key":"11111111-1111-4111-8111-111111111111","due":"2026-11-25T08:00:00+01:00","repeat":"daily","timezone":"Europe/Amsterdam"}
```

Dien dit uitsluitend zelf in via POST /api/v1/automation/jobs of de actiebediening.
EmailCheck met input {"query":"in:inbox newer_than:1d"} is een andere expliciet
te plannen controle. Er zijn geen vooraf aangemaakte controles op je accounts.

WorkflowCreate heeft title en steps, maximaal tien. Elke stap heeft precies tool
en input. Stappen zijn concrete gevalideerde acties; er is geen expressietaal,
code-evaluatie of impliciete modeluitvoering. Gebruik gecontroleerde event-/draft-
en thread-ID's uit eerdere zoek-/conceptacties. Voorbeeld:

```json
{"title":"Controleer en herinner","steps":[{"tool":"ReminderList","input":{}},{"tool":"NotificationSend","input":{"category":"important","text":"Controle afgerond"}}]}
```

Een externe stap wacht altijd op eigen approval. WaitForReply kan een bekende
Gmail-thread met due volgen. Een antwoord wordt ter beoordeling aangeboden;
de daaropvolgende CalendarUpdate vereist nog steeds aparte toestemming. Een
geweigerde, mislukte of onzekere stap blokkeert het vervolg. Pauzeren van de
ouder verhindert de uitvoering van verdere kinderen.

Goedkeuren: bekijk de exacte ontvangers, inhoud, tijden en gevolgen. Kies
Goedkeuren of Weigeren en bevestig. De UI vraagt een apparaatgebonden challenge
op, vijf minuten geldig, uitsluitend eenmaal bruikbaar. Een gewijzigde actie
kan die toestemming niet hergebruiken. Uitgestelde externe acties waarvan de
toestemming verlopen is, vragen opnieuw approval.

Meldingen: urgent/appointments/important/news; centrale categorieën, stilteuren
en frequentie in web → Meldingen. Android vraagt daarnaast OS-meldingsrechten.
Stilte schuift aflevering door; een frequentielimiet voorkomt een onmiddellijke
storm. Windows/Android bewaren de laatst geziene positie. Inhoud blijft in de
geauthenticeerde inbox. Android levert zonder FCM alleen terwijl de app actief is.
