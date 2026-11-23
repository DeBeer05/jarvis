param([string]$ClientFile, [switch]$CheckOnly, [switch]$NoBrowser)
. (Join-Path $PSScriptRoot 'Server-Common.ps1')
Push-Location $JarvisProjectRoot
try {
    if (-not $ClientFile) {
        if ($CheckOnly) { throw 'Geef -ClientFile op voor alleen controleren.' }
        Write-Output 'Kies je gedownloade Google OAuth-clientbestand van type Desktop-app.'
        Write-Output 'Benodigde APIs in Google Cloud: Google Calendar API en Gmail API.'
        Add-Type -AssemblyName PresentationFramework
        $picker = New-Object Microsoft.Win32.OpenFileDialog
        $picker.Title = 'Kies Google Desktop OAuth-client JSON'
        $picker.Filter = 'Google OAuth JSON (*.json)|*.json'
        if (-not $picker.ShowDialog()) { Write-Output 'Geannuleerd; niets gewijzigd.'; exit 0 }
        $ClientFile = $picker.FileName
    }
    $python = Get-JarvisServerPython
    $arguments = @((Join-Path $PSScriptRoot 'configure_google.py'), '--root', $JarvisProjectRoot, '--client-file', $ClientFile)
    if ($CheckOnly) { $arguments += '--check-only' }
    & $python @arguments
    if ($LASTEXITCODE -ne 0) { throw 'Google-clientbestand niet ingesteld.' }
    if ($CheckOnly) { exit 0 }
    $stopOutput = & $python -m server stop
    $stopCode = $LASTEXITCODE
    Write-Output $stopOutput
    if ($stopCode -ne 0) {
        $stopState = $stopOutput | ConvertFrom-Json
        if ($stopState.status -ne 'not_running') { throw 'Gecontroleerd stoppen niet bevestigd; geen proces geforceerd gestopt.' }
    }
    & (Join-Path $PSScriptRoot 'Start-Server.ps1') -Background
    $asset = Invoke-WebRequest -Uri 'http://127.0.0.1:8765/chat/assets/automations.js' -UseBasicParsing
    if ($asset.StatusCode -ne 200 -or $asset.Headers['Content-Type'] -notmatch '(java|ecma)script') { throw 'Automatiseringen-script wordt niet correct geladen.' }
    Write-Output 'Log zo nodig in op JARVIS en open daarna opnieuw de koppelpagina.'
    Write-Output 'Alle vier ondersteunde rechten staan geselecteerd. Klik zelf Google koppelen en geef toestemming bij Google.'
    $url = 'http://127.0.0.1:8765/automations?google=all#oauth'
    Write-Output $url
    if (-not $NoBrowser) { Start-Process $url }
} catch {
    Write-Output 'Google-setup niet voltooid. Controleer het gekozen Desktop OAuth-JSON, de serverstatus en de installatiehandleiding.'
    exit 1
} finally { Pop-Location }
