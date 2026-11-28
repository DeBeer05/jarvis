param([string]$InstallRoot="$env:ProgramData\JARVIS")
. "$PSScriptRoot\Common.ps1"
Require-Admin
& "$PSScriptRoot\STOP.ps1" -InstallRoot $InstallRoot
Unregister-ScheduledTask -TaskName 'JARVIS-MiniPC' -Confirm:$false
if(Get-ScheduledTask -TaskName 'JARVIS-OracleLink' -ErrorAction SilentlyContinue){Stop-ScheduledTask -TaskName 'JARVIS-OracleLink';Unregister-ScheduledTask -TaskName 'JARVIS-OracleLink' -Confirm:$false}
if(Get-ScheduledTask -TaskName 'JARVIS-Backup' -ErrorAction SilentlyContinue){Stop-ScheduledTask -TaskName 'JARVIS-Backup';Unregister-ScheduledTask -TaskName 'JARVIS-Backup' -Confirm:$false}
Write-Host 'Automatische taken verwijderd. Code, instellingen en persoonlijke gegevens zijn behouden.'
