# Fase 7.5: prestaties (in uitvoering)

## Gemeten op 24 november 2026

Ontwikkeldesktop: Ryzen 7 5700X, RTX 4060, 32 GB RAM. De onderstaande proef
gebruikte daadwerkelijk de bestaande Piper Ronnie en Whisper Small in de
geïsoleerde voice-runtime, via de bestaande SpeechBridge. Geen microfoon,
Google-account, modeldownload of netwerkprovider aangeroepen. Twee TTS- en twee
STT-aanvragen volgden in hetzelfde private subprocess. Audio bleef in RAM.

| Aanvraag | Totale wandtijd | Inference | Worker-RAM na aanvraag |
|---|---:|---:|---:|
| Piper eerste aanvraag | 1,004 s | 0,701 s | 193,7 MiB |
| Piper tweede aanvraag | 0,098 s | 0,095 s | 197,1 MiB |
| Whisper eerste aanvraag | 3,321 s | 3,093 s | 518,8 MiB |
| Whisper tweede aanvraag | 1,975 s | 1,969 s | 517,6 MiB |

Whisper gebruikte CPU, niet CUDA. Piek-RAM van de gezamenlijke helper was
877,6 MiB. Runtime-CPU-tijd was cumulatief 1,91 / 2,75 / 14,00 / 21,64 s;
dit zijn meerdere CPU-threads en geen CPU-gebruikspercentages. ASR gaf in beide
proeven tekst terug. Dit is geen beoordeling van echte microfoonherkenning.

De proef gebruikte één korte synthetische Nederlandse zin. Resultaten zijn
momentopnamen, geen percentielen, duurtest of garantie. Ze bevatten geen VAD-
wachtduur, AI-generatie, netwerktransport of luidsprekerbuffer. Totale
responstijd, AI time-to-first-token en echte onderbrekingen worden na het
aansluiten van de nieuwe gespreksmodus afzonderlijk gemeten.

## Implementatie

`providers/voice_pipe.py` bevat de gedeelde stdlib-procesbewaking voor server en
Windows-client. Alleen de bestaande private inferencehelper laadt modellen;
de serveromgeving importeert geen Whisper, Piper, Qt of sounddevice.
Annulering stopt alleen het eigen subprocess en verwerpt oude resultaten.
Een timer geeft de servermodellen vrij na de ingestelde inactiviteit.
Idle stoppen van Windows-output vernietigt niet meer telkens de geladen modellen.

Private pipe-I/O draait op workerthreads, onafhankelijk van het gebruikte
Windows-eventlooptype. Python beschrijft de beperkingen van Windows
SelectorEventLoop voor subprocessen in de
[officiële platformdocumentatie](https://docs.python.org/3.12/library/asyncio-platforms.html#subprocess-support-on-windows).

## Doel en toekomstige mini-pc

Een eerste gesproken reactie binnen ongeveer 1–3 s blijft een prestatiedoel.
De gemeten CPU-STT kan dit budget grotendeels gebruiken; het doel is dus nog
niet bewezen. VAD, inference, AI en TTS moeten apart worden gemeten.

De audiohelper lijkt op basis van deze proef qua RAM geschikt voor een systeem
met 8 GB, bij cloud-AI en begrensde context. Dit onderbouwt geen totale
systeemgarantie: Windows, clients, andere processen en een lokaal taalmodel
zijn niet meegemeten. Geen mini-pc-test of migratie uitgevoerd. Het lichte
geheugenprofiel kan wisselend STT/TTS-modellen vrijgeven ten koste van latency.
