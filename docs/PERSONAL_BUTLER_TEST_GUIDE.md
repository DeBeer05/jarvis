# Persoonlijke butler — praktische acceptatie

Test op een ontwikkelinstallatie. Externe acties alleen met een eigen expliciet
testvoorstel en actuele rechten; technische transportmocks zijn geen accounttest.

## Fase 1: persoonlijkheid en geheugen

1. Kies Classic Butler, meneer en Ieder antwoord. Stel humor/formaliteit naar wens
   in; spreek over een drukke of vermoeiende dag. Beoordeel tact en lengte apart
   van technische tests. Een stemming is een vermoeden, geen opgeslagen diagnose.
2. Sla via ‘Onthoud …’ een onschuldig projectfeit of voorkeur op. Controleer het
   onder Geheugen; wijzig het en controleer dat de oude versie niet terugkomt.
3. Schakel onder Geheugen ‘Eerdere gesprekken gericht terugvinden’ in. Bespreek
   een fictief project, begin een nieuw gesprek en vraag naar dat project. Dit
   gebruikt alleen relevante opgeslagen gebruikersuitspraken, geen modelwaarheid.
4. Herstart backend/client en herhaal stap 3. Probeer ook een tweede gekoppeld
   apparaat. Zet synchronisatie uit: alleen bronnen met bekende eigen
   apparaatbinding mogen dan worden teruggevonden.
5. Verwijder het expliciete projectgeheugen en vraag opnieuw, ook in een gesprek
   dat dit eerder als context gebruikte. Bronvergeten blokkeert afgeleide context.
6. Zet geschiedenis uit en noem een nieuw fictief feit. Het mag later niet via
   deze zoekfunctie terugkomen. Verwijder een oud gesprek: de FTS-index volgt mee.
7. Test met cloud-AI terwijl cloudgeheugen uit staat: oude uitspraken gaan niet
   mee. Gevoelig geheugen blijft bij cloud altijd uitgesloten. Geen echte
   wachtwoorden, medische gegevens of sleutels gebruiken voor acceptatietests.

Technisch: migratie v9 gebruikt dezelfde SQLite-database met de bestaande
automatische pre-migratiebackup. FTS5 indexeert uitsluitend bestaande
gebruikersuitspraken; er is geen vectorservice, extra model of periodieke
samenvattingscall. Maximaal drie fragmenten van 480 tekens, binnen het bestaande
contextbudget. De functie is standaard uit en verandert geen cloudtoestemming.

Volgende fasen worden hier pas toegevoegd nadat ze zijn geïmplementeerd.
