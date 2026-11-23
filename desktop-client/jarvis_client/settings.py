import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlsplit


def endpoint(value):
    if not isinstance(value, str):
        raise ValueError("Ongeldig serveradres.")
    value = value.strip().rstrip("/")
    try:
        url = urlsplit(value)
        if url.username or url.password or url.query or url.fragment or url.path or not url.hostname:
            raise ValueError
        if url.scheme != "https" and not (url.scheme == "http" and url.hostname in ("127.0.0.1", "localhost", "::1")):
            raise ValueError
        if not 1 <= (url.port or (443 if url.scheme == "https" else 80)) <= 65535:
            raise ValueError
    except ValueError:
        raise ValueError("Gebruik een HTTPS-origin of http://127.0.0.1:8765, zonder pad of credentials.") from None
    return value


def data_directory():
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local/share"))) / "JARVIS" / "Desktop"


@dataclass
class Preferences:
    local_url: str = "http://127.0.0.1:8765"
    remote_url: str = ""
    connection_mode: str = "local"
    auto_connect: bool = True
    minimize_to_tray: bool = True
    notifications: bool = True
    notify_answers: bool = False
    startup: bool = False
    theme: str = "dark"
    language: str = "nl"
    provider: str = "auto"
    log_level: str = "warning"

    def validate(self):
        self.local_url = endpoint(self.local_url)
        if self.remote_url:
            self.remote_url = endpoint(self.remote_url)
            if urlsplit(self.remote_url).scheme != "https":
                raise ValueError("Het externe profiel vereist HTTPS.")
        if self.connection_mode not in ("local", "remote", "auto") or self.connection_mode == "remote" and not self.remote_url:
            raise ValueError("Kies een geldig verbindingsprofiel en serveradres.")
        if self.provider not in ("auto", "gemini", "groq", "ollama") or self.theme not in ("dark", "light") or self.language not in ("nl", "en") or self.log_level not in ("warning", "info", "debug"):
            raise ValueError("Ongeldige instelling.")
        for key in ("auto_connect", "minimize_to_tray", "notifications", "notify_answers", "startup"):
            if type(getattr(self, key)) is not bool:
                raise ValueError("Ongeldige schakelaar.")
        return self

    def candidates(self):
        self.validate()
        if self.connection_mode == "remote":
            return [self.remote_url]
        if self.connection_mode == "auto":
            return list(dict.fromkeys(url for url in (self.local_url, self.remote_url) if url))
        return [self.local_url]


class SettingsStore:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory else data_directory()
        self.path = self.directory / "settings.json"

    def load(self):
        if not self.path.exists():
            return Preferences()
        try:
            body = json.loads(self.path.read_text(encoding="utf-8"))
            return Preferences(**body).validate()
        except (OSError, ValueError, TypeError):
            raise ValueError("Instellingen zijn onleesbaar. Herstel settings.json; het bestand is behouden.") from None

    def save(self, preferences):
        preferences.validate()
        self.directory.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(preferences), indent=2), encoding="utf-8")
        temporary.replace(self.path)
