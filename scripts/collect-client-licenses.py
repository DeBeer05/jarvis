"""Copy installed runtime license notices beside the portable DLLs."""
import importlib.metadata
import shutil
import sys
from pathlib import Path

destination = Path(sys.argv[1]).resolve() / "third-party-licenses"
destination.mkdir(parents=True, exist_ok=True)
names = ("PySide6-Essentials", "shiboken6", "httpx", "httpcore", "anyio", "idna", "certifi", "h11", "typing_extensions", "numpy", "sounddevice", "cffi", "pycparser", "pydantic", "pydantic_core", "annotated-types", "typing-inspection","websockets")
if "--voice" in sys.argv:
    names = (package.metadata["Name"] for package in importlib.metadata.distributions())
for name in names:
    package = importlib.metadata.distribution(name)
    for relative in package.files or ():
        if "license" in str(relative).lower() or "copying" in str(relative).lower():
            source = Path(package.locate_file(relative))
            if source.is_file():
                target = destination / name / str(relative).replace("../", "")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
print("Runtime license notices collected.")
