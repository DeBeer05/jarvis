param([switch]$AcceptSdkLicenses, [switch]$IncludeEmulator)
$ErrorActionPreference = 'Stop'
$phase6Root = Split-Path -Parent $PSScriptRoot
$phase6Tools = Join-Path $phase6Root '.local\android-tools'
$phase6Sdk = Join-Path $phase6Tools 'sdk'
$phase6Manager = Join-Path $phase6Sdk 'cmdline-tools\latest\bin\sdkmanager.bat'
if (-not (Get-Command java -ErrorAction SilentlyContinue)) { throw 'Installeer eerst een compatibele JDK 17 of nieuwer.' }
if (-not (Test-Path -LiteralPath $phase6Manager)) {
    if (-not $AcceptSdkLicenses) { throw 'Lees de Android SDK-licentie op developer.android.com/studio en gebruik daarna -AcceptSdkLicenses.' }
    New-Item -ItemType Directory -Force -Path $phase6Tools | Out-Null
    $phase6Zip = Join-Path $phase6Tools 'command-tools.zip'
    Invoke-WebRequest -Uri 'https://dl.google.com/android/repository/commandlinetools-win-15859902_latest.zip' -OutFile $phase6Zip
    if ((Get-FileHash -LiteralPath $phase6Zip -Algorithm SHA256).Hash -ne '90AE805D20434428BFFCB699C290860F19BB5F66A67E6B330067E3DE801FB04A') { throw 'Android-tools SHA256 klopt niet.' }
    $phase6Unpacked = Join-Path $phase6Tools 'unpacked'
    Expand-Archive -LiteralPath $phase6Zip -DestinationPath $phase6Unpacked -Force
    New-Item -ItemType Directory -Force -Path (Join-Path $phase6Sdk 'cmdline-tools') | Out-Null
    $phase6Source = (Resolve-Path (Join-Path $phase6Unpacked 'cmdline-tools')).Path
    $phase6Destination = [IO.Path]::GetFullPath((Join-Path $phase6Sdk 'cmdline-tools\latest'))
    if (-not $phase6Source.StartsWith($phase6Tools, [StringComparison]::OrdinalIgnoreCase) -or -not $phase6Destination.StartsWith($phase6Tools, [StringComparison]::OrdinalIgnoreCase)) { throw 'Onverwacht SDK-pad.' }
    Move-Item -LiteralPath $phase6Source -Destination $phase6Destination
}
if ($AcceptSdkLicenses) {
    1..100 | ForEach-Object { 'y' } | & $phase6Manager --sdk_root=$phase6Sdk --licenses
    if ($LASTEXITCODE -ne 0) { throw 'SDK-licenties bevestigen mislukt.' }
}
& $phase6Manager --sdk_root=$phase6Sdk 'platform-tools' 'platforms;android-37.2' 'build-tools;36.0.0'
if ($LASTEXITCODE -ne 0) { throw 'SDK-installatie mislukt.' }
if ($IncludeEmulator) {
    & $phase6Manager --sdk_root=$phase6Sdk 'emulator' 'system-images;android-36;google_apis;x86_64'
    if ($LASTEXITCODE -ne 0) { throw 'Emulatorinstallatie mislukt.' }
}
$phase6SdkProperty = $phase6Sdk.Replace('\', '/').Replace(':', '\:')
[IO.File]::WriteAllText((Join-Path $phase6Root 'android\local.properties'), "sdk.dir=$phase6SdkProperty`n", [Text.UTF8Encoding]::new($false))
Write-Output 'Android-buildtools gereed. Geen publieke toegang, telefooninstallatie of microfoon gestart.'
