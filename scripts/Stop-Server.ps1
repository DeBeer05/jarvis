. (Join-Path $PSScriptRoot 'Server-Common.ps1')
Push-Location $JarvisProjectRoot
try {
    & (Get-JarvisServerPython) -m server stop
    if ($LASTEXITCODE -ne 0) { throw 'Geen passende server gevonden of afsluiten mislukt; er is geen proces geforceerd gestopt.' }
} finally { Pop-Location }
