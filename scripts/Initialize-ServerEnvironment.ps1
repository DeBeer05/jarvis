param([string]$PythonVersion = '3.12')
. (Join-Path $PSScriptRoot 'Server-Common.ps1')
Push-Location $JarvisProjectRoot
try {
    $venvPath = Join-Path $JarvisProjectRoot '.venv'
    if (Test-Path -LiteralPath $venvPath) {
        $pythonPath = Get-JarvisServerPython
        & $pythonPath --version
        if ($LASTEXITCODE -ne 0) { throw 'Bestaande virtuele omgeving is niet bruikbaar; niets overschreven.' }
        Write-Output 'Bestaande virtuele omgeving behouden.'
        return
    }
    & py "-$PythonVersion" -m venv $venvPath
    if ($LASTEXITCODE -ne 0) { throw "Python $PythonVersion ontbreekt of venv aanmaken is mislukt." }
    Write-Output 'Virtuele omgeving voorbereid. Installeer nu de serverdependencies.'
} finally { Pop-Location }
