# Persoonlijk geheugen

Geheugenbeheer staat op Windows onder **Instellingen → Gesprekken en geheugen →
Geheugen en samenvattingen** en op Android onder **Instellingen → Gesprekken en
geheugen → Geheugen**. Zoek op inhoud of filter op categorie.

Je kunt herinneringen toevoegen, wijzigen, verwijderen en exporteren. Android
kan een herinnering ook als verouderd markeren. Gevoelige inhoud vereist bij
opslaan expliciete toestemming; het betreffende vakje markeert haar als gevoelig.
Wachtwoorden en sleutels horen nooit in het geheugen.

Expliciete chat-/spraakopdrachten gebruiken dezelfde centrale opslag:

- ‘Onthoud dat ik liever afspraken na tien uur plan.’
- ‘Wat weet je nog over mij?’
- ‘Vergeet afspraken na tien uur.’

Bij meerdere overeenkomende herinneringen wordt niet willekeurig verwijderd.
‘Vergeet dat’ vraagt om een concrete inhoud of selectie in het geheugenmenu.
Het volledige geheugen wissen vraagt in het menu een afzonderlijke bevestiging.

Gewone herinneringen worden standaard niet aan cloud-AI toegevoegd. Dit kan
uitsluitend met de expliciete privacyvoorkeur voor cloudgeheugen. Gevoelige
herinneringen worden alleen in een lokale-only route opgehaald, met de afzonderlijke
geheugenvoorkeur daarvoor. Offline-modus laat geen cloudfallback toe.

Verwijderen of corrigeren invalideert betrokken bronbeurten, beurten die de
herinnering als AI-context gebruikten, FTS-resultaten en samenvattingen. Verwijderde
context wordt niet uit een oude samenvatting opnieuw opgehaald. Lopende gewone
generaties stoppen bij een geheugenwijziging.

De oorspronkelijke gespreksgeschiedenis wordt hiermee niet automatisch gewist.
Die beheer je afzonderlijk bij **Gesprekken**. Ook openstaande automatiseringstaken
kunnen noodzakelijke taakparameters bevatten; geheugen wissen annuleert geen
externe acties en verandert geen uitgevoerde taken. Het menu vermeldt dit onderscheid.

Samenvattingen worden lokaal en extractief gemaakt en zijn zichtbaar/bewerkbaar.
Automatische onthoudregels, aanvullende privacyretentie en semantische retrieval
zijn tijdens deze documentversie nog in uitvoering; de actuele retrieval gebruikt
SQLite FTS5 en metadata/ranking, zonder vectordatabase of embeddingdownload.
