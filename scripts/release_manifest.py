"""Verify exact, root-approved source artifacts without a production Git clone."""
import hashlib
import json
from pathlib import Path,PurePosixPath
import re


def verify(directory,commit,expected):
    directory=Path(directory).resolve(strict=True);path=directory/'release-manifest.json'
    if not re.fullmatch(r'[0-9a-f]{64}',expected) or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
        raise ValueError('Manifest differs from exact approval')
    document=json.loads(path.read_text(encoding='utf-8'))
    if document.get('schema')!=1 or document.get('commit')!=commit or not re.fullmatch(r'[0-9a-f]{40}',commit):raise ValueError('Release commit mismatch')
    entries=document.get('files')
    if not isinstance(entries,dict) or not 1<=len(entries)<=2000:raise ValueError('Invalid release manifest')
    for name,checksum in entries.items():
        relative=PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:raise ValueError('Unsafe release path')
        target=directory/relative
        if target.is_symlink() or not target.resolve(strict=True).is_relative_to(directory):raise ValueError('Unexpected source link')
        if hashlib.sha256(target.read_bytes()).hexdigest()!=checksum:raise ValueError('Source checksum mismatch')
    actual={path.relative_to(directory).as_posix() for path in directory.rglob('*') if path.is_file() and not path.relative_to(directory).parts[0]=='.venv' and '__pycache__' not in path.parts and path.name!='release-manifest.json'}
    if actual!=set(entries):raise ValueError('Unlisted release source')
    return document
