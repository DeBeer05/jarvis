"""Explicit installation of approved Supertonic 3 assets; no runtime downloads."""
import hashlib
import json
import os
from pathlib import Path
import urllib.request

REPOSITORY='supertone-oss-archive/supertonic-3'
REVISION='aafc6e32416a594460b32413efc49d7fe4ce6d46'
MODELS={'duration_predictor.onnx':'c3eb91414d5ff8a7a239b7fe9e34e7e2bf8a8140d8375ffb14718b1c639325db','text_encoder.onnx':'c7befd5ea8c3119769e8a6c1486c4edc6a3bc8365c67621c881bbb774b9902ff','vector_estimator.onnx':'883ac868ea0275ef0e991524dc64f16b3c0376efd7c320af6b53f5b780d7c61c','vocoder.onnx':'085de76dd8e8d5836d6ca66826601f615939218f90e519f70ee8a36ed2a4c4ba'}


def main():
    import argparse
    parser=argparse.ArgumentParser(description='Download circa 400 MB Supertonic 3 only with explicit consent.')
    parser.add_argument('--consent-download',action='store_true');options=parser.parse_args()
    if not options.consent_download:parser.error('Read the size/license in docs/TTS_PROVIDERS.md and explicitly pass --consent-download')
    root=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.local/share')))/'JARVIS/Desktop/models/supertonic-3'
    for folder,files in [('onnx',list(MODELS)+['tts.json','unicode_indexer.json']),('voice_styles',[f'M{i}.json' for i in range(1,6)]),('', ['LICENSE','README.md'])]:
        for name in files:
            relative=(folder+'/' if folder else '')+name;target=root/relative;target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists() and (name not in MODELS or hashlib.sha256(target.read_bytes()).hexdigest()==MODELS[name]):continue
            data=urllib.request.urlopen(f'https://huggingface.co/{REPOSITORY}/resolve/{REVISION}/{relative}',timeout=60).read(300_000_001)
            if len(data)>300_000_000:raise ValueError('Unexpected asset size')
            if name in MODELS and hashlib.sha256(data).hexdigest()!=MODELS[name]:raise ValueError('Model checksum mismatch')
            temporary=target.with_suffix(target.suffix+'.part');temporary.write_bytes(data);temporary.replace(target)
            print(relative,len(data),flush=True)
    (root/'installation.json').write_text(json.dumps({'repository':REPOSITORY,'revision':REVISION,'verified_models':MODELS}),encoding='utf-8')


if __name__=='__main__':main()
