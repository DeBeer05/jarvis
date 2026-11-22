. (Join-Path $PSScriptRoot 'Server-Common.ps1')
Push-Location $JarvisProjectRoot
try {
    & (Get-JarvisServerPython) -m server status
    if ($LASTEXITCODE -ne 0) { throw 'Server niet actief, niet bereikbaar of runtimegegevens ongeldig.' }
} finally { Pop-Location }
