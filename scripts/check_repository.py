"""Dependency-free preparation checks; never imports or starts the application."""

from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = (
    "server", "desktop-client", "android-app", "integrations", "tests",
    "scripts", "infrastructure", "docs", "config", ".github/workflows",
)
DOCUMENTS = (
    "readme.md", "LICENSE", "AGENTS.md", "DEVELOPMENT_PROGRESS.md",
    "GIT_WORKFLOW.md", "PROJECT_STRUCTURE.md", "SETUP_CHECKLIST.md",
    "ARCHITECTURE_PLAN.md", "CHANGELOG.md", "docs/CI_PLAN.md",
    "docs/UPSTREAM_REVIEW.md", ".gitignore", ".env.example",
    ".github/workflows/repository-check.yml", "scripts/new-branch.ps1",
    "scripts/configure-git.ps1",
    "server/__main__.py", "server/app.py", "server/config.py", "server/database.py",
    "server/control.py", "server/api/routes.py", "requirements-server.txt",
    "requirements-server-dev.txt", "constraints-server.txt", "pytest.ini",
    "docs/HEADLESS_SERVER.md", "docs/SERVER_API.md", ".github/workflows/server-tests.yml",
    "docs/AI_ENGINE.md", "docs/CHAT_API.md", "docs/PHASE_2_TEST_REPORT.md",
    "server/ai/router.py", "server/ai/providers.py", "server/chat_service.py",
    "server/chat_store.py", "server/api/chat.py", "server/http_security.py",
    "server/static/chat.html", "server/static/chat.css", "server/static/chat.js",
    "config/jarvis-system-prompt.txt",
    "server/security/store.py", "server/security/gate.py", "server/security/api.py",
    "server/security/service.py", "server/security/schema.py", "server/security/types.py",
    "server/static/auth.js", "server/static/login.html", "server/static/login.js",
    "server/static/security.html", "server/static/security.js",
    "docs/AUTHENTICATION.md", "docs/DEVICE_PAIRING.md", "docs/SECURITY.md",
    "docs/PHASE_3_TEST_REPORT.md",
    "docs/JARVIS_MASTER_VISION.md", "docs/ARCHITECTURE_REVIEW.md",
    "docs/USER_EXPERIENCE_REQUIREMENTS.md", "docs/CONVERSATION_ACCEPTANCE_TESTS.md",
    "docs/EXPERIENCE_IMPROVEMENT_PLAN.md",
)
IGNORED_PROBES = (
    ".env", ".env.local", ".env.production", ".env - kopie.example", ".venv/probe", "venv/probe",
    "__pycache__/probe.pyc", "nested/probe.pyc", "logs/probe.log",
    "config/api_keys.json", "config/certs/probe.pem", "config/whatsapp_web/session",
    "nested/token.json", "nested/client_secret.json", "credentials.json",
    "passwords.txt", "secrets/probe", "probe.db", "probe.sqlite3", "probe.bak",
    "backups/probe", "probe.tmp", "build/probe", "dist/probe",
    "android-app/.gradle/probe", "android-app/app/build/probe", "probe.apk",
    "probe.aab", ".idea/probe", ".vscode/probe", "models/probe.gguf",
    "nested/probe.onnx", "node_modules/probe", ".pytest_cache/probe",
    ".local/run/server.json", ".local/data/jarvis.sqlite3", ".local/logs/server.log",
)
PATTERNS = {
    "Groq API key": re.compile(rb"\bgsk_[A-Za-z0-9]{32,}"),
    "Google API key": re.compile(rb"AIza[0-9A-Za-z_-]{35}"),
    "GitHub token": re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})"),
    "AWS access key": re.compile(rb"(?:AKIA|ASIA)[A-Z0-9]{16}"),
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "provider key": re.compile(rb"\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{32,}"),
    "secret assignment": re.compile(
        rb'''(?im)^\s*["']?(?:api_key|access_token|refresh_token|password|client_secret)["']?\s*[:=]\s*["']([^"'\r\n]{12,})["']'''
    ),
}


def git(*args: str, input_text: str | None = None) -> subprocess.CompletedProcess:
    # Binary stdin avoids Windows translating LF into CRLF in path probes.
    result = subprocess.run(
        ["git", *args], cwd=ROOT,
        input=input_text.encode("utf-8") if input_text is not None else None,
        capture_output=True, check=False,
    )
    return subprocess.CompletedProcess(
        result.args, result.returncode,
        result.stdout.decode("utf-8", errors="replace").replace("\r\n", "\n"),
        result.stderr.decode("utf-8", errors="replace").replace("\r\n", "\n"),
    )


