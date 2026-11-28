# Shared installation functions. Secrets/data are kept outside versioned releases.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
function Require-Admin {
 $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
 if(-not ([Security.Principal.WindowsPrincipal]$identity).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'Start PowerShell als administrator.'}
}
function Assert-Root([string]$Root) {
 $resolved=[IO.Path]::GetFullPath($Root)
 if($resolved -eq [IO.Path]::GetPathRoot($resolved) -or $resolved.Length -lt 12){throw 'Kies een aparte JARVIS-installatiemap.'}
 if(Test-Path -LiteralPath $resolved){if((Get-Item -LiteralPath $resolved).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Geen omgeleide installatiemap toegestaan.'}}
 return $resolved
}
function Current-Release([string]$Root) {
 $name=(Get-Content -LiteralPath (Join-Path $Root 'current.txt') -Raw).Trim()
 if($name -notmatch '^[a-zA-Z0-9._-]+$'){throw 'Ongeldige releaseverwijzing.'}
 return Join-Path $Root "releases\$name"
}
function Invoke-Python([string]$Python,[string[]]$Arguments) {
 & $Python @Arguments
 if($LASTEXITCODE -ne 0){throw "Python-opdracht is mislukt ($LASTEXITCODE). Raadpleeg de logboeken."}
}
function Set-Runtime([string]$Root) {
 $env:JARVIS_MODELS_DIR=Join-Path $Root 'models'
 $env:JARVIS_VOICE_PYTHON=Join-Path $Root 'voice-venv\Scripts\python.exe'
 $env:JARVIS_DATABASE_PATH=Join-Path $Root 'data\jarvis.sqlite3'
 $env:JARVIS_RUNTIME_DIR=Join-Path $Root 'run'
 $env:JARVIS_LOG_PATH=Join-Path $Root 'logs\server.log'
 $env:JARVIS_VAULT_KEY_FILE=Join-Path $Root 'secrets\vault.bin'
}
function Wait-Ready {
 for($attempt=0;$attempt -lt 30;$attempt++){
  try{$response=Invoke-RestMethod -Uri 'http://127.0.0.1:8765/health' -TimeoutSec 2;if($response.status -eq 'ok' -or $response.status -eq 'ready'){return}}catch{}
  Start-Sleep -Seconds 1
 }
 throw 'JARVIS reageert niet op de healthcheck. Bekijk STATUS.ps1 en logs\server.log.'
}
