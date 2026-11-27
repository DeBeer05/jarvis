"""Explicit encrypted SQLite backup/restore; never uploads or starts services.

Use a separate protected backup key. Restore only into a NEW empty directory.
--portable re-encrypts OAuth in the snapshot, never in the running database.
"""
import argparse
from contextlib import closing
import base64
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cryptography.fernet import Fernet
from server.automation.vault import SecretVault
from server.voice_secrets import read_secret,save_secret

MAX_BYTES=128*1024*1024


def snapshot(database):
    database=Path(database).resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix='jarvis-backup-') as directory:
        path=Path(directory)/'snapshot.sqlite3'
        with closing(sqlite3.connect(database.as_uri()+'?mode=ro',uri=True)) as source,closing(sqlite3.connect(path)) as target:
            source.backup(target)
            if target.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Database-integriteitscontrole mislukt')
        return path.read_bytes()


def portable_snapshot(raw,old_key_file=''):
    key=Fernet.generate_key()
    with tempfile.TemporaryDirectory(prefix='jarvis-portable-') as directory:
        path=Path(directory)/'snapshot.sqlite3';path.write_bytes(raw)
        with closing(sqlite3.connect(path)) as db,db:
            tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'integration_secrets' in tables:
                old=SecretVault(None,old_key_file)
                for name,ciphertext in db.execute('SELECT key,ciphertext FROM integration_secrets').fetchall():
                    value=old.crypt(ciphertext,True)
                    db.execute('UPDATE integration_secrets SET ciphertext=? WHERE key=?',(b'JARVIS-FERNET-1\0'+Fernet(key).encrypt(value),name))
            if 'integration_oauth' in tables:db.execute('DELETE FROM integration_oauth')
        return path.read_bytes(),key


def backup(database,destination,key_file,*,portable=False,old_vault_key='',includes=()):
    destination=Path(destination)
    if destination.exists():raise ValueError('Backup bestaat al')
    raw=snapshot(database)
    files={'jarvis.sqlite3':raw}
    if portable:
        files['jarvis.sqlite3'],files['vault.key']=portable_snapshot(raw,old_vault_key)
    for item in includes:
        path=Path(item)
        if path.name in files or path.is_symlink() or not path.is_file():raise ValueError('Dubbel of ongeldig aanvullend bestand')
        # Explicitly included settings/credentials remain inside the encrypted archive.
        files[path.name]=path.read_bytes()
    if sum(map(len,files.values()))>MAX_BYTES:raise ValueError('Backup te groot voor dit hulpprogramma')
    document={'version':1,'portable':portable,'files':{name:{'sha256':hashlib.sha256(value).hexdigest(),'data':base64.b64encode(value).decode()} for name,value in files.items()}}
    encrypted=Fernet(read_secret(key_file).encode()).encrypt(json.dumps(document).encode())
    descriptor=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(descriptor,'wb') as stream:stream.write(encrypted)


def restore(archive,directory,key_file):
    archive=Path(archive);directory=Path(directory)
    if archive.stat().st_size>MAX_BYTES*2:raise ValueError('Backup te groot')
    document=json.loads(Fernet(read_secret(key_file).encode()).decrypt(archive.read_bytes()))
    if document.get('version')!=1 or not isinstance(document.get('files'),dict):raise ValueError('Onbekend backupformaat')
    files={}
    for name,item in document['files'].items():
        if not name or name in ('.','..') or '/' in name or '\\' in name or ':' in name:raise ValueError('Ongeldige bestandsnaam')
        raw=base64.b64decode(item['data'],validate=True)
        if hashlib.sha256(raw).hexdigest()!=item['sha256']:raise ValueError('Backupsom klopt niet')
        files[name]=raw
    if 'jarvis.sqlite3' not in files or sum(map(len,files.values()))>MAX_BYTES:raise ValueError('Ongeldige backupinhoud')
    # Validate before creating any output. A live target is never overwritten.
    with tempfile.TemporaryDirectory(prefix='jarvis-restore-') as temp:
        probe=Path(temp)/'check.sqlite3';probe.write_bytes(files['jarvis.sqlite3'])
        with closing(sqlite3.connect(probe)) as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Ongeldige database')
    directory.mkdir(mode=0o700,parents=True,exist_ok=False)
    for name,raw in files.items():
        descriptor=os.open(directory/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(descriptor,'wb') as stream:stream.write(raw)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['keygen','backup','restore','daily'])
    parser.add_argument('--key-file',required=True)
    parser.add_argument('--database');parser.add_argument('--archive');parser.add_argument('--directory')
    parser.add_argument('--portable',action='store_true');parser.add_argument('--old-vault-key',default='')
    parser.add_argument('--include',action='append',default=[])
    args=parser.parse_args()
    try:
        if args.operation=='keygen':
            if Path(args.key_file).exists():raise ValueError('Sleutel bestaat al')
            save_secret(args.key_file,Fernet.generate_key().decode())
        elif args.operation in ('backup','daily'):
            if args.operation=='daily':
                import datetime
                if not args.directory:parser.error('--directory is verplicht')
                directory=Path(args.directory);directory.mkdir(mode=0o700,parents=True,exist_ok=True)
                args.archive=str(directory/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.enc'))
            if not args.database or not args.archive:parser.error('--database en --archive zijn verplicht')
            backup(args.database,args.archive,args.key_file,portable=args.portable,old_vault_key=args.old_vault_key,includes=args.include)
        else:
            if not args.archive or not args.directory:parser.error('--archive en --directory zijn verplicht')
            restore(args.archive,args.directory,args.key_file)
        print('Voltooid; geen gegevens verzonden of diensten gestart.')
        return 0
    except Exception:
        # Do not print values, paths or decrypted credentials from exceptions.
        print('Niet voltooid: controleer sleutel, bron, vrije ruimte en een nieuwe bestemming.',file=sys.stderr)
        return 1


if __name__=='__main__':raise SystemExit(main())
