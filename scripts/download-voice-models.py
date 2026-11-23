"""Explicit, pinned downloads only; never imported by the app."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import urllib.request


MODELS = (
    ("Systran/faster-whisper-small", "536b0662742c02347bc0e980a01041f333bce120", "whisper-small",
     ("README.md", "config.json", "model.bin", "tokenizer.json", "vocabulary.txt")),
    ("rhasspy/piper-voices", "e9c8a39444359388adaa94255becb37a5a2b8e51", "piper",
     ("nl/nl_NL/mls/medium/nl_NL-mls-medium.onnx", "nl/nl_NL/mls/medium/nl_NL-mls-medium.onnx.json",
      "nl/nl_NL/mls/medium/MODEL_CARD", "README.md")),
)
RONNIE = (("rhasspy/piper-voices", "e9c8a39444359388adaa94255becb37a5a2b8e51", "piper-ronnie",
           ("nl/nl_NL/ronnie/medium/nl_NL-ronnie-medium.onnx", "nl/nl_NL/ronnie/medium/nl_NL-ronnie-medium.onnx.json",
            "nl/nl_NL/ronnie/medium/MODEL_CARD", "README.md")),)


def digest(path, kind):
    h = hashlib.sha256() if kind == "sha256" else hashlib.sha1(usedforsecurity=False)
    if kind == "git":
        h.update(f"blob {path.stat().st_size}\0".encode())
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(root, models=MODELS):
    for repo, revision, directory, names in models:
        with urllib.request.urlopen(f"https://huggingface.co/api/models/{repo}/revision/{revision}?blobs=true", timeout=30) as response:
            metadata = {item["rfilename"]: item for item in json.load(response)["siblings"]}
        target = root / directory
        target.mkdir(parents=True, exist_ok=True)
        records = []
        for name in names:
            info = metadata[name]
            kind = "sha256" if "lfs" in info else "git"
            expected = info["lfs"]["sha256"] if "lfs" in info else info["blobId"]
            destination = target / Path(name).name
            if not (destination.is_file() and destination.stat().st_size == info["size"] and digest(destination, kind) == expected):
                temporary = destination.with_suffix(destination.suffix + ".partial")
                with urllib.request.urlopen(f"https://huggingface.co/{repo}/resolve/{revision}/{name}", timeout=90) as response, temporary.open("wb") as output:
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
                if temporary.stat().st_size != info["size"] or digest(temporary, kind) != expected:
                    raise RuntimeError("Modelcontrole mislukt: " + Path(name).name)
                temporary.replace(destination)
            records.append({"file": destination.name, "bytes": info["size"], "sha256": digest(destination, "sha256")})
            print(f"Gecontroleerd: {directory}/{destination.name} ({info['size']} bytes)", flush=True)
        (target / "download-manifest.json").write_text(json.dumps({"repository": repo, "revision": revision, "files": records}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download circa 563 MB Whisper Small + Piper NL; alleen na toestemming.")
    parser.add_argument("--accept-downloads", action="store_true", help="Bevestig de vooraf besproken modeldownload van circa 563 MB")
    parser.add_argument("--directory", type=Path, default=Path(os.environ.get("LOCALAPPDATA", Path.home())) / "JARVIS/Desktop/models")
    parser.add_argument("--ronnie-only", action="store_true", help="Alleen de extra Nederlandse Ronnie-stem (~63 MB), na aparte toestemming")
    args = parser.parse_args()
    if not args.accept_downloads:
        parser.error("Vooraf toestemming nodig voor circa 563 MB; gebruik daarna --accept-downloads.")
    download(args.directory, RONNIE if args.ronnie_only else MODELS)
