"""Short-lived SQLite connections and one small, versioned schema migration."""

import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

SCHEMA_VERSION = 13


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
            if 0 < version < SCHEMA_VERSION:
                backup_path = self.path.with_name(self.path.name + f".pre-v{SCHEMA_VERSION}-" + uuid.uuid4().hex[:10] + ".bak")
                backup = sqlite3.connect(backup_path)
                try:
                    connection.backup(backup)
                finally:
                    backup.close()
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            if version < 1:
                connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (1,))
                connection.execute("PRAGMA user_version=1")
            if version < 2:
                connection.execute(
                    "CREATE TABLE chat_conversations (id TEXT PRIMARY KEY, title TEXT NOT NULL, "
                    "created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
                )
                connection.execute(
                    "CREATE TABLE chat_turns (id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL "
                    "REFERENCES chat_conversations(id) ON DELETE CASCADE, created_at TEXT NOT NULL, "
                    "user_text TEXT NOT NULL, assistant_text TEXT NOT NULL DEFAULT '', provider TEXT, "
                    "model TEXT, status TEXT NOT NULL, error_code TEXT, sequence INTEGER NOT NULL, "
                    "UNIQUE(conversation_id, sequence))"
                )
                connection.execute("CREATE INDEX chat_turns_conversation ON chat_turns(conversation_id, sequence)")
                connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (2,))
                connection.execute("PRAGMA user_version=2")
            if version < 3:
                from server.security.schema import migrate
                migrate(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (3)")
                connection.execute("PRAGMA user_version=3")
            if version < 4:
                from server.automation.store import migrate
                migrate(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (4)")
                connection.execute("PRAGMA user_version=4")
            if version < 5:
                from server.natural.schema import migrate
                migrate(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (5)")
                connection.execute("PRAGMA user_version=5")
            if version < 6:
                connection.execute("CREATE TABLE natural_memory_origins(memory_id TEXT PRIMARY KEY REFERENCES natural_memories(id) ON DELETE CASCADE,device_id TEXT NOT NULL)")
                connection.execute("CREATE INDEX natural_memory_key ON natural_memories(user_id,memory_key,status,updated)")
                connection.execute("INSERT INTO natural_memory_origins SELECT m.id,a.device_id FROM natural_memories m JOIN natural_audit a ON a.id=(SELECT min(id) FROM natural_audit WHERE target=m.id AND user_id=m.user_id AND event='memory_created')")
                connection.execute("INSERT INTO schema_migrations(version) VALUES (6)")
                connection.execute("PRAGMA user_version=6")
            if version < 7:
                connection.execute("CREATE TABLE natural_contacts(id TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,name TEXT NOT NULL,email TEXT NOT NULL,aliases TEXT NOT NULL,revision INTEGER NOT NULL,created REAL NOT NULL,updated REAL NOT NULL)")
                connection.execute("CREATE INDEX natural_contacts_user ON natural_contacts(user_id)")
                connection.execute("INSERT INTO schema_migrations(version) VALUES (7)")
                connection.execute("PRAGMA user_version=7")
            if version < 8:
                connection.execute("CREATE TABLE voice_usage(id TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES auth_users(id),created REAL NOT NULL,characters INTEGER NOT NULL,credits INTEGER NOT NULL,status TEXT NOT NULL)")
                connection.execute('CREATE INDEX voice_usage_owner_time ON voice_usage(user_id,created)')
                connection.execute('INSERT INTO schema_migrations(version) VALUES (8)')
                connection.execute('PRAGMA user_version=8')
            if version < 9:
                from server.natural.episodes import migrate
                migrate(connection)
                connection.execute('INSERT INTO schema_migrations(version) VALUES (9)')
                connection.execute('PRAGMA user_version=9')
            if version < 10:
                from server.natural.events import migrate as migrate_events
                from server.natural.presence import migrate as migrate_presence
                migrate_events(connection)
                migrate_presence(connection)
                connection.execute('INSERT INTO schema_migrations(version) VALUES (10)')
                connection.execute('PRAGMA user_version=10')
            if version < 11:
                from server.natural.life_items import migrate
                migrate(connection)
                connection.execute('INSERT INTO schema_migrations(version) VALUES (11)')
                connection.execute('PRAGMA user_version=11')
            if version < 12:
                from server.natural.device_status import migrate
                migrate(connection)
                connection.execute('INSERT INTO schema_migrations(version) VALUES (12)')
                connection.execute('PRAGMA user_version=12')
            if version < 13:
                from server.natural.vision import migrate
                migrate(connection)
                connection.execute('INSERT INTO schema_migrations(version) VALUES (13)')
                connection.execute('PRAGMA user_version=13')
            # A process restart must never present an unfinished answer as complete.
            connection.execute("UPDATE chat_turns SET status='interrupted', error_code='server_restarted' WHERE status='running'")
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
