$ErrorActionPreference = 'Stop'
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    $originUrl = git remote get-url origin
    if ($LASTEXITCODE -ne 0 -or $originUrl -notmatch 'github\.com[:/]DeBeer05/jarvis(?:\.git)?/?$') {
        throw 'Origin moet eerst naar de eigen fork DeBeer05/jarvis wijzen.'
    }
    $settings = @{
        'remote.pushDefault' = 'origin'
        'remote.origin.pushurl' = 'git@github.com:DeBeer05/jarvis.git'
        'remote.upstream.pushurl' = 'no_push://upstream-read-only'
        'push.default' = 'current'
        'pull.ff' = 'only'
        'fetch.prune' = 'true'
        'branch.autoSetupMerge' = 'simple'
        'init.defaultBranch' = 'main'
        'branch.main.pushRemote' = 'origin'
        'branch.develop.pushRemote' = 'origin'
    }
    foreach ($entry in $settings.GetEnumerator()) {
        git config --local $entry.Key $entry.Value
        if ($LASTEXITCODE -ne 0) { throw "Git-configuratie mislukt: $($entry.Key)" }
    }
    # Windows already includes PowerShell 5.1; do not require a separate pwsh install.
    $branchShell = if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) { 'powershell.exe' } else { 'pwsh' }
    foreach ($typeName in @('feature', 'fix', 'hotfix', 'release')) {
        git config --local "alias.$typeName" "!$branchShell -NoProfile -File scripts/new-branch.ps1 -Type $typeName"
        if ($LASTEXITCODE -ne 0) { throw "Alias mislukt: $typeName" }
    }
    Write-Output 'Repositorylokale Git-instellingen en branchhelpers geconfigureerd.'
} finally {
    Pop-Location
}
