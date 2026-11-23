"""No microphone, network or model download: packaged helper import smoke."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory(prefix="jarvis-voice-smoke-") as directory:
    requests = [{"operation": "tts", "text": "Een synthetische test.", "models": directory, "voice": "ronnie"},
                {"operation": "stt", "audio": "", "models": directory}]
    result = subprocess.run([str(Path(sys.argv[1]).resolve())], input="".join(json.dumps(request) + "\n" for request in requests),
                            capture_output=True, text=True, timeout=30, check=True,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    parsed = [json.loads(line) for line in result.stdout.splitlines()]
    if parsed != [{"ok": False, "code": "tts_model_missing"}, {"ok": False, "code": "stt_model_missing"}]:
        raise RuntimeError("Packaged voice imports or missing-model handling failed")
    if list(Path(directory).iterdir()):
        raise RuntimeError("Unexpected model downloads")
print("Packaged speech helper imports work; missing model handled without download.")
