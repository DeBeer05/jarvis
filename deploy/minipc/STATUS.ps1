param([string]$InstallRoot="$env:ProgramData\JARVIS")
. "$PSScriptRoot\Common.ps1"
$release=Current-Release $InstallRoot
Set-Runtime $InstallRoot
Push-Location $release
try {& "$release\.venv\Scripts\python.exe" -m server status; & "$release\.venv\Scripts\python.exe" -m pip check} finally {Pop-Location}
Get-ScheduledTask -TaskName 'JARVIS-MiniPC' | Select-Object TaskName,State
if(Test-Path "$InstallRoot\logs\server.log"){Get-Content "$InstallRoot\logs\server.log" -Tail 15}
