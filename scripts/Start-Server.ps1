param([switch]$Background)
. (Join-Path $PSScriptRoot 'Server-Common.ps1')
Push-Location $JarvisProjectRoot
try {
    $pythonPath = Get-JarvisServerPython
    if ($Background) {
        $process = Start-Process -FilePath $pythonPath -ArgumentList @('-m', 'server', '--no-console') -WorkingDirectory $JarvisProjectRoot -WindowStyle Hidden -PassThru
        & $pythonPath -m server status --wait 15
        if ($LASTEXITCODE -ne 0) { throw 'Server niet gereed. Bekijk .local/logs/server.log of start zonder -Background voor de foutmelding.' }
        Write-Output 'Server gestart of bestaande lokale server gevonden; gebruik Stop-Server.ps1 voor gecontroleerd afsluiten.'
    } else {
        & $pythonPath -m server
        if ($LASTEXITCODE -ne 0) { throw 'Server eindigde met een fout. Bekijk de gestructureerde logs.' }
    }
} finally { Pop-Location }
