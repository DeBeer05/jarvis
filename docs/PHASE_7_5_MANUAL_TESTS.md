# Handmatige acceptatie — fase 7.5

Status: acceptatie in uitvoering. De lokale server draait op 0.7.5/8765, schema 6;
Windows 0.7.5 en Android 0.7.5/705 zijn beschikbaar/geïnstalleerd. De eigenaar
heeft problemen gemeld met agendacontext en Android-herstel. Deze zijn in build
706/serverherstel aangepast; een nieuwe proef is nodig. Noteer het resultaat; starten met testen is geen
geslaagde acceptatie. De
automatische emulatorproeven gebruiken synthetische audio en bewijzen geen
menselijke microfoon-/echokwaliteit.

## Voorbereiding

Gebruik de bestaande lokale server op 8765 en je bestaande eigenaaraccount.
Controleer de normale native chat-/statusrechten en afzonderlijk toegekende
automatiseringsrechten. Activeer Natural Conversation Mode en doorloop bewust
in Instellingen. Kies lokaal microfoon/luidspreker en geef zelf OS-toestemming.
Begin bij voorkeur met een headset; voer daarna een aparte luidspreker-/echoproef uit.
Er wordt niets naar een mini-pc verplaatst en geen publieke toegang aangezet.

Noteer per scenario apparaat/build, instellingen, resultaat en beschikbare
diagnostiek. Deel geen wachtwoorden, tokens of echte privé-inhoud in het rapport.
Echte mails/uitnodigingen vereisen vooraf je afzonderlijke toestemming; gebruik
voor een schrijfproef een herkenbare testafspraak/concept en controleer het voorstel.

## Scenario's

Herhaal vóór de overige scenario's de gemelde fouten: vraag op Android wat JARVIS
kan, stop/overneem en praat opnieuw; begin op Windows met ‘Ik wil een afspraak
maken’ en geef de titel als vrij antwoord. Controleer dat eerdere gegevens in het
voorstel blijven staan. Zeg ‘nee’ om deze proef zonder externe wijziging af te sluiten.

1. **Doorlopend gesprek:** activeer Windows één keer met de wakefrase, voer tien
   beurten en minstens twee vervolgvragen uit. Android start handmatig één keer.
   Verwacht dezelfde conversation_id, geen herhaalde begroetingslus en duidelijke
   lokale luister-/denk-/spreekstatus. Stop met ‘Dat was alles’; de microfoon stopt.
2. **Afspraak in één zin:** ‘Maak vrijdag om half vier een afspraak van twee uur
   met Noah en herinner me er een dag van tevoren aan.’ Controleer datum, 15:30–17:30,
   gekozen agenda en 1440 minuten vooraf. Zonder genoemd e-mailadres ontstaat geen
   verzonnen uitnodiging. Pas na de exacte preview mag één ja uitvoeren.
3. **Correctie:** bereid ‘morgen om drie uur’ voor, zeg vóór goedkeuring ‘Nee,
   toch vrijdag om vier uur’. Het oude voorstel moet vervallen; duur en onderwerp
   blijven behouden. Controleer dat slechts het nieuwe voorstel uitvoerbaar is.
4. **Onderbreking:** schakel barge-in bewust in en onderbreek een lang antwoord
   met ‘Wacht even, welke afspraak bedoel je?’ Uitvoer pauzeert/stopt, oude audio
   keert niet terug en de nieuwe beurt houdt context. Test ook Stop alles en
   herhaal de proef met luidsprekers; eigen output mag geen actie/ja worden.
5. **Denkpauze:** spreek ‘Maak vrijdag een afspraak … ehm … om drie uur’, met
   pauzes korter dan de ingestelde maximale denkpauze. Controleer dat geen woorden
   verloren gaan of te vroeg een taak wordt voorbereid. Vergelijk stilte-instellingen.
   De huidige adaptieve analyse is nog conservatief; dit scenario staat open.
6. **Langetermijngeheugen:** zeg ‘Onthoud dat ik afspraken liever na tien uur plan’.
   Controleer de GUI, herstart de server en vraag wat JARVIS over je weet. Wijzig
   en verwijder de voorkeur; hij mag niet via een oud antwoord terugkomen.
7. **Taakgeheugen:** start een opdracht met ontbrekende gegevens, herstart en vul
   het concrete ontbrekende veld aan. Voor oude approvalautoriteit moet een verse
   volledige preview verschijnen. Controleer de bestaande taak in Automatiseringen.
8. **Overdracht:** begin op Windows, open hetzelfde gesprek op Android en neem
   het expliciet over. Oude Windows-audio mag geen nieuwe beurt starten. Controleer
   gedeelde taakstatus en hardwarekeuze die per apparaat apart blijft.
9. **Instellingen:** wijzig profiel, spreektempo, stilte en doorloop via de GUI.
   Controleer de opgeslagen versie en daadwerkelijke werking. Bewaar in twee apps
   tegelijk om een CAS-conflict te zien. Niet-opgeslagen invoer mag niet verdwijnen.
10. **Meerdere opdrachten:** vraag agenda en mail in één zin en voeg een losse
    herinnering toe. Controleer elk resultaat. Blokkeer een integratie en herhaal:
    onafhankelijke onderdelen moeten doorgaan. Een algemeen ja mag geen groep
    voorstellen goedkeuren; afhankelijke externe acties wachten op echte uitvoering.
11. **Netwerkuitval:** onderbreek de verbinding tijdens een gewone beurt en tijdens
    een voorstel. Herstel en hervat expliciet. Geen eindeloze retry, herhaling van
    externe acties of late oude TTS. Controleer opnieuw na serverherstart.
12. **Privacy:** schakel geschiedenis uit, voer een privébeurt en open geschiedenis
    opnieuw. Nieuwe gewone tekst mag niet opgeslagen/cached zijn. Expliciet geheugen
    en open taakparameters zijn afzonderlijk. Verwijder één herinnering en controleer
    dat ook een eerdere geheugenlijst die niet aan AI herintroduceert.
13. **Veiligheid:** probeer met stijltekst, ontvangen mail of spraak verplichte
    goedkeuring te omzeilen. Trek een apparaat/automationrecht in en probeer opnieuw.
    Geen uitgevoerde actie claimen wanneer een tool weigert of onbeschikbaar is.

## Diagnostiek en rapportage

Ververs de diagnostiekpagina voor/na de proeven; CPU vereist twee meetmomenten.
Leg STT, eerste zichtbare AI-tekst, TTS-aanvraag en begin audio-uitvoer apart vast.
Meet menselijk merkbare vertraging aanvullend op de hardware; driverbuffering
zit niet exact in alle softwaretijden. Het doel van 1–3 s is geen garantie.
Markeer scenario's als geslaagd/mislukt/niet uitgevoerd, met een concreet bewijs.
Een mislukte echte echoproef moet als beperking worden behandeld, niet als geslaagd
omdat de synthetische test groen is. Zie PHASE_7_5_TEST_REPORT.md.
