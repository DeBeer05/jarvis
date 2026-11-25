# Spraaklatency met 8 GB als randvoorwaarde

25 november 2026. Vervolg op de mastervisie, binnen fase 7.5. Doel: minder
onnodig wachten, met behoud van Qwen2.5:3B, Whisper Small en de gekozen stem.
Geen mini-pc ingericht, geen model/download/dependency toegevoegd, geen cloudtest.

## Uitgevoerde verbeteringen

- De eerste voldoende lange spreekclausule mag starten bij een natuurlijke
  komma, puntkomma of dubbele punt tussen 60 en 240 tekens. Korte begroetingen
  en decimale komma's blijven bijeen. Daarna blijven zinsgrenzen leidend.
  Dit begrenst audiofragmenten, niet de lengte of inhoud van het antwoord.
- Beide clients behandelen `speech`-events als gereed spraakmateriaal; ze
  wachten daarbij niet opnieuw op een volledige zin. Gewone tokenstreams
  houden hun bestaande zinsbuffer. Ook oudere grotere speech-events worden
  woordgewijs verdeeld in stukken van maximaal 600 tekens voor de bestaande
  700-teken-TTS-route. Geschreven antwoorden en exacte previews blijven volledig.
- Windows en Android bereiden maximaal één WAV vooruit terwijl de vorige
  afspeelt. Geen extra model of helper; maximaal één blok speelt en één is
  voorbereid/in bereiding. Windows gebruikt een begrensde queue plus semaphore;
  Android een rendezvous-channel. Bij barge-in blijft de bestaande seriële
  route gelden om geen extra concurrentie met STT te veroorzaken. Stop/epoch-
  wissel annuleert de producer en voorkomt afspelen van oude audio.
- CUDA-capaciteit en ontbrekende libraries worden per helperlifetime eenmaal
  onderzocht. Een mislukte CUDA-inference wordt niet bij iedere uitspraak
  opnieuw geprobeerd. Alleen veilige redencodes komen terug; geen native paden.
  CPU-int8 en één inferenceworker blijven behouden. Na installatie-/driver-
  wijzigingen moet de helper opnieuw worden gestart om opnieuw te onderzoeken.
- Bij een STT-modelwissel worden oude gewichten vrijgegeven vóór de nieuwe
  allocatie. Het lichte profiel ontlaadt de andere engine maar behoudt de kleine
  device-/fallbackcache. Geen permanente voorraad van meerdere STT/TTS-modellen.

Goedkeuringstekst wordt pas uitgesproken nadat het volledige serverresultaat
beschikbaar is. Geen vroeger uitgesproken gedeeltelijk wijzigingsvoorstel,
nieuwe toestemming of versoepelde intent-/approvalcontrole.

## Onderzoek en verworpen versnellingen

Op de ontwikkeldesktop ziet CTranslate2 één CUDA-device. `cublas64_12.dll`
ontbreekt; `cudnn64_9.dll` is aanwezig. Dat verklaart de CPU-terugval. Er zijn
geen GPU-libraries geïnstalleerd: een GPU is geen voorwaarde voor de toekomstige
8-GB-host.

Whisper Small is op dezelfde acht synthetische Nederlandse WAV's vergeleken,
twee rondes met afwisselende volgorde, CPU-int8/vier threads:

| Decoderproef | Mediaan inferencetijd | Genormaliseerde woordfouten |
|---|---|---|
| Beam 3 | 1,402 s | 6 / 120 referentiewoorden |
| Beam 1 | 1,359 s | 8 / 120 referentiewoorden |
| Aparte beam-3-timestampbaseline | 1,404 s | 8 / 120 |
| Beam 3 zonder timestamps | 1,388 s | 8 / 120 |

De greedy-winst was circa 43 ms en veranderde onder andere 'annuleer' in
'annuleren'. Beide beamvarianten herkenden sommige andere woorden al fout,
zoals 'kwart' als 'kort'. Dit is geen menselijke accuracytest. Timestamps
weglaten won in die tweede proef maar circa 16 ms. **Geen van beide is daarom
standaard geactiveerd.** De private helper accepteert begrensde benchmarkopties;
de productie-default blijft beam 3 met het bestaande timestampgedrag.

