"""Explicit local configuration, independent of desktop credentials and GUI."""

import os
from io import StringIO
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from dotenv import dotenv_values
from dotenv.parser import parse_stream

ROOT = Path(__file__).resolve().parents[1]


class ConfigurationError(ValueError):
    """Messages name settings only; never echo potentially secret values."""


@dataclass(frozen=True)
class Settings:
    environment: str
    host: str
    port: int
    log_level: str
    log_path: Path
    log_max_bytes: int
    log_backup_count: int
    database_path: Path
    runtime_dir: Path
    ai_provider: str
    gemini_api_key: str = field(repr=False, default="")


def load_settings(
    *, root: Path = ROOT, environ: Mapping[str, str] | None = None,
    env_file: Path | None = None,
) -> Settings:
    root = root.resolve()
    source = env_file if env_file is not None else root / ".env"
    try:
        content = source.read_text(encoding="utf-8") if source.is_file() else ""
        # python-dotenv otherwise only warns and silently skips malformed lines.
        if any(binding.error for binding in parse_stream(StringIO(content))):
            raise ConfigurationError("Invalid .env syntax")
        values = dict(dotenv_values(stream=StringIO(content), interpolate=False))
    except (OSError, UnicodeError):
        raise ConfigurationError("Cannot read .env configuration") from None
    values.update(os.environ if environ is None else environ)

    def text(name: str, default: str) -> str:
        value = values.get(name, default)
        if not isinstance(value, str) or "\0" in value:
            raise ConfigurationError(f"Invalid {name}")
        return value.strip()

    def choice(name: str, default: str, allowed: tuple[str, ...]) -> str:
        value = text(name, default).lower()
        if value not in allowed:
            raise ConfigurationError(f"Invalid {name}")
        return value

    def number(name: str, default: str, low: int, high: int) -> int:
        try:
            value = int(text(name, default))
        except ValueError:
            raise ConfigurationError(f"Invalid {name}") from None
        if not low <= value <= high:
            raise ConfigurationError(f"Invalid {name}")
        return value

    def path(name: str, default: str) -> Path:
        value = text(name, default)
        if not value or value.startswith(("\\\\", "//")) or "://" in value:
            raise ConfigurationError(f"{name} must be a local filesystem path")
        try:
            target = Path(value).expanduser()
            return (target if target.is_absolute() else root / target).resolve()
        except (OSError, ValueError):
            raise ConfigurationError(f"Invalid {name}") from None

    # Public/network binding is deliberately unavailable throughout phase 1.
    host = choice("JARVIS_HOST", "127.0.0.1", ("127.0.0.1",))
    choice("JARVIS_ENABLE_EXTERNAL_ACCESS", "false", ("false",))
    choice("JARVIS_ENABLE_AUTOMATIONS", "false", ("false",))
    database = path("JARVIS_DATABASE_PATH", ".local/data/jarvis.sqlite3")
    log_path = path("JARVIS_LOG_PATH", ".local/logs/server.log")
    if database == log_path:
        raise ConfigurationError("Database and log paths must be different")
    return Settings(
        environment=choice("JARVIS_ENV", "development", ("development", "production")),
        host=host,
        port=number("JARVIS_PORT", "8765", 1, 65535),
        log_level=choice("JARVIS_LOG_LEVEL", "info", ("debug", "info", "warning", "error", "critical")),
        log_path=log_path,
        log_max_bytes=number("JARVIS_LOG_MAX_BYTES", "1048576", 1024, 104857600),
        log_backup_count=number("JARVIS_LOG_BACKUP_COUNT", "3", 1, 10),
        database_path=database,
        runtime_dir=path("JARVIS_RUNTIME_DIR", ".local/run"),
        ai_provider=choice("JARVIS_AI_PROVIDER", "none", ("none", "gemini", "ollama")),
        gemini_api_key=text("GEMINI_API_KEY", ""),
    )
