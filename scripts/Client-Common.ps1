$ErrorActionPreference = 'Stop'
$JarvisClientRoot = Split-Path -Parent $PSScriptRoot
$JarvisClientPython = Join-Path $JarvisClientRoot '.local\client-venv\Scripts\python.exe'
function Assert-JarvisClientEnvironment {
    if (-not (Test-Path -LiteralPath $JarvisClientPython)) { throw 'Voer eerst scripts/Install-WindowsClient.ps1 uit.' }
}
