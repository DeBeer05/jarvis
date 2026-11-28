param([string]$InstallRoot="$env:ProgramData\JARVIS")
& "$PSScriptRoot\STOP.ps1" -InstallRoot $InstallRoot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
& "$PSScriptRoot\START.ps1" -InstallRoot $InstallRoot
