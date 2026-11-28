param([Parameter(Mandatory)][string]$Package,[string]$InstallRoot,[switch]$UseExisting)
$ErrorActionPreference='Stop'
if(-not $InstallRoot){$InstallRoot=Join-Path $env:TEMP ('jarvis-minipc-smoke-'+[guid]::NewGuid())}
if(-not $UseExisting){& "$Package\INSTALL.ps1" -InstallRoot $InstallRoot -NoService -SkipOwnerSetup -SkipVoice}
if(-not $?) {throw 'Isolatie-installatie mislukt.'}
. "$Package\Common.ps1"
$release=Current-Release $InstallRoot
$python="$release\.venv\Scripts\python.exe"
Set-Runtime $InstallRoot
$env:JARVIS_PORT='18766'
$env:JARVIS_ALLOWED_ORIGINS='http://127.0.0.1:18766,http://localhost:18766'
if(Get-NetTCPConnection -LocalPort 18766 -State Listen -ErrorAction SilentlyContinue){throw 'Testpoort al in gebruik.'}
$stdout=Join-Path $InstallRoot 'logs\smoke.out'
$stderr=Join-Path $InstallRoot 'logs\smoke.err'
$process=Start-Process -FilePath $python -ArgumentList @('-m','server','--no-console') -WorkingDirectory $release -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
$null=$process.Handle
try{
 $ready=$false
 for($attempt=0;$attempt -lt 30;$attempt++){
  try{$value=Invoke-RestMethod http://127.0.0.1:18766/ready -TimeoutSec 2;if($value.status -eq 'ready'){$ready=$true;break}}catch{}
  Start-Sleep -Seconds 1
 }
 if(-not $ready){throw 'Geisoleerde server is niet gereed.'}
 Push-Location $release
 try{
  Invoke-Python $python @('-m','pip','check')
  Invoke-Python $python @('-c','from server.config import load_settings; from server.database import Database; from server.voice_secrets import read_secret; s=load_settings(); d=Database(s.database_path); d.initialize(); assert d.check(); assert len(read_secret(s.vault_key_file))==44; print(12345)')
  Invoke-Python $python @('-m','server','stop','--wait','15')
 }finally{Pop-Location}
 if(-not $process.WaitForExit(15000)){throw 'Testserver sluit niet correct af.'}
 $process.Refresh()
 if($process.ExitCode -ne 0){throw 'Testserver eindigde met een fout.'}
 Write-Host "Geisoleerde installatie, dependencies, SQLite, DPAPI, health en gecontroleerd stoppen geslaagd: $InstallRoot"
}finally{
 if(-not $process.HasExited){Stop-Process -Id $process.Id -ErrorAction SilentlyContinue}
 Remove-Item Env:\JARVIS_PORT -ErrorAction SilentlyContinue
 Remove-Item Env:\JARVIS_ALLOWED_ORIGINS -ErrorAction SilentlyContinue
}
