$ErrorActionPreference = 'Stop'
$JarvisProjectRoot = Split-Path -Parent $PSScriptRoot

function Get-JarvisServerPython {
    $pythonPath = Join-Path $JarvisProjectRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $pythonPath)) {
        throw 'Virtuele omgeving ontbreekt. Voer scripts/Initialize-ServerEnvironment.ps1 uit.'
    }
    return $pythonPath
}
