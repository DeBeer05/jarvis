param([string]$InstallRoot="$env:ProgramData\JARVIS")
. "$PSScriptRoot\Common.ps1"
Require-Admin
Start-ScheduledTask -TaskName 'JARVIS-MiniPC'
Wait-Ready
$release=Current-Release $InstallRoot
Set-Runtime $InstallRoot
Push-Location $release
try{Invoke-Python "$release\.venv\Scripts\python.exe" @('-m','server','status')}finally{Pop-Location}
Write-Host 'JARVIS is bereikbaar op poort 8765.'
