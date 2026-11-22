"""Bounded conversation persistence; never holds a connection during AI calls."""
import sqlite3
import uuid
from datetime import datetime, timezone

from server.database import Database
from server.redaction import redact


class ChatError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(code)
        self.code, self.message, self.status = code, message, status


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ChatStore:
    def __init__(self, database: Database, *, secret: str = "", secrets: tuple[str, ...] = (), max_conversations: int = 100, max_turns: int = 100):
        self.database, self.secret = database, secret
        self.secrets = (secret, *secrets)
        self.max_conversations, self.max_turns = max_conversations, max_turns

    def clean(self, text: str) -> str:
        for secret in self.secrets:
            text = redact(text, secret)
        return text

    def start(self, request_id: str, conversation_id: str | None, message: str) -> tuple[str, list[dict]]:
        message = self.clean(message)
        with self.database.connection() as db:
            db.row_factory = sqlite3.Row
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM chat_turns WHERE id=?", (request_id,)).fetchone():
                raise ChatError("duplicate_request", "Dit verzoek is al verwerkt. Start een nieuw verzoek.", 409)
            if conversation_id:
                if not db.execute("SELECT 1 FROM chat_conversations WHERE id=?", (conversation_id,)).fetchone():
                    raise ChatError("not_found", "Gesprek niet gevonden.", 404)
            else:
                count = db.execute("SELECT count(*) FROM chat_conversations").fetchone()[0]
                if count >= self.max_conversations:
                    raise ChatError("history_full", "De gesprekslimiet is bereikt. Verwijder eerst een oud gesprek.", 409)
                conversation_id = str(uuid.uuid4())
                db.execute("INSERT INTO chat_conversations VALUES (?,?,?,?)", (conversation_id, message[:72], now(), now()))
            count = db.execute("SELECT count(*) FROM chat_turns WHERE conversation_id=?", (conversation_id,)).fetchone()[0]
            if count >= self.max_turns:
                raise ChatError("conversation_full", "Dit gesprek is vol. Begin een nieuw gesprek.", 409)
            rows = db.execute(
                "SELECT user_text,assistant_text FROM chat_turns WHERE conversation_id=? "
                "AND status='completed' ORDER BY sequence DESC LIMIT 20", (conversation_id,),
            ).fetchall()
            history = []
            for row in reversed(rows):
                history.extend([{"role": "user", "content": row["user_text"]}, {"role": "assistant", "content": row["assistant_text"]}])
            db.execute(
                "INSERT INTO chat_turns(id,conversation_id,created_at,user_text,status,sequence) VALUES (?,?,?,?,?,?)",
                (request_id, conversation_id, now(), message, "running", count + 1),
            )
            db.execute("UPDATE chat_conversations SET updated_at=? WHERE id=?", (now(), conversation_id))
        return conversation_id, history

    def finish(self, request_id: str, text: str, provider: str | None, model: str | None, status: str, error_code: str | None) -> None:
        with self.database.connection() as db:
            db.execute(
                "UPDATE chat_turns SET assistant_text=?,provider=?,model=?,status=?,error_code=? WHERE id=?",
                (self.clean(text), provider, self.clean(model or "") or None, status, error_code, request_id),
            )

    def list(self, limit: int = 50, offset: int = 0) -> dict:
        with self.database.connection(readonly=True) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT * FROM chat_conversations ORDER BY updated_at DESC LIMIT ? OFFSET ?", (limit + 1, offset)).fetchall()
        return {"items": [dict(row) for row in rows[:limit]], "has_more": len(rows) > limit}

    def get(self, conversation_id: str) -> dict:
        with self.database.connection(readonly=True) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM chat_conversations WHERE id=?", (conversation_id,)).fetchone()
            if row is None:
                raise ChatError("not_found", "Gesprek niet gevonden.", 404)
            turns = db.execute(
                "SELECT * FROM chat_turns WHERE conversation_id=? ORDER BY sequence", (conversation_id,),
            ).fetchall()
        return {**dict(row), "turns": [dict(turn) for turn in turns]}

    def delete(self, conversation_id: str) -> None:
        with self.database.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM chat_turns WHERE conversation_id=? AND status='running' LIMIT 1", (conversation_id,)).fetchone():
                raise ChatError("conversation_busy", "Stop eerst het lopende antwoord.", 409)
            cursor = db.execute("DELETE FROM chat_conversations WHERE id=?", (conversation_id,))
            if cursor.rowcount == 0:
                raise ChatError("not_found", "Gesprek niet gevonden.", 404)