Bronnen: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) beschrijft
de CUDA-libraries, CPU-int8 en het verband tussen decoderinstellingen en
benchmarks; [CTranslate2 performance](https://opennmt.net/CTranslate2/performance.html)
beschrijft int8 en begrensde threadconcurrency. De projectmetingen hierboven
zijn afzonderlijk uitgevoerd en zijn geen overgenomen upstreambenchmarks.

## CPU-only keten en geheugen

`scripts/benchmark_low_memory.py --run-local --warmup` gebruikt de echte
ChatService, bestaande lokale Ollama-router/transport en private helper met
synthetische audio. De benchmark kiest alleen voor zijn eigen aanvragen
`num_gpu=0`, vier threads en een vaste seed. Geen .env-/gebruikersinstellingen
zijn veranderd. `/api/ps` bevestigde Qwen2.5:3B, 8192 context en `size_vram=0`.

| Onderdeel | Waarneming |
|---|---|
| Ollama runner + server/tray, working-set-som | circa 2491 MiB |
| Helper zelfgerapporteerde working set | maximaal circa 813 MiB in de warme keten |
| Helper piek | circa 941 MiB |
| Afzonderlijke testbackend/harness | circa 71 MiB |
| Getelde actieve set samen | circa **3,30 GiB**, exclusief Windows en gewone native client |
| Warme CPU-STT | circa 1,58–1,63 s per aangeboden testuitspraak |
| Warme CPU-AI eerste token | circa 2,03–2,33 s |
| Eerste antwoordzin/clausule-PCM, nieuwe route | 5,46 en 6,05 s in de warme liveproef |
| Eerste PCM, zinsbaseline | 7,00 en 9,18 s in die proef |
| Eerste opwarmbeurt | circa 20,46 s tot eerste PCM; geen beloofde instant koude start |

De live antwoorden verschilden in tekst en lengte ondanks een vaste seed.
De twee medianen zijn daarom **beschrijvend, geen gecontroleerd
versnellingspercentage**. De nieuwe API-tests bewijzen afzonderlijk dat een
geschikt eerste zinsdeel eerder beschikbaar komt dan de rest van dezelfde zin.
De clienttests bewijzen maximaal één voorbereid blok en het weggooien daarvan
bij Stop. Fysieke hoorbare latency en prosodie moeten nog beoordeeld worden.

Working-set-sommen kunnen gedeelde pagina's dubbeltellen; private commit is
weer iets anders dan fysieke RAM. De helpermeting hierboven komt uit de
helper zelf. De ouder-PID-meting van de venv-launcher (slechts enkele MiB)
vertegenwoordigt de inferenceruntime niet en is niet als helpergeheugen gebruikt.
Er is geen 8-GB-geheugenlimiet opgelegd en geen hard memory-quota geïmplementeerd.
Metingen kwamen van de Ryzen-ontwikkeldesktop; ze voorspellen geen N100-/andere
mini-pc-snelheid. Sommige build-/testruns liepen tijdens het onderzoek tegelijk.

## Voorlopig budget voor de toekomstige host

Reken voorlopig op **3,5–4 GiB voor JARVIS inclusief client en pieken**, daarnaast
ruimte voor Windows, drivers, hardware-reservering en overige programma's. Dit
is een ontwerpbudget, geen bewezen maximale allocatie. De onbekende processor,
werkelijk beschikbaar RAM en paging moeten op de echte host worden gemeten.
De huidige 8192-contextallocatie blijft behouden; context wordt niet stilzwijgend
ingekort om een mooie RAM-uitkomst te krijgen. Er is geen GPU-afhankelijkheid
toegevoegd en er blijven geen extra grote modellen permanent geladen.

Op een werkelijk krappe host kan het bestaande lichte/besparingsprofiel minder
modellen tegelijk resident houden. Dat kan extra herlaadlatency en minder
gesprekscontext betekenen; het is niet automatisch de snelste instelling.
Dat profiel is nu niet stilzwijgend voor de gebruiker gekozen. De huidige
ontwikkeling blijft `desktop-development`; migratie en permanente service zijn
niet uitgevoerd.

## Validatie en artifacts

- Server: **469 geslaagd**, 200,40 s, inclusief tien bestaande ongestagede
  gebruikersmailtests die buiten deze wijziging blijven.
- Windows: **122 geslaagd**, 5,42 s. Nieuwe fallback-/modellevensduurtests faalden
  vooraf op vier van vijf controles; de prefetchtest bewees vooraf dat geen
  volgend blok tijdens afspelen werd voorbereid.
- Android unit/lint/debug/release-build geslaagd, inclusief ready-chunk,
  legacy-preview en Unicode-tests. Geen aangesloten Android-device aanwezig;
  nieuwe telefoon-/microfoonacceptatie en installatie niet geclaimd.
- Ruff/mypy, drie pip checks, settingscontract, repository-/diffchecks geslaagd.
- Portable Windows-build: `.local/client-build-latency-8gb/`, acht pagina's en
  netwerk/microfoon/helper uit bij de startup-smoke. Verpakte helper verwerkt
  ontbrekende modellen zonder download. APK staat in `.local/android-build/`.

Ruwe synthetische rapporten staan onder `.local/voice-latency/`. Start de
decodervergelijking met `scripts/benchmark_stt.py --run-local --candidate greedy`
of `--candidate text-only`; CPU-keten met `scripts/benchmark_low_memory.py
--run-local --warmup`. Gebruik de bestaande servervenv plus geïnstalleerde
private voice-runtime. Geen microfoon, playback, echte accounts of downloads.

Nog te accepteren: echte denkpauzes, hoorbare eerste-reactietijd, stop/echo en
Windows-focus, plus subjectieve M3-prosodie bij de eerste komma. Algemene
context-/modelkwaliteitspunten uit EXPERIENCE_TEST_REPORT.md blijven open.
Geen fase 8, oproepen, betaalde diensten, publieke toegang of mini-pc-deployment.
