param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('feature', 'fix', 'hotfix', 'release')]
    [string]$Type,
    [Parameter(Mandatory = $true)]
    [string]$Name
)
$ErrorActionPreference = 'Stop'
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    $status = git status --porcelain
    if ($LASTEXITCODE -ne 0) { throw 'Geen bruikbare Git-repository.' }
    if ($status) { throw 'Werkmap bevat wijzigingen; eerst beoordelen en veilig afhandelen.' }
    $branchName = "$Type/$Name"
    git check-ref-format --branch $branchName | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Ongeldige branchnaam.' }
    $baseBranch = if ($Type -eq 'hotfix') { 'main' } else { 'develop' }
    git show-ref --verify --quiet "refs/heads/$baseBranch"
    if ($LASTEXITCODE -ne 0) { throw "Lokale basisbranch $baseBranch ontbreekt." }
    git switch --no-track -c $branchName $baseBranch
    if ($LASTEXITCODE -ne 0) { throw 'Branch kon niet worden aangemaakt; niets geforceerd.' }
    Write-Output "Branch $branchName gemaakt vanaf $baseBranch. Push uitsluitend naar origin."
} finally {
    Pop-Location
}
