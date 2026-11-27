"""Bounded local retrieval of user-authored episodes; never execution authority."""
import re
from datetime import datetime, timezone

from server.natural.memory import SECRET, SENSITIVE


STOP = set('de het een en of van voor naar met dat dit die over wat wie hoe waar wanneer welke ik je jij u uw mijn me mij we ons is zijn ben heb heeft kan kun wil zou maar ook nog dan er te in op aan bij om als vertel graag eerder vorige vorig keer gesprek gesprekken hadden besproken weet herinner onthoud'.split())


def migrate(db):
    db.execute("CREATE VIRTUAL TABLE natural_episode_fts USING fts5(user_text,content='chat_turns',content_rowid='rowid',tokenize='unicode61 remove_diacritics 2')")
    db.execute("CREATE TRIGGER natural_episode_insert AFTER INSERT ON chat_turns BEGIN INSERT INTO natural_episode_fts(rowid,user_text) VALUES(new.rowid,new.user_text); END")
    db.execute("CREATE TRIGGER natural_episode_delete AFTER DELETE ON chat_turns BEGIN INSERT INTO natural_episode_fts(natural_episode_fts,rowid,user_text) VALUES('delete',old.rowid,old.user_text); END")
    db.execute("CREATE TRIGGER natural_episode_update AFTER UPDATE OF user_text ON chat_turns BEGIN INSERT INTO natural_episode_fts(natural_episode_fts,rowid,user_text) VALUES('delete',old.rowid,old.user_text); INSERT INTO natural_episode_fts(rowid,user_text) VALUES(new.rowid,new.user_text); END")
    db.execute("INSERT INTO natural_episode_fts(natural_episode_fts) VALUES('rebuild')")
    db.execute("CREATE TABLE natural_episode_origins(turn_id TEXT PRIMARY KEY REFERENCES chat_turns(id) ON DELETE CASCADE,device_id TEXT NOT NULL)")
    db.execute("CREATE TABLE natural_episode_sources(turn_id TEXT NOT NULL REFERENCES chat_turns(id) ON DELETE CASCADE,source_turn TEXT NOT NULL,PRIMARY KEY(turn_id,source_turn))")
    db.execute("CREATE INDEX natural_episode_source ON natural_episode_sources(source_turn)")


class EpisodeMemory:
    def __init__(self, store):
        self.store = store

    def retrieve(self, principal, conversation, query, config, *, local):
        memory = config['memory']
        if not (memory['episodes'] and memory['long_term'] and memory['history']):
            return []
        if not local and not config['privacy']['cloud_memories']:
            return []
        words = sorted(set(re.findall(r'[\wÀ-ÿ]{3,40}', query.casefold())) - STOP)[:8]
        if not words or memory['context_items'] == 0:
            return []
        terms = ' OR '.join('"' + word + '"' for word in words)
        cutoff = datetime.fromtimestamp(self.store.clock() - config['privacy']['history_days'] * 86400, timezone.utc).isoformat()
        with self.store.transaction(principal) as (db, user):
            rows = db.execute("""SELECT t.id,t.conversation_id,t.created_at,t.user_text
                FROM natural_episode_fts JOIN chat_turns t ON t.rowid=natural_episode_fts.rowid
                JOIN natural_conversation_owners o ON o.conversation_id=t.conversation_id
                LEFT JOIN natural_episode_origins d ON d.turn_id=t.id
                WHERE natural_episode_fts MATCH ? AND o.user_id=?
                AND t.conversation_id!=? AND t.status='completed' AND t.created_at>=?
                AND (? OR d.device_id=?)
                AND t.id NOT IN (SELECT source_turn FROM natural_forgotten WHERE user_id=?)
                ORDER BY bm25(natural_episode_fts),t.created_at DESC LIMIT 20""",
                (terms,user,conversation,cutoff,int(memory['synchronize']),principal.device_id,user)).fetchall()
        # No assistant-generated claims or guessed emotions become stored facts.
        result = []
        for row in rows:
            text = row['user_text']
            if SECRET.search(text) or (SENSITIVE.search(text) and not (local and memory['sensitive'])):
                continue
            result.append({'source_turn':row['id'],'conversation_id':row['conversation_id'],
                           'at':row['created_at'],'user_said':text[:480]})
            if len(result) >= min(3,memory['context_items']):
                break
        return result

    def record(self, principal, turn, sources):
        if not sources:
            return
        with self.store.transaction(principal,write=True) as (db,user):
            db.executemany('INSERT OR IGNORE INTO natural_episode_sources VALUES (?,?)',
                           [(turn,item['source_turn']) for item in sources])
