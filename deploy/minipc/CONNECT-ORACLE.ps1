param([string]$InstallRoot="$env:ProgramData\JARVIS",[string]$HostName,[string]$AdminKey,[string]$HostPublicKey,[string]$GatewayHost)
. "$PSScriptRoot\Common.ps1"
Require-Admin
$InstallRoot=Assert-Root $InstallRoot
if(Test-Path "$PSScriptRoot\oracle-connection.json"){
 $site=Get-Content "$PSScriptRoot\oracle-connection.json" -Raw|ConvertFrom-Json
 if(-not $HostName){$HostName=$site.host}
 if(-not $HostPublicKey){$HostPublicKey=$site.host_public_key}
 if(-not $GatewayHost){$GatewayHost=$site.gateway}
}
if(-not $HostName){$HostName=Read-Host 'Oracle IP of hostnaam'}
if(-not $HostPublicKey){$HostPublicKey=Read-Host 'Eerder via Oracle Console gecontroleerde SSH-hostsleutel (ssh-ed25519 AAAA...)'}
if(-not $GatewayHost){$GatewayHost=Read-Host 'Gratis HTTPS-hostnaam van uw Oracle-gateway'}
if($HostName -notmatch '^[a-zA-Z0-9.-]+$' -or $GatewayHost -notmatch '^[a-zA-Z0-9.-]+$' -or $HostPublicKey -notmatch '^ssh-ed25519 [A-Za-z0-9+/=]+$'){throw 'Ongeldige hostgegevens.'}
if(-not $AdminKey){
 $documents=[Environment]::GetFolderPath('MyDocuments')
 $AdminKey=Join-Path $documents 'oracle ssh\private.key'
 if(-not(Test-Path -LiteralPath $AdminKey)){$AdminKey=Read-Host 'Volledig pad naar uw bestaande Oracle private.key'}
}
$secrets=Join-Path $InstallRoot 'secrets'
$key=Join-Path $secrets 'oracle-link'
$known=Join-Path $secrets 'oracle-known-hosts'
Set-Content -LiteralPath $known -Value "$HostName $HostPublicKey" -Encoding ascii
if(-not(Test-Path -LiteralPath $key)){
 $release=Current-Release $InstallRoot
 Invoke-Python "$release\.venv\Scripts\python.exe" @("$release\scripts\minipc_admin.py",'generate-link-key',$key)
}
& icacls $key /inheritance:r /grant:r '*S-1-5-18:F' '*S-1-5-32-544:F' /setowner '*S-1-5-18' | Out-Null
if($LASTEXITCODE -ne 0){throw 'De tunnelsleutel kon niet met SYSTEM worden beveiligd.'}
$public=(Get-Content "$key.pub" -Raw).Trim()
if($public -notmatch '^ssh-ed25519 [A-Za-z0-9+/=]+(?: [A-Za-z0-9_.-]+)?$'){throw 'Ongeldige lokale publieke tunnelsleutel.'}
$provision=Get-Content "$PSScriptRoot\provision-link.sh" -Raw
# The public key contains no shell metacharacters; never upload the private key.
$provision=$provision.Replace('read -r public_key',"public_key='$public'")
$provision | & ssh -i $AdminKey -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o "UserKnownHostsFile=$known" -o HostKeyAlgorithms=ssh-ed25519 "ubuntu@$HostName" "sed 's/`\r$//' | bash"
if($LASTEXITCODE -ne 0){throw 'Oracle-inrichting niet bevestigd; bestaande SSH-toegang is behouden.'}
$link=@{host=$HostName;key=$key;known=$known}|ConvertTo-Json
Set-Content "$InstallRoot\data\oracle-link.json" $link
$action=New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$InstallRoot\TUNNEL.ps1`" -InstallRoot `"$InstallRoot`""
$settings=New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -StartWhenAvailable
Register-ScheduledTask -TaskName 'JARVIS-OracleLink' -Action $action -Trigger (New-ScheduledTaskTrigger -AtStartup) -User SYSTEM -RunLevel Highest -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName 'JARVIS-OracleLink'
# Preserve previous settings and add only explicit gateway settings.
$envFile=Join-Path $InstallRoot 'data\.env'
Copy-Item $envFile "$envFile.pre-oracle-$(Get-Date -Format yyyyMMddHHmmss)"
$lines=Get-Content $envFile | Where-Object {$_ -notmatch '^JARVIS_(PUBLIC_ORIGIN|TRUSTED_HOSTS|ALLOWED_ORIGINS|COOKIE_SECURE)='}
$lines+=@("JARVIS_PUBLIC_ORIGIN=https://$GatewayHost","JARVIS_TRUSTED_HOSTS=127.0.0.1,localhost,$GatewayHost","JARVIS_ALLOWED_ORIGINS=http://127.0.0.1:8765,http://localhost:8765,https://$GatewayHost",'JARVIS_COOKIE_SECURE=true')
Set-Content $envFile $lines
& "$PSScriptRoot\RESTART.ps1" -InstallRoot $InstallRoot
Write-Host "Open https://$GatewayHost op uw telefoon. Meld u aan en bevestig de bestaande eigenaarpairing."
