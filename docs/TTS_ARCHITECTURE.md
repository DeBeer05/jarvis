# Centrale TTS-architectuur

Tekst/spraak → bestaande STT → Context/AIRouter → IntelligentResponseManager → gedeelde
`providers/speech_format.py` → TTSRouter → bestaande SpeechBridge/private helper → native audio.

`server/natural/tts.py` kiest lokale providers. Automatic/Quality/Offline kiezen
Supertonic indien de gekozen stem is geïnstalleerd; Fast en energiebesparing gebruiken
Piper waar beschikbaar. Manual gebruikt de gekozen provider. Per authenticated
(session, device, utterance_id) wordt de provider en stemconfiguratie vastgezet.

Alleen een fout vóór de eerste geslaagde audio kan eenmaal naar Piper terugvallen.
Na een geleverd segment wordt niet midden in het antwoord van stem gewisseld. Een
vervolgfout stopt de uitvoer. Annulering/authenticatiefouten/busy worden niet als
fallbackreden behandeld. Opnieuw uitvoeren van externe acties is geen TTS-fallback.

De bestaande private helper laadt één TTS-provider tegelijk, hergebruikt sessies en
beperkt ONNX tot vier CPU-threads. Geen runtime-downloads; de servervenv importeert
geen inferencebibliotheken. STT blijft de bestaande Whisper-helper gebruiken. CPU is
de werkelijk geïntegreerde TTS-backend; GPU-TTS wordt niet aangeboden als bewezen optie.

Een optionele centrale vluchtige audiocache is begrensd op 8 MB, met 120 s verval.
Sleutels bevatten sessie, apparaat, geheugenversie en een digest van tekst/stemopties.
Geheugenwijzigingen maken oude cacheverwijzingen ongeldig. Geen microfoonaudio op schijf.
Voice Studio schakelt caching uit voor eerlijke metingen. Clients spelen seriële queues;
onderbreking/cancel behoudt bestaande generatiecontrole en annuleert de inferencehelper.

GET /api/v1/natural/voice-studio: lokale mogelijkheden en configuratieprofielen.
POST /api/v1/natural/voice-studio/preview: maximaal 350 tekens en strikt Voice-model;
geauthenticeerd, rate limited, één begrensd WAV-resultaat, zonder opslag/taakuitvoering.
Bestaande /mobile/speech/synthesize accepteert optionele utterance_id/conversation_id,
controleert rechten en gebruikt dezelfde router. Geen publieke toegang of telefonie.
