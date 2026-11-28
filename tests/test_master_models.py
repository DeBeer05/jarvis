import hashlib
import io
import json
import tarfile

import pytest

from scripts.install_voice_models import install


def test_model_transfer_checks_every_byte_and_preserves_existing_weights(tmp_path):
    raw=b'synthetic approved weights';name='whisper-small/model.bin'
    manifest=json.dumps({name:hashlib.sha256(raw).hexdigest()}).encode();archive=tmp_path/'models.tar'
    with tarfile.open(archive,'w') as bundle:
        for path,data in [(name,raw),('models-manifest.json',manifest)]:
            entry=tarfile.TarInfo(path);entry.size=len(data);bundle.addfile(entry,io.BytesIO(data))
    expected=hashlib.sha256(manifest).hexdigest();target=tmp_path/'models'
    assert install(archive,target,expected)==1 and install(archive,target,expected)==1
    (target/name).write_bytes(b'existing different weights')
    with pytest.raises(ValueError,match='preserved'):install(archive,target,expected)
