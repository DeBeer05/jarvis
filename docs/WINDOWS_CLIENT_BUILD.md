# Windows-build

Python 3.12 x64, Windows PowerShell 5.1. Vanuit de bestaande projectroot:

```powershell
powershell.exe -NoProfile -File scripts/Install-WindowsClient.ps1
powershell.exe -NoProfile -File scripts/Install-VoiceRuntime.ps1
.\.local\client-venv\Scripts\python.exe -m pytest -c pytest-client.ini -q
powershell.exe -NoProfile -File scripts/Build-WindowsClient.ps1
```

Runtime-/buildversies zijn vastgelegd in requirements-client*.txt en
constraints-client.txt. De servervenv wordt niet uitgebreid met Qt/PyInstaller.
PyInstaller maakt een portable onedir-build voor snelle start en vervangbare
losse Qt-DLLs. Geen installer, service of automatische systeemwijziging.

Uitvoer:

- `.local/client-build/dist/JARVIS/JARVIS.exe` met `_internal` en licenties.
- `.local/client-build/JARVIS-Windows-0.5.0-x64.zip`, de volledige map inclusief voice-runtime; modellen blijven extern.
- SHA-256 wordt door het buildscript weergegeven; een build is reproduceerbaar
  qua stappen/versies, niet als garantie van identieke PE-bytes/tijdstempels.

Kopieer/pak altijd de gehele map uit. Alleen JARVIS.exe is onvoldoende.
Config, credentials, server, API-sleutels, databases en modellen worden niet
meegebundeld. Windows Credential Manager bestaat al als OS-voorziening.
Bron-/licentieverantwoording staat naast de executable.

Automatische rookproef zonder netwerk of persoonlijke credentials:

```powershell
$exe = (Resolve-Path .local/client-build/dist/JARVIS/JARVIS.exe).Path
$profile = Join-Path $env:TEMP ('jarvis-smoke-' + [guid]::NewGuid())
$report = Join-Path $env:TEMP ('jarvis-smoke-' + [guid]::NewGuid() + '.json')
$process = Start-Process -FilePath $exe -ArgumentList @('--data-dir', ('"' + $profile + '"'), '--self-test-report', ('"' + $report + '"')) -PassThru
if (-not $process.WaitForExit(20000)) { throw 'Startup timeout' }
Get-Content -LiteralPath $report
```

De app toont een echt Qt-venster en sluit daarna zelf. Verwacht versie 0.5.0,
7 pagina's, network_started false en microphone_active false. CI doet deze proef na een Windows-build,
naast de normale server- en clienttests. Normaal starten gebruikt geen testvlag.
