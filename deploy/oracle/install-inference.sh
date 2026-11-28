#!/usr/bin/env bash
# Existing ARM64 VM only. No cloud resource creation or public inference port.
set -euo pipefail
test "$(uname -m)" = aarch64
version=v0.40.19
sha=29e1dd8826628d73c49655b497c70cb3f3c40f7d0d43ca8f8a150a4e6e4dbc72
base=/opt/jarvis-ai/ollama/$version
sudo -n apt-get update -qq
sudo -n env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends curl ca-certificates zstd python3-venv
sudo -n install -d -m 0755 "$base"
if ! test -x "$base/bin/ollama"; then
    archive=$(mktemp /tmp/jarvis-ollama.XXXXXX.tar.zst)
    trap 'rm -f "$archive"' EXIT
    curl --fail --location --retry 2 --proto '=https' --tlsv1.2 "https://github.com/ollama/ollama/releases/download/$version/ollama-linux-arm64.tar.zst" -o "$archive"
    printf '%s  %s\n' "$sha" "$archive" | sha256sum --check --status
    sudo -n tar --zstd -xf "$archive" -C "$base"
fi
if ! id jarvis-ai >/dev/null 2>&1; then sudo -n useradd --system --home-dir /var/lib/jarvis-ai --shell /usr/sbin/nologin jarvis-ai; fi
sudo -n install -d -m 0700 -o jarvis-ai -g jarvis-ai /var/lib/jarvis-ai /var/lib/jarvis-ai/models
sudo -n tee /etc/systemd/system/jarvis-inference.service >/dev/null <<EOF
[Unit]
Description=JARVIS private ARM64 AI inference
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=300
StartLimitBurst=10
[Service]
User=jarvis-ai
Group=jarvis-ai
ExecStart=$base/bin/ollama serve
Environment=HOME=/var/lib/jarvis-ai
Environment=OLLAMA_HOST=127.0.0.1:11434
Environment=OLLAMA_MODELS=/var/lib/jarvis-ai/models
Environment=OLLAMA_NUM_PARALLEL=1
Environment=OLLAMA_MAX_LOADED_MODELS=1
Environment=OLLAMA_MAX_QUEUE=4
Environment=OLLAMA_CONTEXT_LENGTH=4096
Environment=OLLAMA_KEEP_ALIVE=30m
Environment=OLLAMA_NO_CLOUD=1
Restart=on-failure
RestartSec=3
MemoryMax=9G
TasksMax=256
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/jarvis-ai
UMask=0077
[Install]
WantedBy=multi-user.target
EOF
sudo -n systemctl daemon-reload
sudo -n systemctl enable --now jarvis-inference.service
for attempt in $(seq 1 30); do
    if curl --fail --silent http://127.0.0.1:11434/api/version; then echo; exit 0; fi
    sleep 1
done
echo 'Inference failed readiness; inspect journalctl -u jarvis-inference' >&2
exit 1
