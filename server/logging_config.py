"""Bounded JSON logging with no configuration dumps or exception messages."""

import json
import logging
import re
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

from server.config import Settings


class JsonFormatter(logging.Formatter):
    def __init__(self, secrets: tuple[str, ...] = ()):
        super().__init__()
        self.secrets = tuple(value for value in secrets if value)

    def format(self, record: logging.LogRecord) -> str:
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        for name in ("error_type", "error_code", "request_id", "status_code", "environment", "host", "port", "schema_version"):
            if hasattr(record, name):
                data[name] = getattr(record, name)
        if record.exc_info:
            data["error_type"] = record.exc_info[0].__name__
        result = json.dumps(data, ensure_ascii=True)
        for secret in self.secrets:
            # Replace the JSON-escaped form, including multiline secret values.
            result = result.replace(json.dumps(secret)[1:-1], "[REDACTED]")
        result = re.sub(r"(?i)((?:password|token|api[_-]?key|secret)[=:]\\?\"?)[^\s,\"}]+", r"\1[REDACTED]", result)
        return result


def configure_logging(settings: Settings, *, console: bool = True) -> list[logging.Handler]:
    settings.log_path.parent.mkdir(parents=True, exist_ok=True)
    formatter = JsonFormatter((settings.gemini_api_key, settings.groq_api_key))
    file_handler = RotatingFileHandler(
        settings.log_path, maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count, encoding="utf-8",
    )
    handlers: list[logging.Handler] = [file_handler]
    if console:
        handlers.append(logging.StreamHandler())
    for handler in handlers:
        handler.setFormatter(formatter)
    for name in ("jarvis.server", "uvicorn", "uvicorn.error"):
        logger = logging.getLogger(name)
        logger.handlers = handlers.copy()
        logger.setLevel(settings.log_level.upper())
        logger.propagate = False
    return handlers


def close_logging(handlers: list[logging.Handler]) -> None:
    for name in ("jarvis.server", "uvicorn", "uvicorn.error"):
        logger = logging.getLogger(name)
        logger.handlers = [handler for handler in logger.handlers if handler not in handlers]
    for handler in handlers:
        handler.close()
