"""Local process ownership and authenticated graceful shutdown, never PID killing."""

import json
import os
import re
import secrets
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from server.config import Settings


def read_record(path: Path) -> dict:
    if path.stat().st_size > 8192:
        raise ValueError("Invalid runtime record")
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise ValueError("Invalid runtime record")
    if (
        record.get("service") != "jarvis-server" or record.get("host") != "127.0.0.1"
        or type(record.get("port")) is not int or not 1 <= record["port"] <= 65535
        or type(record.get("pid")) is not int or record["pid"] <= 0
        or not isinstance(record.get("instance_id"), str)
        or re.fullmatch(r"[a-f0-9]{32}", record["instance_id"]) is None
        or not isinstance(record.get("token"), str)
        or re.fullmatch(r"[A-Za-z0-9_-]{32,128}", record["token"]) is None
    ):
        raise ValueError("Invalid runtime record")
    return record


class RuntimeControl:
    def __init__(self, settings: Settings):
        self.directory = settings.runtime_dir
        self.path = self.directory / "server.json"
        self.record = {
            "service": "jarvis-server", "pid": os.getpid(),
            "host": settings.host, "port": settings.port,
            "instance_id": secrets.token_hex(16), "token": secrets.token_urlsafe(32),
        }
        self.lock = None

    def __enter__(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        self.lock = (self.directory / "server.lock").open("a+b")
        if self.lock.seek(0, 2) == 0:
            self.lock.write(b"0")
            self.lock.flush()
        self.lock.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.lock.close()
            self.lock = None
            raise RuntimeError("Another server owns this runtime directory") from None
        try:
            if self.path.exists():
                read_record(self.path)  # Refuse to overwrite unknown user files.
            descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(self.record, stream)
        except Exception:
            self.lock.close()
            self.lock = None
            raise
        return self

    def __exit__(self, *args):
        try:
            if self.path.exists() and read_record(self.path)["instance_id"] == self.record["instance_id"]:
                self.path.unlink()
        finally:
            if self.lock is not None:
                self.lock.close()  # OS releases the advisory lock, including after a crash.


def _request(record: dict, path: str, *, shutdown: bool = False) -> dict:
    request = Request(
        f"http://127.0.0.1:{record['port']}{path}",
        method="POST" if shutdown else "GET",
        headers={"Authorization": "Bearer " + record["token"]} if shutdown else {},
    )
    # Never send local control tokens through environment-configured HTTP proxies.
    with build_opener(ProxyHandler({})).open(request, timeout=1) as response:
        return json.load(response)


def inspect_server(settings: Settings) -> tuple[dict, dict]:
    record = read_record(settings.runtime_dir / "server.json")
    status = _request(record, "/api/v1/status")
    if status.get("instance_id") != record["instance_id"] or status.get("service") != "jarvis-server":
        raise ValueError("Server instance does not match runtime record")
    return record, status


def control_command(settings: Settings, command: str, wait: float = 0) -> int:
    deadline = time.monotonic() + (wait if wait else (10 if command == "stop" else 0))
    while True:
        try:
            record, status = inspect_server(settings)
            break
        except (OSError, ValueError, URLError, HTTPError):
            if command != "status" or time.monotonic() >= deadline:
                print(json.dumps({"status": "not_running", "service": "jarvis-server"}))
                return 1
            time.sleep(0.1)
    if command == "status":
        print(json.dumps(status))
        return 0
    try:
        _request(record, "/internal/shutdown", shutdown=True)
        while time.monotonic() < deadline:
            if not (settings.runtime_dir / "server.json").exists():
                print(json.dumps({"status": "stopped", "service": "jarvis-server"}))
                return 0
            time.sleep(0.1)
    except (OSError, ValueError, URLError, HTTPError):
        pass
    print(json.dumps({"status": "stop_failed", "service": "jarvis-server"}))
    return 1
