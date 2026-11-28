param([string]$InstallRoot="$env:ProgramData\JARVIS")
. "$PSScriptRoot\Common.ps1"
$InstallRoot=Assert-Root $InstallRoot
$release=Current-Release $InstallRoot
Set-Runtime $InstallRoot
$env:PYTHONPATH=$release
Copy-Item "$InstallRoot\data\.env" "$release\.env" -Force
Push-Location $release
try { & "$release\.venv\Scripts\python.exe" -m server run --no-console; exit $LASTEXITCODE } finally { Pop-Location }
