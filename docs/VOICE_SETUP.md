# Spraak gebruiken

Start vanuit de bestaande projectmap in Windows PowerShell (5.1 werkt):

```powershell
powershell.exe -NoProfile -File scripts/Start-Server.ps1 -Background
powershell.exe -NoProfile -File scripts/Start-WindowsClient.ps1
```

Sluit een al geopende oudere app eerst volledig via het systeemvak. Alleen het
venster sluiten kan de app in het systeemvak laten draaien. Serverpoort blijft
8765. Je bestaande gebruikersnaam/wachtwoord en veilig bewaarde sessie blijven
geldig. Spraak maakt geen nieuw account of server aan.

1. Open **Spraak**, log indien nodig in bij Account.
2. Open **Stem en microfoon instellen**, klik **Audioapparaten vernieuwen** en kies microfoon/luidspreker. De apparaatkeuze wordt meteen onthouden. Controleer de
   namen opnieuw na apparaatwissels; Windows-apparaatnummers kunnen veranderen.
3. Kies **Piper → Ronnie**, snelheid 1.0, GPU automatisch of CPU. Klik
   **Spraakinstellingen toepassen en opslaan**. **Stemvoorbeeld afspelen** test
   alleen uitvoer en vraagt geen microfoontoegang.
4. Geef bij de instellingen eenmalig microfoontoestemming; de app onthoudt die op
   verzoek van de eigenaar. Op deze desktop is dat al ingesteld. Windows kan daarnaast
   eigen microfoonrechten vereisen; geef die zelf in Windows als je dat wilt.
5. Klik de grote **Start luisteren**-knop of **Ctrl+Space**. Spreek
   Nederlands. Stilte beëindigt de opname; nogmaals klikken verwerkt meteen.
   **Ik luister** betekent actieve opname; **Ik hoor je** betekent dat de lokale
   spraakpoort geluid herkent. De niveaubalk beweegt met het microfoonsignaal.
   **Spraak verwerken** betekent herkenning; onder **JIJ** zie je wat is verstaan.
   **JARVIS denkt/spreekt** toont de antwoordfase. De aparte regel vermeldt altijd
   of de microfoon actief of uit is. Het antwoord stroomt en wordt uitgesproken.
6. **Stop alles** of **Ctrl+Shift+Space** onderbreekt audio, wachtende synthese en
   het AI-antwoord. Druk daarna opnieuw op spreken voor je volgende vraag.

Sneltoetsen zijn instelbaar en standaard alleen binnen JARVIS actief. Globaal
registreren gebeurt uitsluitend na het afzonderlijke opt-in-vinkje én toepassen.
Dit vinkje wordt bij iedere appstart opnieuw uitgezet. Een bezette combinatie
geeft een melding; de appcombinaties blijven dan beschikbaar.

**Hé JARVIS** is optioneel en experimenteel: schakel het na toestemming in en
zeg de activatie aan het begin van je uiting. De herkenning wacht op stilte en
Whisper. Dit is langzamer dan een dedicated wake-wordmodel. Gebruik PTT voor de
betrouwbaarste bediening. Zet wake uit of klik Stop om standby te beëindigen.
Een optioneel vervolgvraagvenster (1–30 s) start na het gesproken antwoord een
nieuwe opname in hetzelfde gesprek. Standaard 0/uit. Geen agenda-integratie actief.

De instelling gevoeligheid regelt de spraakenergiepoort, geen getrainde
wake-word-confidence. Verlaag bij ruis/ongewenste activatie, verhoog bij zachte
spraak. Pas invoerversterking voorzichtig aan; clipping schaadt herkenning.
Opnamelimiet en stilte-timeout begrenzen langere opdrachten.

Installatie bij een nieuwe checkout, zonder modeldownloads:

```powershell
powershell.exe -NoProfile -File scripts/Install-WindowsClient.ps1
powershell.exe -NoProfile -File scripts/Install-VoiceRuntime.ps1
```

De eigenaar gaf in deze opdracht expliciet toestemming voor Whisper Small + MLS
(circa 563 MB) en daarna Ronnie (circa 63 MB). Op deze desktop staan ze al in
`%LOCALAPPDATA%\JARVIS\Desktop\models`. Runtime downloadt nooit automatisch.
Op een andere pc: lees [modellen en licenties](VOICE_MODELS.md), geef eerst
toestemming en voer dan bewust uit:

```powershell
.\.venv\Scripts\python.exe scripts/download-voice-models.py --accept-downloads
.\.venv\Scripts\python.exe scripts/download-voice-models.py --accept-downloads --ronnie-only
```

De tweede opdracht is nodig voor de aanbevolen standaardstem. Modelmap is
instelbaar; plaats niet-persoonlijke modellen buiten Git. Stemprofiel 0–51 geldt
alleen voor de experimentele MLS-stem; Ronnie heeft één spreker.

Portable build (modellen blijven extern):

```powershell
powershell.exe -NoProfile -File scripts/Build-WindowsClient.ps1
.\.local\client-build\dist\JARVIS\JARVIS.exe
```

Kopieer bij portable gebruik de **hele JARVIS-map**, inclusief voice-runtime.
Zip: `.local/client-build/JARVIS-Windows-0.5.0-x64.zip`. Geen Python-installatie
nodig voor de complete portable map; Windowsdrivers en lokale modellen wel.
Geen Whisper-/Piper-spraakgewichten, credentials, logs of persoonlijke chatdatabase
in de zip. Silero-VAD en aanvullende pakketdata uit de vastgepinde wheels zijn
wel onderdeel van de runtime.

Bij fouten: controleer invoer/uitvoer, modelmap en of een andere app de microfoon
bezet houdt. Bij CUDA-problemen kies CPU; er is automatische fallback. Bij
serveruitval wordt niets ongemerkt opnieuw verstuurd; laat de app herverbinden,
log alleen indien nodig opnieuw in en spreek de vraag opnieuw in.
STT/Piper werken lokaal zonder internet; AI-antwoord offline vereist ook een
werkende lokale server plus Ollama/model en keuze Ollama. Auto kan cloud proberen.
