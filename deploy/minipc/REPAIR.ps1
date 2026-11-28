param([string]$InstallRoot="$env:ProgramData\JARVIS")
. "$PSScriptRoot\Common.ps1"
Require-Admin
$release=Current-Release $InstallRoot
Push-Location $release
try {Invoke-Python "$release\.venv\Scripts\python.exe" @('-m','pip','install','-r','requirements-server.txt');Invoke-Python "$release\.venv\Scripts\python.exe" @('-m','pip','check')} finally {Pop-Location}
& "$PSScriptRoot\RESTART.ps1" -InstallRoot $InstallRoot
