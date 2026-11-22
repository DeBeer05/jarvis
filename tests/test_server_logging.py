import json
import logging
from dataclasses import replace

from server.logging_config import close_logging, configure_logging


def test_json_logs_rotation_and_redaction(settings):
    canary = "test-canary-" + "never-expose"
    settings = replace(settings, gemini_api_key=canary, log_max_bytes=1024, log_backup_count=2)
    handlers = configure_logging(settings, console=False)
    logger = logging.getLogger("jarvis.server")
    try:
        for _ in range(30):
            logger.warning("warning %s password=%s", canary, "private-value")
        try:
            raise ValueError(canary)
        except ValueError:
            logger.exception("safe_exception_event")
    finally:
        close_logging(handlers)
    files = list(settings.log_path.parent.glob("server.log*"))
    assert 1 < len(files) <= 3
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert canary not in text
        assert "private-value" not in text
        assert path.stat().st_size <= 1024
        assert all(json.loads(line)["timestamp"] for line in text.splitlines())
