"""Schema migration statements; executed inside Database's migration transaction."""

STATEMENTS = (
    "CREATE TABLE auth_users (id INTEGER PRIMARY KEY CHECK(id=1), username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, created_at REAL NOT NULL)",
    "CREATE TABLE auth_devices (id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES auth_users(id), name TEXT NOT NULL, type TEXT NOT NULL, created_at REAL NOT NULL, last_seen REAL NOT NULL, trusted INTEGER NOT NULL DEFAULT 1, revoked_at REAL)",
    "CREATE TABLE auth_permissions (device_id TEXT NOT NULL REFERENCES auth_devices(id), permission TEXT NOT NULL, PRIMARY KEY(device_id,permission))",
    "CREATE TABLE auth_sessions (id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES auth_users(id), device_id TEXT NOT NULL REFERENCES auth_devices(id), created_at REAL NOT NULL, last_seen REAL NOT NULL, expires_at REAL NOT NULL, access_hash TEXT NOT NULL UNIQUE, access_expires_at REAL NOT NULL, csrf_hash TEXT NOT NULL, revoked_at REAL)",
    "CREATE TABLE auth_refresh_tokens (id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES auth_sessions(id), token_hash TEXT NOT NULL UNIQUE, issued_at REAL NOT NULL, expires_at REAL NOT NULL, consumed_at REAL, revoked_at REAL)",
    "CREATE INDEX auth_refresh_session ON auth_refresh_tokens(session_id)",
    "CREATE TABLE auth_pairing (id TEXT PRIMARY KEY, device_hash TEXT NOT NULL UNIQUE, user_code_hash TEXT NOT NULL, challenge TEXT NOT NULL, name TEXT NOT NULL, type TEXT NOT NULL, requested_scopes TEXT NOT NULL, approved_scopes TEXT, created_at REAL NOT NULL, expires_at REAL NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, last_poll REAL, poll_interval INTEGER NOT NULL)",
    "CREATE TABLE auth_audit (id INTEGER PRIMARY KEY AUTOINCREMENT, occurred_at REAL NOT NULL, event TEXT NOT NULL, user_id INTEGER, device_id TEXT, session_id TEXT, target_id TEXT, reason TEXT)",
    "CREATE INDEX auth_audit_time ON auth_audit(occurred_at)",
    "CREATE TABLE auth_rates (bucket TEXT PRIMARY KEY, started_at REAL NOT NULL, attempts INTEGER NOT NULL)",
    "CREATE TABLE auth_nonces (token_hash TEXT PRIMARY KEY, expires_at REAL NOT NULL)",
)


def migrate(connection):
    for statement in STATEMENTS:
        connection.execute(statement)
