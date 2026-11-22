"""Short-lived SQLite connections and one small, versioned schema migration."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA_VERSION = 1


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.initialized = False

    @contextmanager
    def connection(self, *, readonly: bool = False):
        target = self.path.as_uri() + "?mode=ro" if readonly else str(self.path)
        connection = sqlite3.connect(target, uri=readonly, timeout=1)
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise sqlite3.DatabaseError("Database schema is newer than this server")
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            if version < 1:
                connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (1,))
                connection.execute("PRAGMA user_version=1")
        self.initialized = True

    def check(self) -> bool:
        if not self.initialized:
            return False
        try:
            with self.connection(readonly=True) as connection:
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                row = connection.execute("SELECT version FROM schema_migrations WHERE version=?", (SCHEMA_VERSION,)).fetchone()
                return version == SCHEMA_VERSION and row == (SCHEMA_VERSION,)
        except (OSError, sqlite3.Error):
            return False

    def close(self) -> None:
        # Every actual connection is already closed by its context manager.
        self.initialized = False
