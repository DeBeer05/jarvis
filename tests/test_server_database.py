import sqlite3

import pytest

from server.database import Database, SCHEMA_VERSION


def test_initialization_and_idempotent_migration(tmp_path):
    database = Database(tmp_path / "nested" / "test.sqlite3")
    assert not database.check()
    database.initialize()
    database.initialize()
    assert database.check()
    with database.connection(readonly=True) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (SCHEMA_VERSION,)
        assert connection.execute("SELECT count(*) FROM schema_migrations").fetchone() == (3,)
        tables = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        assert set(tables) >= {("schema_migrations",), ("chat_conversations",), ("chat_turns",)}
    database.close()
    assert not database.check()
    # Windows refuses this if a database connection was accidentally left open.
    database.path.rename(tmp_path / "closed.sqlite3")


def test_readiness_does_not_recreate_missing_database(tmp_path):
    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    database.path.unlink()
    assert not database.check()
    assert not database.path.exists()


def test_newer_database_schema_is_not_overwritten(tmp_path):
    path = tmp_path / "future.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA user_version=99")
    with pytest.raises(sqlite3.DatabaseError):
        Database(path).initialize()
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (99,)


def test_corrupt_database_fails(tmp_path):
    path = tmp_path / "corrupt.sqlite3"
    path.write_bytes(b"not a SQLite database")
    with pytest.raises(sqlite3.DatabaseError):
        Database(path).initialize()
