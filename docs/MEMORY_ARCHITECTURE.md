# Geheugenarchitectuur — fase 7.5

MemoryManager gebruikt dezelfde SQLite-database en gebruikersautorisatie als de
bestaande backend. Geen externe vectorservice, extra modeldownload of permanent
achtergrondmodel. FTS5 is het zoekfundament; afgeleide informatie krijgt geen
automatische status als bevestigd feit.

## Opslag

`natural_memories` bevat ID, user_id, categorie, inhoud, optionele correctiesleutel,
kind (fact/preference/inference), bron, bronbeurt, created/updated/last_used,
confidence, sensitivity, expires, status en explicit. Wijzigingen gebruiken een
revision voor compare-and-swap. `natural_memory_fts` is de bijbehorende zoekindex.
`natural_forgotten` houdt bron-/afgeleide beurt-ID's bij die geen context meer zijn.

`natural_summaries` bevat per gesprek een extractieve of handmatig bewerkte notitie
met revision/through_sequence. `natural_summary_sources` koppelt geheugenbronnen.
Deze koppelingen volgen de bronbeurten en het werkelijk gebruikte geheugen van
het samengevatte gespreksdeel. Vergeten controleert ook bronbeurten van herinneringen
die pas na de samenvatting zijn opgeslagen. Onverwante samenvattingen blijven staan.
`natural_pending` bewaart begrensde taakreferenties uit de bestaande AutomationEngine;
goedkeuringsnonces, oude previewautoriteit en uitvoeringscredentials ontbreken.
Authenticatie, refreshgeheimen en OAuth blijven in de bestaande beveiligingsopslag.

Schema 5 introduceerde deze tabellen. De bestaande migrator maakt vooraf een
lokale backup van een oudere database; tests controleren migratie en herstart.
De echte gebruikersdatabase wordt pas bij de uiteindelijke gecontroleerde
serverherstart gemigreerd. Tot die stap blijven nieuwe schema's in testdatabases.

## Retrieval en correcties

FTS rangschikt kandidaten vóór de limiet, zodat een oude specifieke herinnering
niet achter honderd recente algemene matches verdwijnt. Nederlandse stopwoorden
en de afspraak/afspraken-variant worden behandeld. Ranking combineert overeenkomst,
FTS-relevantie, betrouwbaarheid, expliciete herkomst en recentheid. Alleen actieve,
niet verlopen en toegestane herinneringen worden geselecteerd; gebruik wordt
geregistreerd. Er zijn nog geen embeddings of algemene semantische zoekmodellen.

Een nieuwe actieve herinnering met dezelfde sleutel maakt de vorige verouderd.
Herkenbare afspraakvoorkeuren krijgen een stabiele sleutel. Dit zijn voorkeuren,
geen harde regels of toestemming om zonder verplichte approval te handelen.
Onduidelijke algemene correcties vragen nog een specifieke herinnering.

## Automatisch onthouden

Standaard uit. Na opt-in herkent een kleine positieve grammatica heldere
persoonlijke plannings-/programmeertaalvoorkeuren. Geen willekeurige gesprekken,
medische termen, politieke voorkeuren, geciteerde externe inhoud of modelgissingen
worden automatisch als feiten verzameld. Bij ‘altijd vragen’ ontstaan voorstellen
die niet in context worden opgehaald. Alleen binnen toegestane zelfstandigheidsregels
worden zulke gewone voorkeuren actief. MemorySave/MemoryUpdate-blokkades blijven gelden.
Geschiedenis uit schakelt automatisch verzamelen uit; expliciet onthouden blijft apart.

Gevoelige herinneringen vereisen altijd expliciete toestemming via geheugenbeheer.
Herkenbare sleutels/wachtwoorden worden ook daar geweigerd. Automatische voorkeuren
hebben explicit=false en een herkenbare bron. Hun automatische herkenning is
bewust beperkt; de GUI en expliciete opdrachten ondersteunen ruimere categorieën.

## Bewaren en verwijderen

Een lichte onderhoudstaak ruimt iedere minuut begrensde aantallen verlopen
herinneringen en oude gesprekstekst op, volgens de gebruikersinstellingen.
Actieve gesprekken/running turns worden overgeslagen. Idempotentiemetadata en
openstaande taakparameters blijven behouden; afgesloten oude taakcontext vervalt.
De taak houdt geen database-lock tijdens netwerkwerk en laadt geen modellen.

Verwijderen ruimt geheugen/FTS en afgeleide context op. Oorspronkelijke gesprekken
zijn afzonderlijke gegevens. SQLite/WAL/backups zijn geen belofte van forensische
overschrijving; een bestaande backup kan oudere gegevens bevatten. API-export bevat
het gekozen geheugen, nooit accountcredentials. Zie MEMORY_USER_GUIDE.md.
