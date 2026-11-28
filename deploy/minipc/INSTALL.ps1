param([string]$InstallRoot="$env:ProgramData\JARVIS",[switch]$SkipOwnerSetup,[switch]$NoService,[switch]$SkipVoice)
. "$PSScriptRoot\Common.ps1"
if(-not $NoService){Require-Admin}
$InstallRoot=Assert-Root $InstallRoot
if((Test-Path -LiteralPath $InstallRoot) -and (Get-ChildItem -LiteralPath $InstallRoot -Force | Select-Object -First 1) -and -not(Test-Path "$InstallRoot\.jarvis-installation")){throw 'Deze map bevat andere gegevens. Kies een nieuwe lege installatiemap.'}
New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
Set-Content "$InstallRoot\.jarvis-installation" 'JARVIS managed installation v1'
$principal=if($NoService){[Security.Principal.WindowsIdentity]::GetCurrent().Name}else{'*S-1-5-32-544'}
& icacls $InstallRoot /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' "${principal}:(OI)(CI)F" | Out-Null
if($LASTEXITCODE -ne 0){throw 'Beveiligde maprechten konden niet worden ingesteld.'}
$python=Get-Command python.exe -ErrorAction SilentlyContinue
if(-not $python -or $python.Source -like '*\WindowsApps\*' -or (& $python.Source -c 'import sys; print(sys.version_info >= (3,12) and sys.version_info < (3,14))') -ne 'True'){
 $installer=Join-Path $env:TEMP ('jarvis-python-'+[guid]::NewGuid()+'.exe')
 Invoke-WebRequest 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile $installer
 $signature=Get-AuthenticodeSignature -LiteralPath $installer
 if($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Python Software Foundation'){throw 'Python-installatiehandtekening is ongeldig.'}
 $process=Start-Process -FilePath $installer -ArgumentList '/quiet InstallAllUsers=1 PrependPath=0 Include_test=0' -WindowStyle Hidden -Wait -PassThru
 if($process.ExitCode -notin 0,3010){throw 'Python installeren is mislukt.'}
 $pythonPath="$env:ProgramFiles\Python312\python.exe"
}else{$pythonPath=$python.Source}
foreach($directory in 'releases','data','logs','run','secrets','backups'){New-Item -ItemType Directory -Force -Path (Join-Path $InstallRoot $directory) | Out-Null}
$manifest=Get-Content "$PSScriptRoot\manifest.json" -Raw | ConvertFrom-Json
$release=Join-Path $InstallRoot ('releases\'+$manifest.version)
if(Test-Path -LiteralPath $release){throw 'Deze release is al aanwezig. Gebruik REPAIR.ps1 of UPDATE.ps1.'}
foreach($entry in $manifest.files.PSObject.Properties){
 $file=Join-Path "$PSScriptRoot\payload" $entry.Name
 if((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLower() -ne $entry.Value){throw 'Installatiepakket is beschadigd.'}
}
Copy-Item -LiteralPath "$PSScriptRoot\payload" -Destination $release -Recurse
Invoke-Python $pythonPath @('-m','venv',"$release\.venv")
$runtimePython="$release\.venv\Scripts\python.exe"
Push-Location $release
try{
 Invoke-Python $runtimePython @('-m','pip','install','--disable-pip-version-check','-r','requirements-server.txt')
 Invoke-Python $runtimePython @('-m','pip','check')
 if(-not $SkipVoice){
  $voicePython=Join-Path $InstallRoot 'voice-venv\Scripts\python.exe'
  if(-not(Test-Path -LiteralPath $voicePython)){Invoke-Python $runtimePython @('-m','venv',"$InstallRoot\voice-venv")}
  Invoke-Python $voicePython @('-m','pip','install','-r','requirements-voice-server.txt')
  Invoke-Python $voicePython @('-m','pip','check')
  Invoke-Python $runtimePython @('scripts/download-voice-models.py','--accept-downloads','--directory',"$InstallRoot\models")
  Invoke-Python $runtimePython @('scripts/download-voice-models.py','--accept-downloads','--ronnie-only','--directory',"$InstallRoot\models")
 }
 if(-not(Test-Path "$InstallRoot\data\.env")){Copy-Item "$PSScriptRoot\.env.example" "$InstallRoot\data\.env"}
 Copy-Item "$InstallRoot\data\.env" "$release\.env"
 Set-Runtime $InstallRoot
 $env:PYTHONPATH=$release
 $init="from pathlib import Path; import os; from cryptography.fernet import Fernet; from server.voice_secrets import save_secret; p=Path(os.environ['JARVIS_VAULT_KEY_FILE']); save_secret(p,Fernet.generate_key().decode(),machine=True) if not p.exists() else None; from server.config import load_settings; from server.database import Database; Database(load_settings().database_path).initialize()"
 Invoke-Python $runtimePython @('-c',$init)
 if(-not $SkipOwnerSetup){Invoke-Python $runtimePython @('-m','server','setup-owner')}
}finally{Pop-Location}
Copy-Item "$PSScriptRoot\*.ps1" $InstallRoot -Force
Copy-Item -LiteralPath "$PSScriptRoot\provision-link.sh" -Destination (Join-Path $InstallRoot 'provision-link.sh') -Force
if(Test-Path -LiteralPath "$PSScriptRoot\oracle-connection.json"){Copy-Item -LiteralPath "$PSScriptRoot\oracle-connection.json" -Destination (Join-Path $InstallRoot 'oracle-connection.json') -Force}
Copy-Item "$PSScriptRoot\INSTALLATIE.md" $InstallRoot -Force
Set-Content "$InstallRoot\current.txt" $manifest.version
if(-not $NoService){
 $action=New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$InstallRoot\RUN.ps1`" -InstallRoot `"$InstallRoot`""
 $settings=New-ScheduledTaskSettingsSet -RestartCount 10 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew
 Register-ScheduledTask -TaskName 'JARVIS-MiniPC' -Action $action -Trigger (New-ScheduledTaskTrigger -AtStartup) -User SYSTEM -RunLevel Highest -Settings $settings -Force | Out-Null
 $backupAction=New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$InstallRoot\BACKUP.ps1`" -InstallRoot `"$InstallRoot`""
 Register-ScheduledTask -TaskName 'JARVIS-Backup' -Action $backupAction -Trigger (New-ScheduledTaskTrigger -Daily -At '03:00') -User SYSTEM -RunLevel Highest -Settings $settings -Force | Out-Null
 & "$InstallRoot\START.ps1" -InstallRoot $InstallRoot
}
Write-Host 'Installatie gereed. Open http://127.0.0.1:8765 en meld u aan. Oracle: CONNECT-ORACLE.ps1.'
