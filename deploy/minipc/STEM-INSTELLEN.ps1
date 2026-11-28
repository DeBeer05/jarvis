param([string]$InstallRoot="$env:ProgramData\JARVIS")
. "$PSScriptRoot\Common.ps1"
Require-Admin
$release=Current-Release $InstallRoot
Push-Location $release
try{Invoke-Python "$release\.venv\Scripts\python.exe" @('scripts/minipc_admin.py','configure-voice',$InstallRoot)}finally{Pop-Location}
