. (Join-Path $PSScriptRoot 'Client-Common.ps1')
Assert-JarvisClientEnvironment
Push-Location $JarvisClientRoot
try {
    & $JarvisClientPython -m PyInstaller --noconfirm --clean --onedir --windowed --noupx --name JARVIS --paths desktop-client --distpath .local/client-build/dist --workpath .local/client-build/work --specpath .local/client-build --exclude-module tkinter --exclude-module PyQt6 --exclude-module PySide6.QtQml --exclude-module PySide6.QtQuick desktop-client/run_client.py
    if ($LASTEXITCODE -ne 0) { throw 'Windows-build mislukt.' }
    $clientBundle = Join-Path $JarvisClientRoot '.local\client-build\dist\JARVIS'
    Copy-Item -LiteralPath (Join-Path $JarvisClientRoot 'LICENSE') -Destination (Join-Path $clientBundle 'LICENSE-Mark-LVII.txt')
    Copy-Item -LiteralPath (Join-Path $JarvisClientRoot 'docs\WINDOWS_CLIENT_THIRD_PARTY.md') -Destination $clientBundle
    & $JarvisClientPython scripts/collect-client-licenses.py $clientBundle
    if ($LASTEXITCODE -ne 0) { throw 'Licenties verzamelen mislukt.' }
    $clientArchive = Join-Path $JarvisClientRoot '.local\client-build\JARVIS-Windows-0.4.0-x64.zip'
    Compress-Archive -LiteralPath $clientBundle -DestinationPath $clientArchive -Force
    Get-FileHash -LiteralPath (Join-Path $clientBundle 'JARVIS.exe'),$clientArchive -Algorithm SHA256 | Select-Object Path,Hash
    Write-Output ('Portable app: ' + (Join-Path $clientBundle 'JARVIS.exe'))
} finally { Pop-Location }
