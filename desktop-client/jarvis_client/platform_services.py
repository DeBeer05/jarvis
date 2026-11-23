"""Explicit local capabilities; never execute model output or arbitrary commands."""
import os
import platform
import sys
import time
from pathlib import Path


class LocalAgent:
    ALLOWED = frozenset(("system_info",))

    def run(self, action, grants):
        if action not in self.ALLOWED or action not in grants:
            raise PermissionError("Deze lokale actie is niet toegestaan.")
        return {"os": platform.system(), "release": platform.release(), "architecture": platform.machine(), "cpu_threads": os.cpu_count()}


class NotificationCenter:
    def __init__(self, deliver, *, clock=time.monotonic):
        self.deliver, self.clock = deliver, clock
        self.enabled, self.answers = True, False
        self.previous = {}
        self.items = []

    def publish(self, kind, text):
        now = self.clock()
        if now - self.previous.get(kind, -1000) < 60:
            return False
        self.previous[kind] = now
        self.items.insert(0, (time.time(), text))
        self.items = self.items[:100]
        if self.enabled and (kind != "answer" or self.answers):
            self.deliver("JARVIS", text)
        return True


class Startup:
    NAME = "JARVISDesktop"
    KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

    @staticmethod
    def command():
        if getattr(sys, "frozen", False):
            return '"' + sys.executable + '" --minimized'
        launcher = Path(__file__).resolve().parents[1] / "run_client.py"
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        return '"' + str(pythonw) + '" "' + str(launcher) + '" --minimized'

    @classmethod
    def set_enabled(cls, enabled):
        if os.name != "nt":
            if enabled:
                raise OSError("Automatisch starten is alleen beschikbaar op Windows.")
            return
        import winreg
        # Only our own per-user Run value; never admin privileges or server startup.
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, cls.KEY) as key:
            if enabled:
                winreg.SetValueEx(key, cls.NAME, 0, winreg.REG_SZ, cls.command())
            else:
                try:
                    winreg.DeleteValue(key, cls.NAME)
                except FileNotFoundError:
                    pass
