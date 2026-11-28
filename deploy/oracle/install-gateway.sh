#!/usr/bin/env bash
# Public TLS gateway only; no personal database or inference API is exposed.
set -euo pipefail
hostname=${1:?Pass a public hostname}
[[ "$hostname" =~ ^[a-z0-9][a-z0-9.-]+$ ]] || exit 2
sudo -n apt-get update -qq
sudo -n env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends debian-keyring debian-archive-keyring apt-transport-https curl gnupg
if ! test -f /usr/share/keyrings/caddy-stable-archive-keyring.gpg; then
 curl --fail --silent --show-error --proto '=https' https://dl.cloudsmith.io/public/caddy/stable/gpg.key | sudo -n gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
fi
curl --fail --silent --show-error --proto '=https' https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt | sudo -n tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
sudo -n chmod o+r /usr/share/keyrings/caddy-stable-archive-keyring.gpg
sudo -n apt-get update -qq
sudo -n env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends caddy
if test -f /etc/caddy/Caddyfile && ! test -f /etc/caddy/Caddyfile.pre-jarvis; then sudo -n cp -p /etc/caddy/Caddyfile /etc/caddy/Caddyfile.pre-jarvis; fi
sudo -n tee /etc/caddy/Caddyfile >/dev/null <<EOF
{
    admin localhost:2019
}
$hostname {
    @internal path /internal /internal/*
    respond @internal 404
    header {
        -Server
        X-Content-Type-Options nosniff
        Referrer-Policy no-referrer
        Strict-Transport-Security "max-age=31536000"
    }
    request_body {
        max_size 12MB
    }
    reverse_proxy 127.0.0.1:18765 {
        header_up Host $hostname
        header_up X-Forwarded-Proto https
        header_up X-Forwarded-For {remote_host}
        flush_interval -1
        transport http {
            dial_timeout 3s
        }
    }
}
EOF
sudo -n caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
sudo -n install -d /etc/systemd/system/caddy.service.d
sudo -n tee /etc/systemd/system/caddy.service.d/jarvis-restart.conf >/dev/null <<'EOF'
[Unit]
StartLimitIntervalSec=300
StartLimitBurst=10
[Service]
Restart=on-failure
RestartSec=3
EOF
sudo -n systemctl daemon-reload
sudo -n systemctl enable caddy
sudo -n systemctl reload-or-restart caddy
# Insert only these ports before the existing reject. Preserve SSH and all rules.
for port in 80 443; do
 sudo -n iptables -C INPUT -p tcp --dport "$port" -j ACCEPT 2>/dev/null || sudo -n iptables -I INPUT 1 -p tcp --dport "$port" -j ACCEPT
done
if test -d /etc/iptables; then sudo -n sh -c 'iptables-save > /etc/iptables/rules.v4'; fi
sudo -n systemctl is-active caddy
