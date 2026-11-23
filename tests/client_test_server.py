"""Synthetic TCP fixture, never the user's personal database or provider keys."""
import sys
from pathlib import Path

import uvicorn

from server.app import create_app
from server.ai.router import AIRouter
from server.config import load_settings
from server.database import Database
from server.security.store import SecurityStore
from tests.ai_helpers import FakeProvider
from tests.auth_helpers import owner_hash


if __name__ == "__main__":
    root, port = Path(sys.argv[1]), int(sys.argv[2])
    settings = load_settings(root=root, environ={"JARVIS_DATABASE_PATH": str(root / "test.sqlite3"), "JARVIS_PORT": str(port), "JARVIS_LOG_PATH": str(root / "test.log"), "GEMINI_API_KEY": "", "GROQ_API_KEY": ""})
    database = Database(settings.database_path)
    database.initialize()
    store = SecurityStore(database, settings)
    store.create_owner("owner", owner_hash())
    app = create_app(settings, ai_router=AIRouter(settings, {name: FakeProvider() for name in ("gemini", "groq", "ollama")}))
    uvicorn.run(app, host="127.0.0.1", port=port, access_log=False, log_level="warning")
