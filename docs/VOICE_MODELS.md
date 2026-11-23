# Spraakmodellen, afhankelijkheden en licenties

Geen automatische runtime-downloads. `download-voice-models.py` vereist expliciet
`--accept-downloads`, gebruikt vastgepinde revisies, controleert bestandsgrootte
en Hugging Face Git-blob/LFS-hash en schrijft een SHA256-manifest naast elk model.
De eigenaar heeft beide oorspronkelijke modellen en aanvullend Ronnie goedgekeurd.
Silero-VAD (~1,2 MB) komt met faster-whisper; Piper/ONNX-wheels bevatten ook
aanvullende taal-/testdata. Die kleine pakketmodellen worden meegebundeld,
de hierboven besproken grote Whisper-/Piper-stemgewichten blijven extern.

| Model | Gewicht | Lokale map onder models | Status |
|---|---:|---|---|
| faster-whisper Small (meertalig) | 483.546.902 bytes + ~2,7 MB config/tokenizer | whisper-small | geïnstalleerd, Nederlands getest |
| Piper nl_NL-mls-medium, 52 profielen | 76.584.246 bytes + config | piper | geïnstalleerd; korte synthetische zinnen onbetrouwbaar in rondreisproef |
| Piper nl_NL-ronnie-medium, één stem | 63.221.984 bytes + config | piper-ronnie | geïnstalleerd, aanbevolen; betere rondreisproef |
| Whisper Base/Tiny | niet gedownload | whisper-base / whisper-tiny | optioneel, eigen conversie/installatie nodig |
| XTTS v2 | niet gedownload, model orde 2 GB plus grote Torch-runtime | geen | niet beschikbaar in deze build |
| Nederlands getraind openWakeWord-model | geen gevalideerd model gekozen | geen | niet beschikbaar; experimentele Whisper-frasefilter aanwezig |

Revisies: Small `536b0662742c02347bc0e980a01041f333bce120`;
Piper-modellen `e9c8a39444359388adaa94255becb37a5a2b8e51`.
Small model.bin SHA256 `3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671`;
MLS `88312e0fbf505b87caf2373d94c1384892e86b1bf2ee482cf65dc8ba179cc7d3`;
Ronnie `c6b69203247c9ff9aaadf59ec51147fffb16bb2c2892eb92d5b75d2f9d096622`.

Whisper/faster-whisper Small: MIT; CTranslate2: MIT. Zie de
[modelkaart](https://huggingface.co/Systran/faster-whisper-small/blob/main/README.md)
en [officiële faster-whisper-bron](https://github.com/SYSTRAN/faster-whisper).
Voor CUDA noemt de upstream cuBLAS12/cuDNN9; anders CPU int8. Op deze desktop
is RTX 4060 aanwezig, maar de noodzakelijke CUDA-runtime niet volledig aanwezig.
De app verandert systeem-PATH of GPU-installaties niet.

[Piper 1.8.0](https://github.com/OHF-Voice/piper1-gpl) is GPL-3.0-or-later en
gebruikt eSpeak NG; licentieteksten worden met de afzonderlijke helper verzameld.
Ronnie vereist Piper >=1.5; de
[modelkaart](https://huggingface.co/rhasspy/piper-voices/blob/main/nl/nl_NL/ronnie/medium/MODEL_CARD)
noemt een CC0-dataset en een CC0 Vlaams basismodel. De
[MLS-modelkaart](https://huggingface.co/rhasspy/piper-voices/blob/main/nl/nl_NL/mls/medium/MODEL_CARD)
noemt OpenSLR94/CC BY 4.0. De modelrepository vermeldt MIT; bewaar daarnaast de
datasetvermelding en modelkaarten. Geen imitatie van een gekozen acteur of
persoon, geen stemkloning of persoonlijke referentieaudio.

De originele Mark-LVII-bron en auteursvermelding blijven CC BY-NC 4.0.
De afzonderlijke, nieuw geschreven inferencehelper wordt als GPL-3.0-or-later
beschikbaar gesteld; dit wijzigt de upstreamlicentie niet. Een lokale build is
voor privégebruik. Er is geen publieke release/distributie uitgevoerd. Bij
verspreiding moeten bijbehorende broncode en alle componentlicenties worden
meegeleverd/nageleefd; de helper is een apart proces met vervangbare runtime.
Zie ook WINDOWS_CLIENT_THIRD_PARTY.md. Geen algemene productlicentieclaim.

XTTS v2 blijft bewust optioneel: aparte Coqui/Torch-installatie, hardwaretest,
modellen, licentiecontrole en toegestane referentiestem ontbreken. De
[CPML-modellicentie](https://huggingface.co/coqui/XTTS-v2/blob/main/LICENSE.txt)
beperkt model en uitvoer tot niet-commercieel gebruik. Er is geen ongeteste knop,
automatische download of stille overstap naar cloud-TTS. Piper is de beschikbare
fallback/standaard vóór het hele antwoord. Hybride TTS is zonder gemeten winst
niet geactiveerd.

[openWakeWord](https://github.com/dscripka/openWakeWord) levert standaard Engelse
modellen; dat bewijst geen betrouwbare Nederlandse Hé JARVIS-detectie.
Voor een dedicated variant: verzamel toegestane Nederlandse positieve varianten,
ruis/negatieven en echte kameropnamen, train volgens
[custom_model.yml](https://github.com/dscripka/openWakeWord/blob/main/examples/custom_model.yml),
houd validatiesprekers gescheiden en meet false accepts per uur en false rejects
op de eigen microfoon. Controleer elke gebruikte model-/datasetlicentie en
referentietoestemming. Pas na die metingen kan een getraind model worden aanbevolen.
