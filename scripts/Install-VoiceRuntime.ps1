. (Join-Path $PSScriptRoot 'Client-Common.ps1')
Push-Location $JarvisClientRoot
try {
    $voicePython = Join-Path $JarvisClientRoot '.local\voice-venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $voicePython)) {
        $serverPython = Join-Path $JarvisClientRoot '.venv\Scripts\python.exe'
        if (Test-Path -LiteralPath $serverPython) { & $serverPython -m venv .local/voice-venv }
        else { py -3.12 -m venv .local/voice-venv }
        if ($LASTEXITCODE -ne 0) { throw 'Spraakomgeving maken mislukt.' }
    }
    & $voicePython -m pip install --upgrade -c constraints-voice.txt pip
    if ($LASTEXITCODE -ne 0) { throw 'Pip installeren mislukt.' }
    & $voicePython -m pip install -r requirements-voice.txt
    if ($LASTEXITCODE -ne 0) { throw 'Spraakdependencies installeren mislukt.' }
    & $voicePython -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Spraakdependencycontrole mislukt.' }
    Write-Output 'Spraakruntime gereed. Geen Whisper-/Piper-modellen gedownload, geen microfoon geopend.'
} finally { Pop-Location }
