"""Install only explicitly transferred model bytes with a pinned manifest."""
import argparse
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import re
import tarfile
import uuid

ALLOWED=frozenset(('whisper-small','piper','piper-ronnie','supertonic-3'))


def install(archive,directory,expected):
    if not re.fullmatch('[a-f0-9]{64}',expected):raise ValueError('Expected model manifest required')
    directory=Path(directory).resolve();directory.mkdir(mode=0o755,parents=True,exist_ok=True)
    with tarfile.open(archive,'r') as bundle:
        members=bundle.getmembers()
        if len(members)>2000 or sum(item.size for item in members)>2_000_000_000:raise ValueError('Model archive limits exceeded')
        raw=bundle.extractfile('models-manifest.json').read(1000000)
        if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Model manifest mismatch')
        entries=json.loads(raw)
        if {item.name for item in members}!={*entries,'models-manifest.json'}:raise ValueError('Unlisted model data')
        for item in members:
            if item.name=='models-manifest.json':continue
            relative=PurePosixPath(item.name)
            if not item.isfile() or relative.is_absolute() or '..' in relative.parts or '\\' in item.name or relative.parts[0] not in ALLOWED:raise ValueError('Unsafe model path')
            target=directory/relative
            if not target.resolve().is_relative_to(directory) or target.is_symlink():raise ValueError('Unexpected model link')
            if target.exists():
                with target.open('rb') as source:actual=hashlib.file_digest(source,'sha256').hexdigest()
                if actual!=entries[item.name]:raise ValueError('Existing model differs; preserved without overwrite')
                continue
            target.parent.mkdir(mode=0o755,parents=True,exist_ok=True)
            temporary=target.with_name(target.name+'.incoming-'+str(uuid.uuid4()))
            checksum=hashlib.sha256()
            try:
                with bundle.extractfile(item) as source,temporary.open('xb') as output:
                    while block:=source.read(1048576):checksum.update(block);output.write(block)
                if checksum.hexdigest()!=entries[item.name]:raise ValueError('Model checksum mismatch')
                temporary.chmod(0o644);temporary.replace(target)
            finally:temporary.unlink(missing_ok=True)
    return len(entries)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--archive',required=True);parser.add_argument('--directory',default='/opt/jarvis/models');parser.add_argument('--manifest-sha256',required=True);args=parser.parse_args()
    if os.name!='posix' or os.geteuid()!=0:parser.error('Run installation as root on the prepared Linux host')
    print('Verified existing model files:',install(args.archive,args.directory,args.manifest_sha256))
