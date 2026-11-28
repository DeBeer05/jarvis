"""Start the native client from source as well as from its frozen bundle."""
import sys
from pathlib import Path

if not getattr(sys,'frozen',False):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from jarvis_client.app import main

if __name__ == "__main__":
    raise SystemExit(main())
