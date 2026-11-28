param([string]$InstallRoot="$env:ProgramData\JARVIS")
$ErrorActionPreference='Stop'
$link=Get-Content "$InstallRoot\data\oracle-link.json" -Raw | ConvertFrom-Json
# Keep both ends loopback-only. SSH authenticates and encrypts every byte.
& ssh -N -T -i $link.key -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o "UserKnownHostsFile=$($link.known)" -o HostKeyAlgorithms=ssh-ed25519 -o ExitOnForwardFailure=yes -o ServerAliveInterval=20 -o ServerAliveCountMax=3 -L '127.0.0.1:11435:127.0.0.1:11434' -R '127.0.0.1:18765:127.0.0.1:8765' "jarvis-link@$($link.host)"
exit $LASTEXITCODE
