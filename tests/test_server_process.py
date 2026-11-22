import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import pytest

from server.control import RuntimeControl, read_record

ROOT = Path(__file__).resolve().parents[1]
FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def test_runtime_lock_prevents_second_instance(settings):
    with RuntimeControl(settings) as first:
        with pytest.raises(RuntimeError, match="Another server"):
            with RuntimeControl(settings):
                pass
        assert read_record(first.path)["instance_id"] == first.record["instance_id"]
    assert not first.path.exists()


def test_unknown_runtime_record_is_preserved(settings):
    settings.runtime_dir.mkdir(parents=True)
    path = settings.runtime_dir / "server.json"
    path.write_text('{"unknown":"user data"}', encoding="utf-8")
    with pytest.raises(ValueError):
        with RuntimeControl(settings):
            pass
    assert path.read_text(encoding="utf-8") == '{"unknown":"user data"}'


def test_imports_do_not_require_gui_audio_gpu_or_ai():
    script = '''
import importlib.abc, sys
blocked = ("PyQt6", "sounddevice", "numpy", "google", "ollama", "torch", "main", "ui", "core", "dashboard", "providers", "plugins")
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == name or fullname.startswith(name + ".") for name in blocked):
            raise AssertionError("Forbidden dependency: " + fullname)
sys.meta_path.insert(0, Guard())
import server.app, server.__main__
assert not any(name == prefix or name.startswith(prefix + ".") for name in sys.modules for prefix in blocked)
'''
    result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True, creationflags=FLAGS)
    assert result.returncode == 0, result.stderr


def server_env(tmp_path, port):
    env = {key: value for key, value in os.environ.items() if not key.startswith("JARVIS_") and key != "GEMINI_API_KEY"}
    env.update({
        "JARVIS_ENV": "production", "JARVIS_PORT": str(port),
        "JARVIS_DATABASE_PATH": str(tmp_path / "server.sqlite3"),
        "JARVIS_LOG_PATH": str(tmp_path / "server.log"),
        "JARVIS_RUNTIME_DIR": str(tmp_path / "run"),
    })
    return env


def test_real_server_starts_and_stops_gracefully(tmp_path):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    env = server_env(tmp_path, port)
    with (tmp_path / "console.log").open("w", encoding="utf-8") as output:
        process = subprocess.Popen([sys.executable, "-m", "server"], cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT, creationflags=FLAGS)
        try:
            status = subprocess.run([sys.executable, "-m", "server", "status", "--wait", "10"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=15, creationflags=FLAGS)
            assert status.returncode == 0, (status.stdout, (tmp_path / "console.log").read_text())
            assert json.loads(status.stdout)["components"]["database"]
            stopped = subprocess.run([sys.executable, "-m", "server", "stop"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=15, creationflags=FLAGS)
            assert stopped.returncode == 0, stopped.stdout
            assert process.wait(timeout=10) == 0
            assert not (tmp_path / "run" / "server.json").exists()
            events = [json.loads(line)["event"] for line in (tmp_path / "server.log").read_text().splitlines()]
            assert "server_started" in events and "server_stopped" in events
        finally:
            if process.poll() is None:
                process.terminate()  # Only the exact test process created above, as failure cleanup.
                process.wait(timeout=10)


def test_invalid_cli_config_does_not_expose_values(tmp_path):
    env = server_env(tmp_path, "invalid-canary-value")
    result = subprocess.run([sys.executable, "-m", "server"], cwd=ROOT, env=env, capture_output=True, text=True, creationflags=FLAGS)
    assert result.returncode == 2
    assert "configuration_error" in result.stdout
    assert "invalid-canary-value" not in result.stdout + result.stderr
    assert not (tmp_path / "server.sqlite3").exists()


def test_console_interrupt_releases_process_ownership(settings, monkeypatch):
    from server import __main__ as entrypoint
    import uvicorn

    monkeypatch.setattr(entrypoint, "load_settings", lambda: settings)
    monkeypatch.setattr(sys, "argv", ["server", "--no-console"])

    def interrupt(self):
        raise KeyboardInterrupt

    monkeypatch.setattr(uvicorn.Server, "run", interrupt)
    assert entrypoint.main() == 0
    assert not (settings.runtime_dir / "server.json").exists()
    with RuntimeControl(settings):
        pass
