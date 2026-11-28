param([string]$InstallRoot="$env:ProgramData\JARVIS",[string]$KeyFile)
. "$PSScriptRoot\Common.ps1"
Require-Admin
$InstallRoot=Assert-Root $InstallRoot
$release=Current-Release $InstallRoot
if(-not $KeyFile){$KeyFile=Join-Path $InstallRoot 'secrets\backup.bin'}
Push-Location $release
try {
 if(-not(Test-Path -LiteralPath $KeyFile)){Invoke-Python "$release\.venv\Scripts\python.exe" @('scripts/minipc_admin.py','keygen-machine',$KeyFile)}
 Invoke-Python "$release\.venv\Scripts\python.exe" @('scripts/cloud_backup.py','daily','--database',"$InstallRoot\data\jarvis.sqlite3",'--directory',"$InstallRoot\backups",'--key-file',$KeyFile,'--portable','--old-vault-key',"$InstallRoot\secrets\vault.bin",'--include',"$InstallRoot\data\.env")
} finally {Pop-Location}
Write-Host 'Bewaar de back-upsleutel afzonderlijk. Deze Windows-DPAPI-sleutel is alleen op deze computer/gebruiker direct bruikbaar.'
