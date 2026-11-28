import hashlib
import json
from pathlib import Path
import tarfile

import pytest

from scripts.build_oracle import build
from scripts.release_manifest import verify


def test_cloud_release_reuses_allowlist_and_exact_approval(tmp_path):
    archive=tmp_path/'release.tar.gz';result=build(archive);release=tmp_path/'release';release.mkdir()
    with tarfile.open(archive) as bundle:
        names=bundle.getnames()
        assert 'server/app.py' in names and 'scripts/server_backup.py' in names
        assert not any(Path(name).name in ('.env','private.key','jarvis.sqlite3') for name in names)
        bundle.extractall(release,filter='data')
    assert verify(release,result['commit'],result['manifest_sha256'])['version']==result['version']
    (release/'server/app.py').write_text('tampered',encoding='utf-8')
    with pytest.raises(ValueError,match='checksum'):verify(release,result['commit'],result['manifest_sha256'])


def test_manifest_cannot_escape_release(tmp_path):
    manifest={'schema':1,'commit':'a'*40,'files':{'../escape.py':'b'*64}}
    raw=json.dumps(manifest).encode();(tmp_path/'release-manifest.json').write_bytes(raw)
    with pytest.raises(ValueError,match='Unsafe'):verify(tmp_path,'a'*40,hashlib.sha256(raw).hexdigest())
