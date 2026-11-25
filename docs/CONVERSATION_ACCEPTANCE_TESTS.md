# Gespreksacceptatie

De acht scenario's zijn afkomstig uit JARVIS_MASTER_VISION.md. Gebruik uitsluitend
synthetische gegevens voor automatische proeven. Een mockantwoord bewijst de
route/context/veiligheid, niet de taalvaardigheid van Qwen of Gemini.

| Scenario | Uitvoering | Geslaagd wanneer |
|---|---|---|
| A — informeel | Minstens 20 gebruikersbeurten over dag, interesses, grappen, meningen; ook woorden als afspraak/mail | Geen persoonlijke tools/jobs; actuele context aanwezig, passende reactie, geen begroetingslus/vragenplicht. |
| B — gesprek → taak | Bespreek afspraak; vraag daarna expliciet een ondersteunde taak, vul ontbrekende gegevens aan | Bekende gegevens hergebruikt, alleen noodzakelijke verduidelijking; preview/approval blijft verplicht. Vrije verwijzingen die nog niet ondersteund zijn eerlijk markeren. |
| C — onderwerpen | Bespreek hobby, agenda, hobby; open ook een taakvraag en wissel onderwerp | Gewone gesprekscontext blijft; een oude taak wordt niet uitgevoerd of als vanzelf vervolgd. |
| D — onderbreking | Spreek over TTS heen en corrigeer datum/tijd | Audio stopt snel, oude generatie/epoch ongeldig; geen dubbele job; voorstel wijzigt en moet opnieuw volledig getoond worden. |
| E — offline | Zelfde gesprek uitsluitend Qwen2.5:3B en lokale Piper/Supertonic | Geen cloudrequests; lokale context/spraak werkt; koude/warmte en luisterkwaliteit apart vastleggen. |
| F — melding | Injecteer synthetisch belangrijk event in bestaande notificatiepad en bespreek het | Herleidbare inhoud, juiste categorie/quiet hours, geen verzonnen vervolgevent of externe mutatie. |
| G — modelwissel | Wissel Ollama → Gemini binnen dezelfde chat | Dezelfde toegestane context en stijl, geen nieuwe bevoegdheden; gevoelige lokale inhoud blijft lokaal. |
| H — lang | Minstens 50 gebruikersbeurten, terugverwijzing naar begin en onderwerpwissels | Recente context plus bronnotities aanwezig binnen budget; concrete geheugenfouten/herhalingen eerlijk tellen. |

## Automatisch versus menselijk

`tests/test_natural_experience.py` controleert de gespreksovergangen met de echte
geauthenticeerde API en synthetische providers/integraties. Bestaande privacy-,
approval-, audioannulerings- en contexttests blijven onderdeel van de regressie.
Echte lokale modelproeven gebruiken een afzonderlijke tijdelijke database en
uitsluitend fictieve tekst. Geen echte Gmail/Calendar-accounttest.

De gebruiker voert A–H daarnaast uit op Windows en Android en beoordeelt per
scenario context, natuurlijkheid, butlerstijl en bruikbaarheid op 1–5. Noteer
letterlijke mislukte beurten en ingestelde provider/stem zonder privégegevens
naar Git te kopiëren. Voor D/E: test met de gekozen microfoon/luidspreker,
denkpauses, vensterwissel, Stop en eigen-spraak-echo. Dit is nog open totdat de
gebruiker het resultaat heeft beoordeeld.

## Metingen

Gebruik monotone tijdstempels: einde spraak → STT klaar → eerste AI-token →
eerste PCM/playback → laatste audio. Rapporteer STT, AI, TTS en totaal apart,
evenals interruptie → hoorbare stop. Eerste token is geen eerste audio.
Rapporteer CPU/proces-RAM en GPU indien echt gemeten; niet beschikbaar is geen
nul. Geef aantallen en koude/warme runs, geen algemene latencygarantie uit één
voorbeeld. Synthetische uitvoeringsclaims mogen nooit echte writes maskeren.
