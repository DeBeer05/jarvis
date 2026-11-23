. (Join-Path $PSScriptRoot 'Client-Common.ps1')
Push-Location $JarvisClientRoot
try {
    if (-not (Test-Path -LiteralPath $JarvisClientPython)) {
        $serverPython = Join-Path $JarvisClientRoot '.venv\Scripts\python.exe'
        if (Test-Path -LiteralPath $serverPython) { & $serverPython -m venv .local/client-venv }
        else { py -3.12 -m venv .local/client-venv }
        if ($LASTEXITCODE -ne 0) { throw 'Clientomgeving maken mislukt.' }
    }
    & $JarvisClientPython -m pip install --upgrade -c constraints-client.txt pip
    if ($LASTEXITCODE -ne 0) { throw 'Pip installeren mislukt.' }
    & $JarvisClientPython -m pip install -r requirements-client-dev.txt
    if ($LASTEXITCODE -ne 0) { throw 'Clientdependencies installeren mislukt.' }
    & $JarvisClientPython -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Clientdependencycontrole mislukt.' }
} finally { Pop-Location }
