$ErrorActionPreference = 'Stop'
$phase6Root = Split-Path -Parent $PSScriptRoot
$phase6OldSdk = $env:ANDROID_HOME
$phase6OldSdkRoot = $env:ANDROID_SDK_ROOT
Push-Location (Join-Path $phase6Root 'android')
try {
    $env:ANDROID_HOME = Join-Path $phase6Root '.local\android-tools\sdk'
    $env:ANDROID_SDK_ROOT = $env:ANDROID_HOME
    if (-not (Test-Path -LiteralPath (Join-Path $env:ANDROID_HOME 'platforms\android-37.2\android.jar'))) { throw 'Voer eerst scripts/Install-AndroidTools.ps1 uit.' }
    & .\gradlew.bat :app:testDebugUnitTest :app:lintDebug :app:assembleDebug :app:assembleRelease --no-daemon
    if ($LASTEXITCODE -ne 0) { throw 'Android-tests/lint/build mislukt.' }
    $phase6Output = Join-Path $phase6Root '.local\android-build'
    New-Item -ItemType Directory -Force -Path $phase6Output | Out-Null
    $phase6Apk = Join-Path $phase6Output 'JARVIS-Android-0.6.0-debug.apk'
    Copy-Item -LiteralPath 'app\build\outputs\apk\debug\app-debug.apk' -Destination $phase6Apk -Force
    Get-FileHash -LiteralPath $phase6Apk -Algorithm SHA256 | Format-List
} finally {
    $env:ANDROID_HOME = $phase6OldSdk
    $env:ANDROID_SDK_ROOT = $phase6OldSdkRoot
    Pop-Location
}
