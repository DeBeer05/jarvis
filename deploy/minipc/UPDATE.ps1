param([Parameter(Mandatory)][string]$Package,[string]$InstallRoot="$env:ProgramData\JARVIS",[switch]$Rollback)
. "$PSScriptRoot\Common.ps1"
Require-Admin
$InstallRoot=Assert-Root $InstallRoot
$previous=(Get-Content "$InstallRoot\current.txt" -Raw).Trim()
if($Rollback){
 if(-not(Test-Path "$InstallRoot\previous.txt")){throw 'Geen eerdere release beschikbaar.'}
 $target=(Get-Content "$InstallRoot\previous.txt" -Raw).Trim()
 if($target -notmatch '^[a-zA-Z0-9._-]+$'){throw 'Ongeldige rollbackverwijzing.'}
 & "$PSScriptRoot\STOP.ps1" -InstallRoot $InstallRoot
 Copy-Item "$InstallRoot\current.txt" "$InstallRoot\last-failed.txt" -Force
 Set-Content "$InstallRoot\current.txt" $target
 & "$PSScriptRoot\START.ps1" -InstallRoot $InstallRoot
 exit
}
$Package=[IO.Path]::GetFullPath($Package)
$manifest=Get-Content "$Package\manifest.json" -Raw | ConvertFrom-Json
if($manifest.version -notmatch '^[a-zA-Z0-9._-]+$'){throw 'Ongeldige versie.'}
$release=Join-Path $InstallRoot ('releases\'+$manifest.version)
if(Test-Path -LiteralPath $release){throw 'Release bestaat al; gebruik REPAIR of kies een nieuw pakket.'}
foreach($entry in $manifest.files.PSObject.Properties){
 if($entry.Name -match '(^|/)\.\.?(/|$)|[:\\]' -or $entry.Name.StartsWith('/')){throw 'Ongeldig pakketpad.'}
 $file=Join-Path "$Package\payload" $entry.Name
 if((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLower() -ne $entry.Value){throw 'Beschadigd pakket.'}
}
# Prepare dependencies while the current service keeps running.
Copy-Item -LiteralPath "$Package\payload" -Destination $release -Recurse
$oldRelease=Current-Release $InstallRoot
Invoke-Python "$oldRelease\.venv\Scripts\python.exe" @('-m','venv',"$release\.venv")
Push-Location $release
try{Invoke-Python "$release\.venv\Scripts\python.exe" @('-m','pip','install','-r','requirements-server.txt');Invoke-Python "$release\.venv\Scripts\python.exe" @('-m','pip','check')}finally{Pop-Location}
& "$PSScriptRoot\BACKUP.ps1" -InstallRoot $InstallRoot
& "$PSScriptRoot\STOP.ps1" -InstallRoot $InstallRoot
Copy-Item "$InstallRoot\data\jarvis.sqlite3" "$InstallRoot\data\pre-update.sqlite3" -Force
Set-Content "$InstallRoot\previous.txt" $previous
Set-Content "$InstallRoot\current.txt" $manifest.version
try{
 & "$PSScriptRoot\START.ps1" -InstallRoot $InstallRoot
 Copy-Item "$Package\*.ps1" $InstallRoot -Force
}catch{
 & "$PSScriptRoot\STOP.ps1" -InstallRoot $InstallRoot
 $stamp=Get-Date -Format 'yyyyMMddHHmmssfff'
 foreach($name in 'jarvis.sqlite3','jarvis.sqlite3-wal','jarvis.sqlite3-shm'){
  $file=Join-Path "$InstallRoot\data" $name
  if(Test-Path -LiteralPath $file){Move-Item -LiteralPath $file -Destination "$file.failed-$stamp"}
 }
 Copy-Item "$InstallRoot\data\pre-update.sqlite3" "$InstallRoot\data\jarvis.sqlite3"
 Set-Content "$InstallRoot\current.txt" $previous
 & "$PSScriptRoot\START.ps1" -InstallRoot $InstallRoot
 throw 'Update niet gezond; de vorige release en database zijn hersteld. De mislukte database is behouden.'
}
