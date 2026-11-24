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
        assert connection.execute("SELECT count(*) FROM schema_migrations").fetchone() == (SCHEMA_VERSION,)
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


def test_schema_six_preserves_memory_and_recovers_only_known_origin(tmp_path):
    database=Database(tmp_path/"existing.sqlite3");database.initialize()
    with database.connection() as db:
        for identifier in ("known","unknown"):
            db.execute("INSERT INTO natural_memories VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (identifier,1,"project","Synthetic memory","","fact","explicit",None,1,1,None,1.,"normal",None,"active",1,1))
        db.execute("INSERT INTO natural_audit(user_id,device_id,at,event,target) VALUES (1,'synthetic-origin',1,'memory_created','known')")
        db.execute("DROP TABLE natural_contacts")
        db.execute("DROP TABLE natural_memory_origins")
        db.execute("DROP INDEX natural_memory_key")
        db.execute("DELETE FROM schema_migrations WHERE version>=6")
        db.execute("PRAGMA user_version=5")
    database.close();database.initialize()
    with database.connection(readonly=True) as db:
        assert db.execute("SELECT count(*) FROM natural_memories").fetchone()[0]==2
        assert db.execute("SELECT * FROM natural_memory_origins").fetchall()==[("known","synthetic-origin")]
    backup=next(tmp_path.glob("existing.sqlite3.pre-v7-*.bak"))
    with sqlite3.connect(backup) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0]==5
        assert db.execute("SELECT count(*) FROM natural_memories").fetchone()[0]==2


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


def test_schema_seven_adds_contacts_without_losing_previous_tables(tmp_path):
    database=Database(tmp_path/"schema6.sqlite3");database.initialize()
    with database.connection() as db:
        db.execute("INSERT INTO natural_audit(user_id,device_id,at,event,target) VALUES (1,'synthetic',1,'test','keep')")
        db.execute("DROP TABLE natural_contacts")
        db.execute("DELETE FROM schema_migrations WHERE version=7")
        db.execute("PRAGMA user_version=6")
    database.close();database.initialize()
    with database.connection(readonly=True) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0]==7
        assert db.execute("SELECT target FROM natural_audit").fetchone()[0]=="keep"
        assert db.execute("SELECT count(*) FROM natural_contacts").fetchone()[0]==0
    backup=next(tmp_path.glob("schema6.sqlite3.pre-v7-*.bak"))
    with sqlite3.connect(backup) as db:assert db.execute("PRAGMA user_version").fetchone()[0]==6
