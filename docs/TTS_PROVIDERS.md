# TTS-providers — gecontroleerd 24 november 2026

| Provider | Nederlandse stemmen | Status | Gebruik |
|---|---|---|---|
| Supertonic 3 | vaste mannenstijlen M1–M5, taal nl | lokaal geïntegreerd en gemeten | aanbevolen kwaliteitskandidaat; luisterproef nodig |
| Piper | nl_NL Ronnie, MLS met sprekernummer | lokaal geïntegreerd en gemeten | snelle offline fallback |
| Edge TTS | kandidaat nl-NL-MaartenNeural | onderzocht, niet geactiveerd | onofficieel online; geen productiedienstgarantie |
| XTTS v2 | Nederlandse taal ondersteund | onderzocht, niet geïnstalleerd | optioneel experiment; geen verplichte zware dependency |

Supertonic ondersteunt lokale ONNX-inference en 31 talen, waaronder Nederlands.
Broncode is MIT; modelgewichten OpenRAIL-M met gebruiksbeperkingen. De officiële
repository is gearchiveerd. Gebruik de vastgezette bestaande release, geen veronderstelde
onderhoudsgarantie: [officiële archive](https://github.com/supertone-oss-archive/supertonic),
[model](https://huggingface.co/supertone-oss-archive/supertonic-3).

Gebruiker gaf expliciet toestemming voor circa 400 MB. Installatie na eigen
omvang-/licentiebeoordeling: `.venv/Scripts/python.exe scripts/install_supertonic.py
--consent-download`. Download alleen in LOCALAPPDATA/JARVIS/Desktop/models/supertonic-3.
Modelrevision aafc6e32416a594460b32413efc49d7fe4ce6d46; vier ONNX-SHA256's vastgelegd in
het script. De bekeken MIT-inferencehelper is vendored op commit
1e9799e964ea4c0dad7cde993b65c3c813a7b373, met copyright/licentie erbij. Modellen niet in Git.
Geen account, betaalde Voice Builder of stemreferentie nodig. Geen cloning uitgevoerd.

Piper-runtime GPL-3.0; modellen hebben eigen datasetvoorwaarden. Bestaande Ronnie-
en MLS-downloads zijn eerder afzonderlijk goedgekeurd. Zie
[Ronnie-modelkaart](https://huggingface.co/rhasspy/piper-voices/blob/main/nl/nl_NL/ronnie/medium/MODEL_CARD)
en docs/VOICE_MODELS.md. MLS-sprekers zijn niet allemaal als volwassen mannen bevestigd.

[Edge-TTS](https://github.com/rany2/edge-tts) gebruikt een onofficiële online-integratie;
code grotendeels LGPLv3. [Microsoft](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=text-to-speech)
noemt MaartenNeural als Nederlandse mannenstem, maar dat bewijst geen toegang via Edge.
Het gevraagde -8%/-8 Hz-profiel is daarom alleen een onderzoeksvoorstel, niet als werkend
geclaimd. Er is geen tekst naar Edge gestuurd, geen limietomzeiling of betaalde dienst.

[XTTS-documentatie](https://docs.coqui.ai/en/stable/models/xtts.html) en
[officieel model](https://huggingface.co/coqui/XTTS-v2) ondersteunen Nederlands; de
modellicentie is CPML en verschilt van de broncodelicentie. Zwaardere runtime en
referentie-/licentievragen voegen hier geen noodzaak toe naast werkende lokale ONNX.
Niet gedownload, geen benchmarkingclaim. Geen ElevenLabs of onverwachte API-kosten.
