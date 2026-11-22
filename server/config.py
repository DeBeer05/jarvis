"""Explicit local configuration, independent of desktop credentials and GUI."""

import os
from io import StringIO
from dataclasses import dataclass, field
from pathlib import Path
import re
from urllib.parse import urlsplit
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
    profile: str = "desktop-development"
    preferred_provider: str = "gemini"
    gemini_model: str = "gemini-3.8-flash"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:0.6b"
    system_prompt: str = field(repr=False, default="")
    ai_timeout_seconds: int = 60
    provider_timeout_seconds: int = 25
    max_concurrent_ai: int = 2
    max_message_chars: int = 8000
    max_context_chars: int = 24000
    max_output_tokens: int = 1024
    max_response_chars: int = 16000
    requests_per_minute: int = 30
    max_conversations: int = 100
    max_turns: int = 100


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

    # Public/network binding stays unavailable in phase 2.
    host = choice("JARVIS_HOST", "127.0.0.1", ("127.0.0.1",))
    choice("JARVIS_ENABLE_EXTERNAL_ACCESS", "false", ("false",))
    choice("JARVIS_ENABLE_AUTOMATIONS", "false", ("false",))
    database = path("JARVIS_DATABASE_PATH", ".local/data/jarvis.sqlite3")
    log_path = path("JARVIS_LOG_PATH", ".local/logs/server.log")
    if database == log_path:
        raise ConfigurationError("Database and log paths must be different")
    profile = choice("JARVIS_PROFILE", "desktop-development", ("desktop-development", "mini-pc-production"))
    mini = profile == "mini-pc-production"
    provider = choice("JARVIS_AI_PROVIDER", "auto", ("auto", "none", "gemini", "ollama"))
    base_url = text("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    try:
        url = urlsplit(base_url)
        if url.scheme not in ("http", "https") or url.hostname not in ("127.0.0.1", "localhost", "::1") or url.username or url.password or url.path or url.query or url.fragment or not 1 <= (url.port or 80) <= 65535:
            raise ValueError
    except ValueError:
        raise ConfigurationError("OLLAMA_BASE_URL must be a loopback HTTP(S) origin without credentials") from None
    if url.hostname == "localhost":
        base_url = base_url.replace("localhost", "127.0.0.1", 1)

    def model(name: str, default: str) -> str:
        value = text(name, default)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}", value):
            raise ConfigurationError(f"Invalid {name}")
        return value

    prompt_file = path("JARVIS_SYSTEM_PROMPT_FILE", str(ROOT / "config/jarvis-system-prompt.txt"))
    try:
        prompt = text("JARVIS_SYSTEM_PROMPT", "") or prompt_file.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        raise ConfigurationError("Cannot read JARVIS_SYSTEM_PROMPT_FILE") from None
    if not prompt or len(prompt) > 12000:
        raise ConfigurationError("Invalid JARVIS_SYSTEM_PROMPT")
    return Settings(
        environment=choice("JARVIS_ENV", "production" if mini else "development", ("development", "production")),
        host=host,
        port=number("JARVIS_PORT", "8765", 1, 65535),
        log_level=choice("JARVIS_LOG_LEVEL", "warning" if mini else "info", ("debug", "info", "warning", "error", "critical")),
        log_path=log_path,
        log_max_bytes=number("JARVIS_LOG_MAX_BYTES", "1048576", 1024, 104857600),
        log_backup_count=number("JARVIS_LOG_BACKUP_COUNT", "3", 1, 10),
        database_path=database,
        runtime_dir=path("JARVIS_RUNTIME_DIR", ".local/run"),
        ai_provider="auto" if provider == "none" else provider,
        gemini_api_key=text("GEMINI_API_KEY", ""),
        profile=profile,
        preferred_provider=choice("JARVIS_AI_PREFERRED_PROVIDER", "gemini", ("gemini", "ollama")),
        gemini_model=model("GEMINI_MODEL", "gemini-3.8-flash"),
        ollama_base_url=base_url,
        ollama_model=model("OLLAMA_MODEL", "qwen3:0.6b"),
        system_prompt=prompt,
        ai_timeout_seconds=number("JARVIS_AI_TIMEOUT_SECONDS", "60", 1, 180),
        provider_timeout_seconds=number("JARVIS_PROVIDER_TIMEOUT_SECONDS", "25", 1, 120),
        max_concurrent_ai=number("JARVIS_AI_MAX_CONCURRENT", "1" if mini else "2", 1, 1 if mini else 4),
        max_message_chars=number("JARVIS_CHAT_MAX_MESSAGE_CHARS", "8000", 1, 8000),
        max_context_chars=number("JARVIS_AI_MAX_CONTEXT_CHARS", "12000" if mini else "24000", 1000, 16000 if mini else 48000),
        max_output_tokens=number("JARVIS_AI_MAX_OUTPUT_TOKENS", "512" if mini else "1024", 16, 1024 if mini else 4096),
        max_response_chars=number("JARVIS_CHAT_MAX_RESPONSE_CHARS", "16000", 100, 32000),
        requests_per_minute=number("JARVIS_CHAT_REQUESTS_PER_MINUTE", "30", 1, 120),
        max_conversations=number("JARVIS_CHAT_MAX_CONVERSATIONS", "100", 1, 500),
        max_turns=number("JARVIS_CHAT_MAX_TURNS", "100", 1, 200),
    )
