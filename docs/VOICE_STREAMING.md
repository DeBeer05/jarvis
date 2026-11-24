# Gespreksaudio en streaming — fase 7.5 in uitvoering

Er blijft één FastAPI-backend op poort 8765 en één bestaande inferencecodebasis
in `desktop-client/voice_runtime/`. De serveromgeving laadt geen Qt, sounddevice,
Whisper of Piper. Alleen de private helper laadt de bestaande modellen.

## Huidige datastroom

1. Windows/Android openen alleen na lokale toestemming en bewuste activatie hun
   gekozen microfoon. Android stopt bij `onStop`; er is geen achtergrondservice.
2. De huidige STT-adapter verzamelt een begrensde uitspraak. PCM16 mono 16 kHz
   wordt als WAV via de geauthenticeerde bestaande mobiele speechroute verwerkt.
3. De transcripttekst gaat naar dezelfde chat/SSE-route, met conversation_id,
   request_id en de actuele audio-epoch. De centrale lease voorkomt oude invoer
   na apparaatoverdracht. Geen directe uitvoering uit ruwe modeltekst.
4. AI-delta's worden per complete zin aan de begrensde TTS-buffer toegevoegd;
   de client hoeft niet op het gehele antwoord te wachten. Backendtoolresultaten
   worden eerst gevalideerd/rendered; voorlopige tekst bevestigt geen externe actie.
5. TTS gebruikt dezelfde private serverhelper. Native clients spelen het WAV-antwoord
   af op hun gekozen uitvoer en geven daarna de volgende spreekbeurt vrij.

Windows Natural Conversation Mode gebruikt `ServerInferenceWorker`, met een
annuleerbare gepoolde AsyncClient buiten de Qt-thread. Hierdoor laden Windows en
Android niet ieder nog een eigen modelkopie op dezelfde ontwikkelhost. De bestaande
lokale Windows-inferenceadapter blijft beschikbaar wanneer de nieuwe modus uit staat.
Enginewisseling wordt tot een veilige beurtgrens uitgesteld.

## Grenzen, annulering en geheugen

- STT: maximaal 60 s / 2.000.000 bytes; mono PCM16 16 kHz, volledige WAV-validatie.
- TTS: maximaal 700 tekens per aanvraag; zinsbuffer begrensd, geen onbegrensde wachtrij.
- Eén inference-slot, geen parallel geladen kopieën per aanvraag. Bij bezet wordt
  een begrensde fout gemeld, geen eindeloze retry.
- `OwnedVoicePipe` bewaakt uitsluitend het eigen subprocess, deadline en protocol.
  Modellen blijven warm tussen aanvragen; idle-unload is instelbaar.
- Disconnect en ingetrokken authenticatie stoppen de bijbehorende inference.
  Clientannulering sluit alleen de spraakverbinding, niet de chatpool.
- Oude generatieresultaten/audiodelta's worden verworpen. Een voice-interruptie
  verwijdert geen duurzame taak of reeds uitgevoerde externe actie.
- Geen ruwe audio op schijf, in SQLite of logs. Protocolbuffers worden na verwerking
  vrijgegeven; de optionele Windows-TTS-cache is begrensd en wordt bij geheugenwijziging
  gewist. Microfoondata is geen cache.

De security-headerlaag gebruikt nu pure ASGI, zodat receive/disconnect behouden
blijft. De oorspronkelijke headers/CSRF/hostcontroles zijn behouden. De keuze sluit
aan bij de [Starlette-middlewaredocumentatie](https://www.starlette.io/middleware/).
Een echte TCP-regressie controleert dat annulering vóór responseheaders ook de
serveraanvraag stopt en dat daarna een nieuwe aanvraag slaagt.

## Luisteren en Android-platformaudio

De stilte- en VAD-drempels komen uit de gedeelde instellingen. De huidige
adaptieve stand is conservatief en gebruikt de ingestelde maximale denkpauze;
incrementele STT/contextuele end-of-turn-analyse wordt nog uitgebreid.
Wakefraseherkenning op Windows is transcriptiegebonden, geen los getraind wake-model.

Android koppelt beschikbare `AcousticEchoCanceler` en `NoiseSuppressor` aan de
AudioRecord-sessie met VOICE_COMMUNICATION. Een actieve voorgrondsessie beheert
de communicatiemode en herstelt haar bij stoppen. Audiofocusverlies stopt ook
de microfoon/doorloop. Beschikbaar is niet hetzelfde als op echte hardware bewezen.
Zie de [officiële AEC-documentatie](https://developer.android.com/reference/android/media/audiofx/AcousticEchoCanceler).

## Bewijs en open werk

De Android ViewModel-lus heeft tien opeenvolgende beurten met één handmatige
activatie in één centraal gesprek uitgevoerd: echte server-STT en TTS, synthetische
vooraf gemaakte WAV-invoer en een test-outputadapter. Dit bewijst de softwareketen,
niet echte microfoon-, echokwaliteit of menselijke beurtwisseling.

Spraakgestuurde barge-in, aanvullende end-of-turn-analyse en de optionele
WebSocket-adapter zijn bij deze documentversie nog in uitvoering. Er is geen
WebRTC- of telefonie-infrastructuur toegevoegd. Latency-/RAM-metingen staan in
`CONVERSATION_PERFORMANCE.md`; het doel van 1–3 s is geen garantie.
