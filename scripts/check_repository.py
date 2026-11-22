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
)
IGNORED_PROBES = (
    ".env", ".env.local", ".env.production", ".venv/probe", "venv/probe",
    "__pycache__/probe.pyc", "nested/probe.pyc", "logs/probe.log",
    "config/api_keys.json", "config/certs/probe.pem", "config/whatsapp_web/session",
    "nested/token.json", "nested/client_secret.json", "credentials.json",
    "passwords.txt", "secrets/probe", "probe.db", "probe.sqlite3", "probe.bak",
    "backups/probe", "probe.tmp", "build/probe", "dist/probe",
    "android-app/.gradle/probe", "android-app/app/build/probe", "probe.apk",
    "probe.aab", ".idea/probe", ".vscode/probe", "models/probe.gguf",
    "nested/probe.onnx", "node_modules/probe", ".pytest_cache/probe",
)
PATTERNS = {
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
        "JARVIS_PHASE": "0", "JARVIS_ENABLE_EXTERNAL_ACCESS": "false",
        "JARVIS_ENABLE_AUTOMATIONS": "false", "JARVIS_AI_MODE": "hybrid",
        "GEMINI_API_KEY": "", "GOOGLE_CLIENT_ID": "", "GOOGLE_CLIENT_SECRET": "",
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
        errors.append("Example must contain only the approved inactive phase-0 placeholders")

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
    print("Pattern checks do not prove that all secrets are absent. No application tests executed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
