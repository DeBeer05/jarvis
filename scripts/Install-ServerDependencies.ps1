param([switch]$IncludeTests)
. (Join-Path $PSScriptRoot 'Server-Common.ps1')
Push-Location $JarvisProjectRoot
try {
    $requirements = if ($IncludeTests) { 'requirements-server-dev.txt' } else { 'requirements-server.txt' }
    & (Get-JarvisServerPython) -m pip install --upgrade -c constraints-server.txt pip
    if ($LASTEXITCODE -ne 0) { throw 'Veilige pip-versie installeren mislukt.' }
    & (Get-JarvisServerPython) -m pip install -r $requirements
    if ($LASTEXITCODE -ne 0) { throw 'Serverdependencies installeren mislukt.' }
    & (Get-JarvisServerPython) -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Dependencycontrole mislukt.' }
} finally { Pop-Location }
