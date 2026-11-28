param([string]$InstallRoot="$env:ProgramData\JARVIS")
. "$PSScriptRoot\Common.ps1"
Require-Admin
$release=Current-Release $InstallRoot
Set-Runtime $InstallRoot
Push-Location $release
try {Invoke-Python "$release\.venv\Scripts\python.exe" @('-m','server','stop','--wait','30')} finally {Pop-Location}
Stop-ScheduledTask -TaskName 'JARVIS-MiniPC' -ErrorAction SilentlyContinue
