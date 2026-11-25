# Intelligent Response Engine

## Plan en bestaande architectuur

Hergebruik: FastAPI 8765, ChatService/AIRouter, ContextManager, NaturalStore/SettingsManager,
AutomationChat/ApprovalManager, SpeechBridge/OwnedVoicePipe, bestaande audio-uitvoer en
onderbrekingsgeneraties. Geen tweede backend, spraakproces of database. Werkvolgorde:
broninspectie → antwoordbeleid en gesproken protocol → lokale TTS-router → native
Voice Studio → deterministische regressies → echte modelbenchmark → builds/luisterproef.

`server/natural/responses.py` bouwt het antwoordbeleid centraal. Zes modi (auto,
ultrakort, kort, gebalanceerd, uitgebreid, volledig) hebben afzonderlijke gesproken en
 geschreven voorkeuren. Expliciet volledig voorlezen/meer uitleg gaat voor de standaard.
De oorspronkelijke modelaanroep krijgt passende instructies; er komt niet standaard
nog een AI-aanroep achteraan. Toolantwoorden krijgen een afzonderlijke lokale gesproken
samenvatting; het geschreven resultaat en geverifieerde bron-ID's blijven beschikbaar.

De voice-SSE-meta meldt `speech_protocol=1`. `delta` blijft geschreven tekst; `speech`
bevat uitsluitend de uit te spreken tekst. Nieuwe Windows-/Android-clients scheiden
beide. Oudere servers zonder dit protocol behouden de eerdere clientroute. Algemene
modelantwoorden leveren zinsgewijs spraak; toolantwoorden wachten op bevestigd resultaat.

Een WAITING_FOR_APPROVAL/WAITING_FOR_INFORMATION-antwoord en samengestelde opdracht
worden niet verkort. Exacte goedkeuringsbinding en backendmachtigingen blijven leidend.
Geen nieuwe agenda/mailactie wordt door samenvatten of stijl toegestaan.

## Grenzen

Samenvattingen van toolgegevens zijn bewust conservatief/extractief, geen getrainde
belangrijkheidsclassifier. Een onderwerpenlijst bewijst niet dat mail ongelezen, urgent
of reactievereisend is. Aantallen betreffen de daadwerkelijk opgehaalde selectie.
Bestaande begrenzing van mailinhoud (5.000 tekens, met inkortmelding), zoekresultaten en
context blijft gelden, ook bij Volledig. Nieuws/berichten gebruiken alleen reeds
beschikbare gegevens/integraties; deze uitbreiding voegt geen nieuws- of WhatsAppdienst toe.
