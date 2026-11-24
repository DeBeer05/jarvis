"""Installed voice capabilities only; no imports/downloads of inference engines."""
import os
from pathlib import Path


def voice_capabilities():
    models=Path(os.environ.get("LOCALAPPDATA",str(Path.home()/".local/share")))/"JARVIS/Desktop/models"
    stt={name:all((models/name/file).is_file() for file in ("model.bin","config.json","tokenizer.json","vocabulary.txt")) for name in ("whisper-small","whisper-base","whisper-tiny")}
    voices={}
    for name,relative in (("ronnie","piper-ronnie/nl_NL-ronnie-medium.onnx"),("mls","piper/nl_NL-mls-medium.onnx")):
        path=models/relative;voices[name]=path.is_file() and path.with_suffix(".onnx.json").is_file()
    root=Path(__file__).resolve().parents[2]
    runtime=any((root/path).is_file() for path in (".local/voice-venv/Scripts/python.exe",".local/voice-venv/bin/python"))
    return {"runtime_installed":runtime,"stt_providers":["whisper"],"tts_providers":["piper"],"whisper_models":stt,"voices":voices,"cuda":"not_verified","speaker_verification":False}