def secret_findings(name: str, data: bytes) -> list[str]:
    findings = []
    if b"\0" in data:
        return findings
    for label, pattern in PATTERNS.items():
        for match in pattern.finditer(data):
            if label == "secret assignment" and any(
                value in match.group(1).lower()
                for value in (b"example", b"your_", b"placeholder", b"getenv", b"environ", b"none", b"os.")
            ):
                continue
            line = data[:match.start()].count(b"\n") + 1
            findings.append(f"{name}:{line}: possible {label}; value hidden")
    return findings


def staged_secret_findings() -> list[str]:
    """Inspect index blobs, even when the working copy has already been cleaned."""
    index = git("ls-files", "--stage", "-z")
    if index.returncode:
        return ["Cannot list staged files"]
    entries = []
    for entry in filter(None, index.stdout.split("\0")):
        metadata, separator, name = entry.partition("\t")
        if not separator:
            return ["Invalid Git index entry"]
        mode, oid, stage = metadata.split()
        if stage != "0":
            return ["Unresolved merge conflicts in Git index"]
        if mode in ("100644", "100755", "120000"):
            entries.append((oid, name))
    if not entries:
        return []
    result = subprocess.run(
        ["git", "cat-file", "--batch"], cwd=ROOT,
        input="".join(oid + "\n" for oid, _ in entries).encode("ascii"),
        capture_output=True, check=False,
    )
    if result.returncode:
        return ["Cannot read staged file contents"]
    errors = []
    offset = 0
    for oid, name in entries:
        end = result.stdout.find(b"\n", offset)
        header = result.stdout[offset:end].split()
        if end < 0 or len(header) != 3 or header[:2] != [oid.encode("ascii"), b"blob"]:
            return ["Invalid staged object response"]
        size = int(header[2])
        start = end + 1
        stop = start + size
        if result.stdout[stop:stop + 1] != b"\n":
            return ["Incomplete staged object response"]
        errors.extend(secret_findings(f"index/{name}", result.stdout[start:stop]))
        offset = stop + 1
    return errors


