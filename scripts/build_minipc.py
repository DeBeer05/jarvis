"""Reproducible headless distribution. Only an explicit source allowlist is copied."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]
TREES=('server','providers')
FILES=('requirements-server.txt','constraints-server.txt','LICENSE','config/jarvis-system-prompt.txt','config/jarvis-voice-system-prompt.txt','requirements-voice-server.txt','constraints-voice.txt')
SCRIPTS=('cloud_backup.py','download-voice-models.py','minipc_admin.py')

def build(destination,site_config=None):
    destination=Path(destination).resolve()
    # Refuse to overwrite arbitrary directories or mix an older package with this build.
    if destination.exists():raise ValueError('Use a new empty output directory')
    destination.mkdir(parents=True)
    payload=destination/'payload';payload.mkdir()
    for tree in TREES:
        for source in (ROOT/tree).rglob('*.py'):
            if '__pycache__' not in source.parts:
                target=payload/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    for source in (ROOT/'desktop-client/voice_runtime').rglob('*.py'):
        target=payload/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    target=payload/'desktop-client/voice_worker.py';shutil.copy2(ROOT/'desktop-client/voice_worker.py',target)
    for name in FILES:
        target=payload/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
    for name in SCRIPTS:
        target=payload/'scripts'/name;target.parent.mkdir(exist_ok=True);shutil.copy2(ROOT/'scripts'/name,target)
    for source in (ROOT/'server/static').rglob('*'):
        if source.is_file():
            target=payload/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    for source in (ROOT/'deploy/minipc').iterdir():
        if source.is_file():shutil.copy2(source,destination/source.name)
    if site_config:
        site=json.loads(Path(site_config).read_text(encoding='utf-8-sig'))
        if set(site)!={'host','host_public_key','gateway'}:raise ValueError('Only public connection metadata is allowed')
        (destination/'oracle-connection.json').write_text(json.dumps(site,indent=2),encoding='utf-8')
    version=subprocess.check_output(['git','rev-parse','--short=12','HEAD'],cwd=ROOT,text=True).strip()
    entries={str(file.relative_to(payload)).replace('\\','/'):hashlib.sha256(file.read_bytes()).hexdigest() for file in payload.rglob('*') if file.is_file()}
    content=hashlib.sha256(json.dumps(entries,sort_keys=True).encode()).hexdigest()[:12]
    manifest={'schema':1,'version':version+'-'+content,'files':entries}
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    archive=destination.with_suffix('.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as zipped:
        for file in destination.rglob('*'):
            if file.is_file():zipped.write(file,Path(destination.name)/file.relative_to(destination))
    return archive

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='dist/JARVIS-MiniPC');parser.add_argument('--site-config');args=parser.parse_args()
    print(build(args.output,args.site_config))
