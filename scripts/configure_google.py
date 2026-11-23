"""Install an explicitly selected Desktop OAuth file without revealing credentials."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile


def validate_client(source):
    source = Path(source)
    if source.stat().st_size > 65536:
        raise ValueError("Google-clientbestand is te groot.")
    raw = source.read_bytes()
    try:
        config = json.loads(raw)
        installed = config["installed"]
        identifier = installed["client_id"]
        if not isinstance(identifier, str) or not identifier.endswith(".apps.googleusercontent.com"):
            raise ValueError()
        if not isinstance(installed.get("client_secret"), str) or not installed["client_secret"]:
            raise ValueError()
    except (ValueError, KeyError, TypeError):
        raise ValueError("Kies de gedownloade OAuth-JSON van type Desktop-app.") from None
    return raw


def configure(root, source, check_only=False):
    root = Path(root).resolve()
    raw = validate_client(source)
    if check_only:
        return None
    env_path = root / ".env"
    content = env_path.read_bytes().decode("utf-8-sig") if env_path.exists() else ""
    from dotenv.parser import parse_stream
    from io import StringIO
    if any(binding.error for binding in parse_stream(StringIO(content))):
        raise ValueError("Herstel eerst de bestaande .env-syntaxis; niets gewijzigd.")
    directory = root / "secrets"
    directory.mkdir(exist_ok=True)
    target = directory / "google-desktop.json"
    if target.exists() and target.read_bytes() != raw:
        target = directory / ("google-desktop-" + hashlib.sha256(raw).hexdigest()[:16] + ".json")
    if target.exists() and target.read_bytes() != raw:
        raise ValueError("Bestandsconflict; bestaande Google-configuratie behouden.")
    # Exclusive creation: existing user configuration is never overwritten.
    if not target.exists():
        with target.open("xb") as output:
            output.write(raw)
    settings = {"JARVIS_GOOGLE_CLIENT_FILE": target.relative_to(root).as_posix(),
                "JARVIS_ENABLE_AUTOMATIONS": "true"}
    newline = "\r\n" if "\r\n" in content else "\n"
    for name, value in settings.items():
        pattern = r"(?m)^[ \t]*(?:export[ \t]+)?" + name + r"[ \t]*=[^\r\n]*"
        if re.search(pattern, content):
            content = re.sub(pattern, name + "=" + value, content)
        else:
            content = content.rstrip("\r\n") + newline + name + "=" + value + newline
    fd, temporary = tempfile.mkstemp(prefix=".env.google-", suffix=".tmp", dir=root)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(content.encode("utf-8"))
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, env_path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--client-file", type=Path, required=True)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    try:
        result = configure(args.root, args.client_file, args.check_only)
    except (OSError, UnicodeError, ValueError):
        print("Google-configuratie niet ingesteld. Controleer het Desktop OAuth-JSON-bestand, .env en schrijfrechten. Bestaande credentials zijn niet getoond.")
        return 1
    print("Desktop OAuth-JSON gecontroleerd." if result is None else "Google-clientbestand veilig ingesteld; overige .env-instellingen behouden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
