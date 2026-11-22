"""Keep configured credentials and recognizable API keys out of stored chat text."""
import re

PATTERNS = (
    re.compile(r"\bgsk_[A-Za-z0-9]{32,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})"),
    re.compile(r"\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{32,}"),
)


def redact(text: str, secret: str = "") -> str:
    if secret:
        text = text.replace(secret, "[GEHEIM VERWIJDERD]")
    for pattern in PATTERNS:
        text = pattern.sub("[GEHEIM VERWIJDERD]", text)
    return text
