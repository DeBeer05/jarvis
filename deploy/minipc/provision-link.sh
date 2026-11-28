#!/usr/bin/env bash
# Input is a PUBLIC key. Private hub keys never leave their originating machine.
set -euo pipefail
read -r public_key
[[ "$public_key" =~ ^ssh-ed25519\ [A-Za-z0-9+/=]+(\ .*)?$ ]] || exit 2
if ! id jarvis-link >/dev/null 2>&1; then
 sudo -n useradd --system --create-home --shell /bin/bash jarvis-link
 # A locked account can reject public-key login on some OpenSSH/PAM setups.
 sudo -n usermod --password '*' jarvis-link
fi
sudo -n install -d -m 0755 /etc/ssh/jarvis-authorized
keyfile=/etc/ssh/jarvis-authorized/jarvis-link
sudo -n touch "$keyfile"
entry="restrict,port-forwarding,permitopen=\"127.0.0.1:11434\",permitlisten=\"127.0.0.1:18765\" $public_key"
if ! sudo -n grep -Fqx "$entry" "$keyfile"; then printf '%s\n' "$entry" | sudo -n tee -a "$keyfile" >/dev/null; fi
sudo -n chmod 0644 "$keyfile"
sudo -n tee /etc/ssh/sshd_config.d/90-jarvis-link.conf >/dev/null <<'EOF'
Match User jarvis-link
    AuthorizedKeysFile /etc/ssh/jarvis-authorized/%u
    AuthenticationMethods publickey
    PasswordAuthentication no
    KbdInteractiveAuthentication no
    AllowTcpForwarding yes
    PermitOpen 127.0.0.1:11434
    PermitListen 127.0.0.1:18765
    GatewayPorts no
    AllowAgentForwarding no
    X11Forwarding no
    PermitTTY no
    ForceCommand /bin/false
Match all
EOF
sudo -n sshd -t
sudo -n systemctl reload ssh
