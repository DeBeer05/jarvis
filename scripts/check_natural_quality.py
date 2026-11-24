"""Reproducible lint/type checks for phase 7.5 without loading models or accounts."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
SERVER=["server/natural","server/ai/policy.py","providers/voice_pipe.py"]
CLIENT=["desktop-client/jarvis_client/voice/echo.py","desktop-client/jarvis_client/voice/manager.py",
        "desktop-client/jarvis_client/voice/audio.py","desktop-client/jarvis_client/voice/server_worker.py",
        "desktop-client/jarvis_client/voice/session.py"]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-python",help="Also check voice adapters against this isolated client environment")
    args=parser.parse_args()
    lint=[*SERVER,"server/automation/chat.py","server/automation/chat_approval.py",
          "desktop-client/jarvis_client/voice","desktop-client/jarvis_client/natural_settings.py",
          "desktop-client/tests/test_barge_in.py",*(str(path.relative_to(ROOT)) for path in sorted((ROOT/"tests").glob("test_natural*.py")))]
    commands=[[sys.executable,"-m","ruff","check",*lint],
              [sys.executable,"-m","mypy","--check-untyped-defs","--ignore-missing-imports","--follow-imports","silent",*SERVER]]
    if args.client_python:commands.append([sys.executable,"-m","mypy","--check-untyped-defs","--ignore-missing-imports","--follow-imports","silent","--python-executable",args.client_python,*CLIENT])
    for command in commands:
        result=subprocess.run(command,cwd=ROOT,check=False)
        if result.returncode:return result.returncode
    return 0


if __name__=="__main__":raise SystemExit(main())
