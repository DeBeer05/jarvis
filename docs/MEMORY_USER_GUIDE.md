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

‘Onthou dit’ kan de laatste duidelijke eigen ik-/mijn-uitspraak opslaan. ‘Vergeet
dat’ werkt alleen bij één zojuist getoonde of opgeslagen herinnering waarvan de
versie niet veranderd is. Een lijst met meerdere herinneringen vraagt een keuze.
Ook zulke geheugenlijst-antwoorden krijgen bronkoppelingen, zodat verwijderde
feiten niet via een oud lijstantwoord opnieuw aan AI worden meegegeven.

Automatisch onthouden staat uit. Na inschakelen herkent JARVIS een beperkte set
heldere plannings-/programmeertaalvoorkeuren. Bij ‘altijd vragen’ verschijnen ze
als **proposed**, zonder ze als actieve waarheid te gebruiken. Kies Wijzigen en
status Actief om zo'n voorstel te bevestigen. Binnen toegestane zelfstandigheidsregels
kunnen gewone voorkeuren meteen actief worden; gevoelige feiten worden niet
automatisch verzameld. Je kunt ook altijd zelf een ruimere herinnering toevoegen.

Samenvattingen worden lokaal en extractief gemaakt en zijn zichtbaar/bewerkbaar.
De huidige implementatie kan bij vergeten conservatief alle samenvattingen van
de gebruiker invalideren. Bewaar belangrijke eigen notities daarom ook als
afzonderlijke expliciete herinnering. Algemene semantische retrieval is nog in
uitvoering; nu gebruikt JARVIS FTS5 en metadata/ranking, zonder embeddingdownload.

Met **Gespreksgeschiedenis uit** bevatten nieuwe chatbeurten geen gewone tekst
in SQLite. Een beperkte actieve context blijft tijdelijk in server-RAM en vervalt
bij inactiviteit/herstart. Android wist de offline Room-cache en schrijft geen
nieuwe gesprekstekst naar die cache. Oudere servergesprekken blijven afzonderlijk
bestaan tot verwijderen of de bewaartermijn. Noodzakelijke open taakparameters,
expliciete herinneringen en request-idempotentiemetadata zijn afzonderlijke gegevens.
