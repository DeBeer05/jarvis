"""Rebuild/check the synthetic Android settings contract without accounts or models."""
import argparse
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from server.natural.models import UserSettings
from server.natural.settings import SettingsManager


def contract():
    capabilities={"runtime_installed":True,"stt_providers":["whisper"],
        "tts_providers":["piper"],"whisper_models":{"whisper-small":True,
        "whisper-base":False,"whisper-tiny":False},"voices":{"ronnie":True,"mls":True},
        "cuda":"not_verified","speaker_verification":False}
    with patch("server.natural.capabilities.voice_capabilities",return_value=capabilities):
        schema=SettingsManager.schema()
    return {"schema":schema,"document":{"revision":0,"settings":UserSettings().model_dump(mode="json")}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    target=ROOT/"android/app/src/androidTest/assets/natural-settings-contract.json"
    document=contract()
    if args.check:
        if json.loads(target.read_text(encoding="utf-8"))!=document:
            raise SystemExit("Android settings contract is stale; run scripts/export_natural_contract.py")
        print("Android settings contract matches the backend.")
    else:
        target.write_text(json.dumps(document,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":main()