def main() -> int:
    errors = []
    for name in DIRECTORIES:
        directory = ROOT / name
        if not directory.is_dir() or not any(directory.iterdir()):
            errors.append(f"Missing or empty directory: {name}")
    for name in DOCUMENTS:
        path = ROOT / name
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"Missing or empty file: {name}")

    probes = git("check-ignore", "--no-index", "--stdin", input_text="\n".join(IGNORED_PROBES) + "\n")
    if probes.returncode not in (0, 1):
        errors.append("git check-ignore failed")
    ignored = set(probes.stdout.splitlines())
    errors.extend(f"Sensitive/generated path not ignored: {name}" for name in IGNORED_PROBES if name not in ignored)
    tracked_ignored = git("ls-files", "--cached", "--ignored", "--exclude-standard", "-z")
    if tracked_ignored.returncode:
        errors.append("Cannot inspect tracked ignored files")
    errors.extend(f"Tracked ignored path needs review: {name}" for name in tracked_ignored.stdout.split("\0") if name)
    example_ignore = git("check-ignore", "--no-index", ".env.example")
    if example_ignore.returncode != 1:
        errors.append(".env.example must remain trackable")

    example = ROOT / ".env.example"
    expected = {
        "JARVIS_PHASE": "7", "JARVIS_ENV": "development", "JARVIS_HOST": "127.0.0.1",
        "JARVIS_PORT": "8765", "JARVIS_LOG_LEVEL": "info",
        "JARVIS_LOG_PATH": ".local/logs/server.log", "JARVIS_LOG_MAX_BYTES": "1048576",
        "JARVIS_LOG_BACKUP_COUNT": "3", "JARVIS_DATABASE_PATH": ".local/data/jarvis.sqlite3",
        "JARVIS_RUNTIME_DIR": ".local/run", "JARVIS_ENABLE_EXTERNAL_ACCESS": "false",
        "JARVIS_ENABLE_AUTOMATIONS": "true", "JARVIS_GOOGLE_CLIENT_FILE": "", "JARVIS_AI_PROVIDER": "auto", "GEMINI_API_KEY": "",
        "JARVIS_PROFILE": "desktop-development", "JARVIS_AI_PREFERRED_PROVIDER": "gemini",
        "GROQ_API_KEY": "", "GROQ_MODEL": "openai/gpt-oss-120b",
        "GEMINI_MODEL": "gemini-3.8-flash", "OLLAMA_BASE_URL": "http://127.0.0.1:11434",
        "OLLAMA_MODEL": "qwen2.5:3b", "JARVIS_SYSTEM_PROMPT_FILE": "config/jarvis-system-prompt.txt",
        "JARVIS_AI_TIMEOUT_SECONDS": "60", "JARVIS_PROVIDER_TIMEOUT_SECONDS": "25",
        "JARVIS_AI_MAX_CONCURRENT": "2", "JARVIS_CHAT_MAX_MESSAGE_CHARS": "8000",
        "JARVIS_AI_MAX_CONTEXT_CHARS": "24000", "JARVIS_AI_MAX_OUTPUT_TOKENS": "1024",
        "JARVIS_CHAT_MAX_RESPONSE_CHARS": "16000", "JARVIS_CHAT_REQUESTS_PER_MINUTE": "30",
        "JARVIS_CHAT_MAX_CONVERSATIONS": "100", "JARVIS_CHAT_MAX_TURNS": "100",
        'JARVIS_ACCESS_SECONDS': '300',
        'JARVIS_REFRESH_SECONDS': '604800',
        'JARVIS_SESSION_SECONDS': '604800',
        'JARVIS_DESKTOP_SESSION_SECONDS': '2592000',
        'JARVIS_PAIRING_SECONDS': '300',
        'JARVIS_PAIRING_POLL_SECONDS': '5',
        'JARVIS_LOGIN_MAX_ATTEMPTS': '5',
        'JARVIS_LOGIN_WINDOW_SECONDS': '300',
        'JARVIS_AUTH_REQUESTS_PER_MINUTE': '60',
        'JARVIS_AUDIT_RETENTION_DAYS': '30',
        'JARVIS_AUDIT_MAX_ENTRIES': '10000',
        'JARVIS_MAX_DEVICES': '20',
        'JARVIS_MAX_SESSIONS': '20',
        'JARVIS_PASSWORD_REVOKE_ALL': 'true',
        'JARVIS_COOKIE_SECURE': 'auto',
        'JARVIS_TRUSTED_HOSTS': '127.0.0.1,localhost',
        'JARVIS_ALLOWED_ORIGINS': 'http://127.0.0.1:8765,http://localhost:8765',
    }
    actual = {}
    if example.is_file():
        for line in example.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.lstrip().startswith("#"):
                key, separator, value = line.partition("=")
                if not separator or key in actual:
                    errors.append("Invalid or duplicate example configuration entry")
                actual[key] = value
    if actual != expected:
        errors.append("Example must contain only the approved local phase-7 defaults and empty secrets")

    errors.extend(staged_secret_findings())
    result = git("ls-files", "--cached", "--others", "--exclude-standard", "-z")
    if result.returncode:
        errors.append("Cannot list repository files")
    names = sorted(set(filter(None, result.stdout.split("\0"))))
    for name in names:
        path = ROOT / name
        if path.is_file():
            errors.extend(secret_findings(name, path.read_bytes()))

    if "--history" in sys.argv:
        history = git("rev-list", "--objects", "--all")
        if history.returncode:
            errors.append("Cannot list history")
        scanned = set()
        for entry in history.stdout.splitlines():
            oid, separator, name = entry.partition(" ")
            if not separator or oid in scanned:
                continue
            kind = git("cat-file", "-t", oid)
            if kind.returncode or kind.stdout.strip() != "blob":
                continue
            blob = subprocess.run(["git", "cat-file", "blob", oid], cwd=ROOT, capture_output=True, check=False)
            if blob.returncode:
                errors.append(f"Cannot inspect history blob {oid[:12]}")
                continue
            scanned.add(oid)
            errors.extend(secret_findings(f"history/{oid[:12]}/{name}", blob.stdout))
        print(f"Historical text/binary blobs inspected: {len(scanned)} (binary contents skipped)")

    whitespace = git("diff", "--check")
    staged_whitespace = git("diff", "--cached", "--check")
    if whitespace.returncode or staged_whitespace.returncode:
        errors.append("Whitespace check failed; run git diff --check and git diff --cached --check")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Repository checks passed: {len(DIRECTORIES)} directories, {len(DOCUMENTS)} required files, {len(names)} files scanned.")
    print("Pattern checks do not prove that all secrets are absent. This command runs no application tests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
