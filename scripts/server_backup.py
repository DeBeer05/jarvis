"""Encrypted cloud backup with only configured existing credential files."""
import argparse
from datetime import datetime,UTC
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dotenv import dotenv_values
from scripts.cloud_backup import backup


def create(environment,directory,key_file):
    environment=Path(environment).resolve(strict=True)
    settings=dotenv_values(environment,interpolate=False)
    database=settings.get('JARVIS_DATABASE_PATH')
    if not database:raise ValueError('Database path is required')
    includes=[environment]
    for name in ('JARVIS_VAULT_KEY_FILE','ELEVENLABS_API_KEY_FILE','JARVIS_GOOGLE_CLIENT_FILE'):
        value=settings.get(name)
        if value and Path(value).is_file():includes.append(Path(value))
    directory=Path(directory);directory.mkdir(mode=0o700,parents=True,exist_ok=True)
    destination=directory/(datetime.now(UTC).strftime('%Y%m%dT%H%M%S.%fZ')+'.enc')
    backup(database,destination,key_file,includes=includes)
    return destination


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--environment',default='/etc/jarvis/server.env')
    parser.add_argument('--directory',default='/var/lib/jarvis/backups');parser.add_argument('--key-file',default='/etc/jarvis/backup.key');args=parser.parse_args()
    print('Encrypted backup created:',create(args.environment,args.directory,args.key_file).name)
