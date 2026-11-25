# Echte TTS-benchmark — 24 november 2026

Ryzen 7 5700X, 32 GB RAM, Windows. scripts/benchmark_tts.py, zes gelijke Nederlandse
synthetische zinnen, snelheid 0,95, Supertonic acht stappen, CPU vier ONNX-threads.
42 WAV-bestanden uitsluitend in .local/tts-benchmark; geen microfoon of privétekst.

| Provider/stem | Eerste sample (s) | Mediaan overige vijf (s) | Helper piek MiB |
|---|---:|---:|---:|
| Supertonic M1 | 2,515 | 1,508 | 505,0 |
| Supertonic M2 | 1,670 | 1,475 | 517,6 |
| Supertonic M3 | 1,415 | 1,308 | 517,6 |
| Supertonic M4 | 1,649 | 1,467 | 518,1 |
| Supertonic M5 | 1,625 | 1,485 | 518,6 |
| Piper Ronnie | 1,065 | 0,189 | 251,8 |
| Piper MLS | 0,821 | 0,231 | 340,3 |

M1 en Ronnie omvatten opstart van hun helper/provider; latere stemmen binnen dezelfde
provider hergebruiken de geladen ONNX-sessies en zijn geen onafhankelijke cold starts.
Gecombineerde warme mediaan: Supertonic 1,467 s, Piper 0,213 s. Dit is tijd tot een
volledige zin-WAV beschikbaar is, geen sample-streaming of volledige STT/AI/audio-latency.
RTF, per-sample generatie-/CPU-tijd en RAM staan in het lokale JSON-rapport.

TTS gebruikt CPU; geen TTS-VRAM-allocatie of GPU-versnelling gemeten. Een losse
nvidia-smi-systeemsnapshot gaf 6% GPU en 6038/8188 MiB; dat is geen toerekening aan TTS
(andere processen/modellen kunnen VRAM gebruiken). Geen GPU-TTS-benchmark geclaimd.

Supertonic is de lokale kwaliteitskandidaat, Piper de snelle fallback. Subjectieve
Nederlandse uitspraak, volwassenheid/diepte en dagelijks gebruik vereisen luisterproef.
De toekomstige 8-GB-mini-pc is niet getest. Circa 0,52 GB TTS-helper is gunstig, maar
Windows, Whisper en Ollama tellen apart mee; kies energiebesparing/klein model en meet
op die machine voordat geschiktheid definitief wordt verklaard. Geen migratie uitgevoerd.


Een opgewarmde echte Supertonic-generatie met langere synthetische tekst is via de
bestaande private pipe geannuleerd. De wachtende aanroep merkte dat na **0,051 s**;
een nieuwe Piper-aanroep werkte daarna. Er werd geen audio afgespeeld en geen fysieke
barge-in/echo beoordeeld. Rapport: .local/tts-benchmark/cancellation.json.
Een verpakte Supertonic M1-helper produceerde ook geldig PCM-WAV (1,705 s generatie).
