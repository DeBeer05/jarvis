"""Build the existing headless payload into a verifiable Oracle release."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_minipc import build as build_minipc


def build(destination):
    destination=Path(destination).resolve()
    if destination.exists():raise ValueError('Release archive already exists')
    destination.parent.mkdir(parents=True,exist_ok=True)
    staging=ROOT/'.local/oracle-build';staging.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=staging) as temporary:
        temporary=Path(temporary);build_minipc(temporary/'package')
        release=temporary/'release';shutil.copytree(temporary/'package/payload',release)
        for name in ('deploy_release.py','release_manifest.py','cloud_health.py','server_backup.py'):
            source=ROOT/'scripts'/name
            if source.is_file():shutil.copy2(source,release/'scripts'/name)
        shutil.copytree(ROOT/'deploy/oracle',release/'deploy/oracle')
        entries={str(path.relative_to(release)).replace('\\','/'):hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(release.rglob('*')) if path.is_file()}
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        content=hashlib.sha256(json.dumps(entries,sort_keys=True).encode()).hexdigest()[:12]
        manifest={'schema':1,'commit':commit,'version':commit[:12]+'-'+content,'files':entries}
        manifest_raw=json.dumps(manifest,indent=2).encode()
        (release/'release-manifest.json').write_bytes(manifest_raw)
        with tarfile.open(destination,'w:gz') as archive:
            for path in sorted(release.rglob('*')):
                if path.is_symlink():raise ValueError('Release symlinks are not permitted')
                if path.is_file():archive.add(path,arcname=str(path.relative_to(release)).replace('\\','/'),recursive=False)
    return {'archive':str(destination),'manifest_sha256':hashlib.sha256(manifest_raw).hexdigest(),'version':manifest['version'],'commit':commit}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    print(json.dumps(build(args.output)))
