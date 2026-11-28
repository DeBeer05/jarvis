#!/usr/bin/env bash
# Prepare a pinned immutable release. No data migration or gateway cutover here.
set -euo pipefail
test "$(id -u)" = 0 || { echo 'Run with sudo.' >&2; exit 2; }
archive=${1:?Release archive}; revision=${2:?Version}; commit=${3:?Commit}; manifest=${4:?Manifest SHA256}
[[ "$revision" =~ ^[a-z0-9-]{12,80}$ && "$commit" =~ ^[a-f0-9]{40}$ && "$manifest" =~ ^[a-f0-9]{64}$ ]] || exit 2
release="/opt/jarvis/releases/$revision"
test ! -e "$release" || { echo 'Release already exists; preserve it and use a new version.' >&2; exit 2; }
apt-get update -qq
env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3-venv libgomp1
id jarvis >/dev/null 2>&1 || useradd --system --user-group --home /var/lib/jarvis --shell /usr/sbin/nologin jarvis
install -d -o root -g root -m 0755 /opt/jarvis /opt/jarvis/releases "$release"
install -d -o root -g jarvis -m 0750 /etc/jarvis
install -d -o jarvis -g jarvis -m 0700 /var/lib/jarvis /var/lib/jarvis/secrets /var/lib/jarvis/backups /var/log/jarvis
python3 - "$archive" "$release" "$commit" "$manifest" <<'PY'
import hashlib,json,sys,tarfile
from pathlib import Path,PurePosixPath
archive,target,commit,expected=sys.argv[1:];root=Path(target)
with tarfile.open(archive,'r:gz') as bundle:
    members=bundle.getmembers()
    if len(members)>2000 or sum(item.size for item in members)>200_000_000:raise ValueError('Archive limits exceeded')
    for item in members:
        path=PurePosixPath(item.name)
        if not item.isfile() or path.is_absolute() or '..' in path.parts or ':' in item.name or '\\' in item.name:raise ValueError('Unsafe archive member')
    bundle.extractall(root,filter='data')
raw=(root/'release-manifest.json').read_bytes()
if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Manifest approval mismatch')
document=json.loads(raw)
if document.get('schema')!=1 or document.get('commit')!=commit:raise ValueError('Commit approval mismatch')
entries=document['files']
for name,checksum in entries.items():
    path=PurePosixPath(name);target=root/path
    if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name or not target.resolve(strict=True).is_relative_to(root):raise ValueError('Unsafe manifest path')
    if hashlib.sha256(target.read_bytes()).hexdigest()!=checksum:raise ValueError('Source checksum mismatch')
if {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.name!='release-manifest.json'}!=set(entries):raise ValueError('Unlisted source')
PY
python3 -m venv "$release/.venv"
"$release/.venv/bin/python" -m pip install --disable-pip-version-check -r "$release/requirements-server.txt"
"$release/.venv/bin/python" -m pip check
chown -R root:root "$release"
chmod -R go-w "$release"
if ! test -e /opt/jarvis/current && ! test -L /opt/jarvis/current; then ln -s "$release" /opt/jarvis/current; fi
install -m 0644 "$release/deploy/oracle/jarvis.service" /etc/systemd/system/jarvis.service
install -m 0644 "$release/deploy/oracle/jarvis-backup.service" /etc/systemd/system/jarvis-backup.service
install -m 0644 "$release/deploy/oracle/jarvis-backup.timer" /etc/systemd/system/jarvis-backup.timer
install -m 0644 "$release/deploy/oracle/jarvis-health.service" /etc/systemd/system/jarvis-health.service
install -m 0644 "$release/deploy/oracle/jarvis-health.timer" /etc/systemd/system/jarvis-health.timer
systemd-analyze verify /etc/systemd/system/jarvis.service /etc/systemd/system/jarvis-backup.service /etc/systemd/system/jarvis-backup.timer
systemctl daemon-reload
echo "Candidate prepared: $revision. No backend started or personal data migrated."
