"""Natural-conversation tables, migrated atomically in the existing database."""


def migrate(db):
    statements = [
        "CREATE TABLE natural_settings(user_id INTEGER NOT NULL,scope TEXT NOT NULL,device_id TEXT NOT NULL DEFAULT '',revision INTEGER NOT NULL,payload TEXT NOT NULL,updated REAL NOT NULL,PRIMARY KEY(user_id,scope,device_id))",
        "CREATE TABLE natural_memories(id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,category TEXT NOT NULL,content TEXT NOT NULL,memory_key TEXT NOT NULL,kind TEXT NOT NULL,source TEXT NOT NULL,source_turn TEXT,created REAL NOT NULL,updated REAL NOT NULL,last_used REAL,confidence REAL NOT NULL,sensitivity TEXT NOT NULL,expires REAL,status TEXT NOT NULL,explicit INTEGER NOT NULL,revision INTEGER NOT NULL DEFAULT 1)",
        "CREATE INDEX natural_memory_owner ON natural_memories(user_id,status,category,updated)",
        "CREATE VIRTUAL TABLE natural_memory_fts USING fts5(id UNINDEXED,user_id UNINDEXED,content,category,tokenize='unicode61 remove_diacritics 2')",
        "CREATE TABLE natural_forgotten(user_id INTEGER NOT NULL,source_turn TEXT NOT NULL,content_hash TEXT NOT NULL,created REAL NOT NULL,PRIMARY KEY(user_id,source_turn,content_hash))",
        "CREATE TABLE natural_summaries(id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,conversation_id TEXT NOT NULL REFERENCES chat_conversations(id) ON DELETE CASCADE,content TEXT NOT NULL,through_sequence INTEGER NOT NULL,created REAL NOT NULL,updated REAL NOT NULL,revision INTEGER NOT NULL DEFAULT 1,UNIQUE(user_id,conversation_id))",
        "CREATE TABLE natural_summary_sources(summary_id TEXT NOT NULL REFERENCES natural_summaries(id) ON DELETE CASCADE,memory_id TEXT NOT NULL,PRIMARY KEY(summary_id,memory_id))",
        "CREATE TABLE natural_conversation_owners(conversation_id TEXT PRIMARY KEY REFERENCES chat_conversations(id) ON DELETE CASCADE,user_id INTEGER NOT NULL)",
        "CREATE TABLE natural_sessions(conversation_id TEXT PRIMARY KEY REFERENCES chat_conversations(id) ON DELETE CASCADE,user_id INTEGER NOT NULL,device_id TEXT NOT NULL,auth_session TEXT NOT NULL,state TEXT NOT NULL,epoch INTEGER NOT NULL,revision INTEGER NOT NULL,started REAL NOT NULL,activity REAL NOT NULL,lease_until REAL NOT NULL,context TEXT NOT NULL DEFAULT '{}')",
        "CREATE TABLE natural_pending(id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,conversation_id TEXT NOT NULL REFERENCES chat_conversations(id) ON DELETE CASCADE,kind TEXT NOT NULL,payload TEXT NOT NULL,revision INTEGER NOT NULL,created REAL NOT NULL,updated REAL NOT NULL,status TEXT NOT NULL DEFAULT 'waiting')",
        "CREATE INDEX natural_pending_owner ON natural_pending(user_id,conversation_id,status)",
        "CREATE TABLE natural_diagnostics(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,device_id TEXT NOT NULL,at REAL NOT NULL,event TEXT NOT NULL,metric REAL,code TEXT)",
        "CREATE TABLE natural_audit(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,device_id TEXT NOT NULL,at REAL NOT NULL,event TEXT NOT NULL,target TEXT)",
    ]
    for statement in statements: db.execute(statement)
    db.execute("INSERT INTO natural_conversation_owners SELECT id,1 FROM chat_conversations WHERE EXISTS(SELECT 1 FROM auth_users WHERE id=1)")
