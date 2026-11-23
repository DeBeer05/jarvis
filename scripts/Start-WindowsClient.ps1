param([switch]$Minimized)
. (Join-Path $PSScriptRoot 'Client-Common.ps1')
Assert-JarvisClientEnvironment
$clientPythonw = Join-Path (Split-Path -Parent $JarvisClientPython) 'pythonw.exe'
$clientEntry = Join-Path $JarvisClientRoot 'desktop-client\run_client.py'
$clientArgs = @('"' + $clientEntry + '"')
if ($Minimized) { $clientArgs += '--minimized' }
# pythonw avoids an extra console; application logs go to LOCALAPPDATA/JARVIS/Desktop.
Start-Process -FilePath $clientPythonw -ArgumentList $clientArgs -WorkingDirectory $JarvisClientRoot
Write-Output 'JARVIS-client gestart. De server wordt niet door de client gestart.'
