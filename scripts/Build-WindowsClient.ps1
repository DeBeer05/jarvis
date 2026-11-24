. (Join-Path $PSScriptRoot 'Client-Common.ps1')
Assert-JarvisClientEnvironment
Push-Location $JarvisClientRoot
$previousClientBuildPath = $env:PATH
try {
    # Build only against this Python/Qt environment and Windows. Tool-host PATHs
    # can contain an unrelated ICU DLL (e.g. PDF tools) with incompatible exports.
    $clientBasePython = & $JarvisClientPython -c 'import sys; print(sys.base_prefix)'
    if ($LASTEXITCODE -ne 0) { throw 'Python-installatie bepalen mislukt.' }
    $env:PATH = @((Split-Path -Parent $JarvisClientPython), $clientBasePython,
        (Join-Path $env:SystemRoot 'System32'), $env:SystemRoot) -join ';'
    & $JarvisClientPython -m PyInstaller --noconfirm --clean --onedir --windowed --noupx --name JARVIS --paths desktop-client --paths . --distpath .local/client-build/dist --workpath .local/client-build/work --specpath .local/client-build --exclude-module tkinter --exclude-module PyQt6 --exclude-module PySide6.QtQml --exclude-module PySide6.QtQuick desktop-client/run_client.py
    if ($LASTEXITCODE -ne 0) { throw 'Windows-build mislukt.' }
    $clientBundle = Join-Path $JarvisClientRoot '.local\client-build\dist\JARVIS'
    # Python 3.12 carries an older VC runtime. Qt's pinned wheel carries newer
    # redistributables; put that coherent set at the loader's first search path.
    $clientQtDirectory = Join-Path (Split-Path -Parent $JarvisClientPython) '..\Lib\site-packages\PySide6'
    foreach ($runtime in (Get-ChildItem -LiteralPath $clientQtDirectory -Filter '*140*.dll' -File)) {
        Copy-Item -LiteralPath $runtime.FullName -Destination (Join-Path $clientBundle '_internal') -Force
    }
    Copy-Item -LiteralPath (Join-Path $JarvisClientRoot 'LICENSE') -Destination (Join-Path $clientBundle 'LICENSE-Mark-LVII.txt')
    Copy-Item -LiteralPath (Join-Path $JarvisClientRoot 'docs\WINDOWS_CLIENT_THIRD_PARTY.md') -Destination $clientBundle
    & $JarvisClientPython scripts/collect-client-licenses.py $clientBundle
    if ($LASTEXITCODE -ne 0) { throw 'Licenties verzamelen mislukt.' }
    $voicePython = Join-Path $JarvisClientRoot '.local\voice-venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $voicePython)) { throw 'Voer scripts/Install-VoiceRuntime.ps1 uit voor de complete spraakbuild.' }
    $env:PATH = @((Split-Path -Parent $voicePython), $clientBasePython,
        (Join-Path $env:SystemRoot 'System32'), $env:SystemRoot) -join ';'
    & $voicePython -m PyInstaller --noconfirm --clean --onedir --console --noupx --name JARVIS-Voice --paths desktop-client --distpath .local/voice-build/dist --workpath .local/voice-build/work --specpath .local/voice-build --collect-all piper --collect-all faster_whisper --collect-all ctranslate2 --collect-all onnxruntime --collect-all av --exclude-module tkinter --exclude-module PyQt6 --exclude-module PySide6 --exclude-module torch --exclude-module tensorflow desktop-client/voice_worker.py
    if ($LASTEXITCODE -ne 0) { throw 'Spraakhelper bouwen mislukt.' }
    $voiceBundle = Join-Path $clientBundle 'voice-runtime'
    # Copy the coherent helper beside the app. Models remain external and are
    # never included automatically. No user files are moved or removed.
    New-Item -ItemType Directory -Force -Path $voiceBundle | Out-Null
    Copy-Item -Path '.local/voice-build/dist/JARVIS-Voice/*' -Destination $voiceBundle -Recurse -Force
    & $voicePython scripts/collect-client-licenses.py $voiceBundle --voice
    if ($LASTEXITCODE -ne 0) { throw 'Spraaklicenties verzamelen mislukt.' }
    $voiceSource = Join-Path $voiceBundle 'helper-source'
    New-Item -ItemType Directory -Force -Path $voiceSource | Out-Null
    Copy-Item -LiteralPath (Join-Path $JarvisClientRoot 'desktop-client\voice_worker.py'),(Join-Path $JarvisClientRoot 'desktop-client\voice_runtime') -Destination $voiceSource -Recurse -Force
    Copy-Item -LiteralPath (Join-Path $JarvisClientRoot 'requirements-voice.txt'),(Join-Path $JarvisClientRoot 'constraints-voice.txt') -Destination $voiceSource
    Copy-Item -LiteralPath (Join-Path $JarvisClientRoot 'docs\VOICE_MODELS.md'),(Join-Path $JarvisClientRoot 'docs\VOICE_PRIVACY.md'),(Join-Path $JarvisClientRoot 'docs\VOICE_SETUP.md') -Destination $clientBundle
    $clientVersion = & $JarvisClientPython -c "import sys; sys.path.insert(0, 'desktop-client'); from jarvis_client import __version__; print(__version__)"
    if ($LASTEXITCODE -ne 0 -or $clientVersion -notmatch '^\d+\.\d+\.\d+$') { throw 'Clientversie bepalen mislukt.' }
    $clientArchive = Join-Path $JarvisClientRoot ('.local\client-build\JARVIS-Windows-' + $clientVersion + '-x64.zip')
    Compress-Archive -LiteralPath $clientBundle -DestinationPath $clientArchive -Force
    Get-FileHash -LiteralPath (Join-Path $clientBundle 'JARVIS.exe'),$clientArchive -Algorithm SHA256 | Select-Object Path,Hash
    Write-Output ('Portable app: ' + (Join-Path $clientBundle 'JARVIS.exe'))
} finally { $env:PATH = $previousClientBuildPath; Pop-Location }
