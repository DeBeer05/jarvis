"""Transactional authentication state. Plaintext credentials never enter SQLite."""
import hmac
import json
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager

from server.security.types import AuthError, Credentials, Principal, OWNER_SCOPES, DEVICE_SCOPES, DEVICE_TYPES, digest, pkce, token


class SecurityStore:
    MAX_REFRESH_ROTATIONS = 4096
    def __init__(self, database, settings, clock=time.time):
        self.database, self.settings, self.clock = database, settings, clock

    @contextmanager
    def db(self, write=False):
        with self.database.connection() as connection:
            connection.row_factory = sqlite3.Row
            if write:
                connection.execute("BEGIN IMMEDIATE")
            yield connection

    def _audit(self, db, event, principal=None, target=None, reason=None):
        db.execute("INSERT INTO auth_audit(occurred_at,event,user_id,device_id,session_id,target_id,reason) VALUES (?,?,?,?,?,?,?)",
                   (self.clock(), event, 1 if principal else None, principal.device_id if principal else None,
                    principal.session_id if principal else None, target, reason))
        db.execute("DELETE FROM auth_audit WHERE occurred_at < ?", (self.clock() - self.settings.audit_days * 86400,))
        db.execute("DELETE FROM auth_audit WHERE id IN (SELECT id FROM auth_audit ORDER BY id DESC LIMIT -1 OFFSET ?)", (self.settings.audit_max_entries,))

    def audit(self, event, principal=None, target=None, reason=None):
        with self.db() as db:
            self._audit(db, event, principal, target, reason)

    def rate(self, bucket, maximum, window=60):
        now = self.clock()
        with self.db(True) as db:
            db.execute("DELETE FROM auth_rates WHERE started_at < ?", (now - 86400,))
            row = db.execute("SELECT * FROM auth_rates WHERE bucket=?", (bucket,)).fetchone()
            count = row["attempts"] + 1 if row and now - row["started_at"] < window else 1
            started = row["started_at"] if row and count != 1 else now
            db.execute("INSERT INTO auth_rates VALUES (?,?,?) ON CONFLICT(bucket) DO UPDATE SET started_at=excluded.started_at,attempts=excluded.attempts", (bucket, started, count))
        if count > maximum:
            raise AuthError("rate_limited", "Te veel pogingen. Wacht even en probeer opnieuw.", 429)

    def reset_rate(self, bucket):
        with self.db() as db:
            db.execute("DELETE FROM auth_rates WHERE bucket=?", (bucket,))

    def prune(self):
        with self.db(True) as db:
            for permission in ("automation:read", "automation:write", "automation:approve", "integrations:manage"):
                db.execute("INSERT OR IGNORE INTO auth_permissions(device_id,permission) SELECT device_id,? FROM auth_permissions WHERE permission='admin:account'", (permission,))
            db.execute("INSERT OR IGNORE INTO auth_permissions(device_id,permission) SELECT d.id,'chat:delete' FROM auth_devices d JOIN auth_permissions p ON p.device_id=d.id WHERE d.type='browser' AND p.permission='admin:account'")
            cutoff = self.clock() - 86400
            db.execute("DELETE FROM auth_refresh_tokens WHERE session_id IN (SELECT id FROM auth_sessions WHERE expires_at<? OR revoked_at<?)", (cutoff, cutoff))
            db.execute("DELETE FROM auth_sessions WHERE expires_at<? OR revoked_at<?", (cutoff, cutoff))
            db.execute("DELETE FROM auth_nonces WHERE expires_at<?", (self.clock(),))
            db.execute("DELETE FROM auth_rates WHERE started_at<?", (cutoff,))
            db.execute("DELETE FROM auth_pairing WHERE expires_at<?", (cutoff,))
            db.execute("DELETE FROM auth_audit WHERE occurred_at<?", (self.clock() - self.settings.audit_days * 86400,))

    def _require_live(self, db, principal):
        row = db.execute("SELECT 1 FROM auth_sessions s JOIN auth_devices d ON d.id=s.device_id WHERE s.id=? AND s.revoked_at IS NULL AND s.expires_at>? AND s.access_expires_at>? AND d.revoked_at IS NULL AND d.trusted=1", (principal.session_id, self.clock(), self.clock())).fetchone()
        if not row:
            raise AuthError()

    def bind_csrf(self, principal, value):
        with self.db(True) as db:
            self._require_live(db, principal)
            db.execute("UPDATE auth_sessions SET csrf_hash=? WHERE id=? AND revoked_at IS NULL", (digest(value), principal.session_id))

    def owner(self):
        with self.db() as db:
            row = db.execute("SELECT * FROM auth_users WHERE id=1").fetchone()
        return dict(row) if row else None

    def create_owner(self, username, password_hash):
        if not password_hash.startswith("$argon2id$"):
            raise ValueError("Argon2id hash required")
        with self.db(True) as db:
            if db.execute("SELECT 1 FROM auth_users").fetchone():
                raise AuthError("owner_exists", "De lokale eigenaar is al ingesteld.", 409)
            db.execute("INSERT INTO auth_users VALUES (1,?,?,?)", (username, password_hash, self.clock()))
            self._audit(db, "owner_created")

    def nonce(self):
        value = token()
        with self.db(True) as db:
            db.execute("DELETE FROM auth_nonces WHERE expires_at < ?", (self.clock(),))
            db.execute("DELETE FROM auth_nonces WHERE token_hash IN (SELECT token_hash FROM auth_nonces ORDER BY expires_at DESC LIMIT -1 OFFSET 255)")
            db.execute("INSERT INTO auth_nonces VALUES (?,?)", (digest(value), self.clock() + 600))
        return value

    def valid_nonce(self, value):
        with self.db() as db:
            row = db.execute("SELECT 1 FROM auth_nonces WHERE token_hash=? AND expires_at>?", (digest(value), self.clock())).fetchone()
        return bool(row)

    def _device(self, db, name, kind, scopes, identifier=None):
        if db.execute("SELECT count(*) FROM auth_devices WHERE revoked_at IS NULL").fetchone()[0] >= self.settings.max_devices:
            raise AuthError("device_limit", "De apparaatlimiet is bereikt. Trek eerst een oud apparaat in.", 409)
        identifier = identifier or str(uuid.uuid4())
        db.execute("INSERT INTO auth_devices(id,user_id,name,type,created_at,last_seen) VALUES (?,1,?,?,?,?)", (identifier, name, kind, self.clock(), self.clock()))
        db.executemany("INSERT INTO auth_permissions VALUES (?,?)", ((identifier, scope) for scope in scopes))
        return identifier

    def _credentials(self, db, device_id, session_id=None, *, session_seconds=None):
        now = self.clock()
        access, refresh, csrf = token(), token(), token()
        if session_id:
            row = db.execute("SELECT * FROM auth_sessions WHERE id=?", (session_id,)).fetchone()
            expires = row["expires_at"]
            db.execute("UPDATE auth_sessions SET access_hash=?,access_expires_at=?,csrf_hash=?,last_seen=? WHERE id=?",
                       (digest(access), min(now + self.settings.access_seconds, expires), digest(csrf), now, session_id))
        else:
            if db.execute("SELECT count(*) FROM auth_sessions WHERE revoked_at IS NULL AND expires_at>?", (now,)).fetchone()[0] >= self.settings.max_sessions:
                raise AuthError("session_limit", "De sessielimiet is bereikt. Trek eerst een oude sessie in.", 409)
            session_id, expires = str(uuid.uuid4()), now + (session_seconds or self.settings.session_seconds)
            db.execute("INSERT INTO auth_sessions(id,user_id,device_id,created_at,last_seen,expires_at,access_hash,access_expires_at,csrf_hash) VALUES (?,1,?,?,?,?,?,?,?)",
                       (session_id, device_id, now, now, expires, digest(access), min(now + self.settings.access_seconds, expires), digest(csrf)))
        db.execute("INSERT INTO auth_refresh_tokens(id,session_id,token_hash,issued_at,expires_at) VALUES (?,?,?,?,?)",
                   (str(uuid.uuid4()), session_id, digest(refresh), now, min(now + self.settings.refresh_seconds, expires)))
        principal = self._principal(db, session_id)
        return Credentials(principal, access, refresh, csrf, max(0, int(principal.access_expires_at - now)))

    def _principal(self, db, session_id):
        row = db.execute("SELECT s.*,u.username FROM auth_sessions s JOIN auth_users u ON u.id=s.user_id WHERE s.id=?", (session_id,)).fetchone()
        scopes = frozenset(r[0] for r in db.execute("SELECT permission FROM auth_permissions WHERE device_id=?", (row["device_id"],)))
        return Principal(session_id, row["device_id"], row["username"], scopes, row["access_expires_at"], row["expires_at"], row["csrf_hash"])

    def login(self, expected_hash, name, device_hint=None, *, desktop=False):
        with self.db(True) as db:
            row = db.execute("SELECT password_hash FROM auth_users WHERE id=1").fetchone()
            if not row or not hmac.compare_digest(row[0], expected_hash):
                raise AuthError("invalid_credentials", "Inloggen mislukt. Controleer je gegevens.")
            if desktop:
                previous = db.execute("SELECT id,type,revoked_at FROM auth_devices WHERE id=?", (device_hint,)).fetchone()
                if previous and previous["type"] != "windows":
                    raise AuthError("invalid_device", "Deze apparaatidentiteit kan niet worden gebruikt.", 409)
                if previous and previous["revoked_at"] is not None and db.execute("SELECT count(*) FROM auth_devices WHERE revoked_at IS NULL").fetchone()[0] >= self.settings.max_devices:
                    raise AuthError("device_limit", "De apparaatlimiet is bereikt. Trek eerst een oud apparaat in.", 409)
                device = previous[0] if previous else self._device(db, name, "windows", DEVICE_SCOPES, device_hint)
                # A successful owner-password check explicitly authorizes this device
                # again. IDs alone never authenticate; no administrative scopes here.
                db.execute("UPDATE auth_devices SET name=?,trusted=1,revoked_at=NULL WHERE id=?", (name, device))
                db.execute("DELETE FROM auth_permissions WHERE device_id=?", (device,))
                db.executemany("INSERT INTO auth_permissions VALUES (?,?)", ((device, scope) for scope in DEVICE_SCOPES))
            else:
                previous = db.execute("SELECT id FROM auth_devices WHERE id=? AND type='browser' AND trusted=1 AND revoked_at IS NULL", (device_hint,)).fetchone() if device_hint else None
                device = previous[0] if previous else self._device(db, name, "browser", OWNER_SCOPES)
            if previous:
                for old in db.execute("SELECT id FROM auth_sessions WHERE device_id=? AND revoked_at IS NULL", (device,)).fetchall():
                    self._revoke(db, old[0])
            credentials = self._credentials(db, device, session_seconds=self.settings.desktop_session_seconds if desktop else None)
            self._audit(db, "login_success", credentials.principal)
        return credentials

    def authenticate(self, access):
        now = self.clock()
        with self.db() as db:
            row = db.execute("SELECT s.id,s.last_seen FROM auth_sessions s JOIN auth_devices d ON d.id=s.device_id WHERE s.access_hash=? AND s.revoked_at IS NULL AND s.expires_at>? AND s.access_expires_at>? AND d.revoked_at IS NULL AND d.trusted=1", (digest(access), now, now)).fetchone()
            if not row:
                raise AuthError()
            principal = self._principal(db, row["id"])
            if now - row["last_seen"] >= 30:
                db.execute("UPDATE auth_sessions SET last_seen=? WHERE id=?", (now, principal.session_id))
                db.execute("UPDATE auth_devices SET last_seen=? WHERE id=?", (now, principal.device_id))
        return principal

    def live(self, principal):
        with self.db() as db:
            row = db.execute("SELECT 1 FROM auth_sessions s JOIN auth_devices d ON d.id=s.device_id WHERE s.id=? AND s.revoked_at IS NULL AND s.expires_at>? AND s.access_expires_at>? AND d.revoked_at IS NULL AND d.trusted=1", (principal.session_id, self.clock(), self.clock())).fetchone()
        return bool(row)

    def _revoke(self, db, session_id):
        db.execute("UPDATE auth_sessions SET revoked_at=coalesce(revoked_at,?) WHERE id=?", (self.clock(), session_id))
        db.execute("UPDATE auth_refresh_tokens SET revoked_at=coalesce(revoked_at,?) WHERE session_id=?", (self.clock(), session_id))

    def revoke_session(self, identifier, principal, event="session_revoked"):
        with self.db(True) as db:
            self._require_live(db, principal)
            if not db.execute("SELECT 1 FROM auth_sessions WHERE id=?", (identifier,)).fetchone():
                raise AuthError("not_found", "Sessies niet gevonden.", 404)
            self._revoke(db, identifier)
            self._audit(db, event, principal, identifier)

    def refresh(self, refresh_token, csrf_hash=None):
        failure = None
        result = None
        with self.db(True) as db:
            row = db.execute("SELECT r.*,s.device_id,s.expires_at AS session_expires,s.revoked_at AS session_revoked,s.csrf_hash,d.revoked_at AS device_revoked,d.trusted FROM auth_refresh_tokens r JOIN auth_sessions s ON s.id=r.session_id JOIN auth_devices d ON d.id=s.device_id WHERE r.token_hash=?", (digest(refresh_token),)).fetchone()
            if not row:
                failure = AuthError()
            elif row["consumed_at"] is not None:
                self._revoke(db, row["session_id"])
                self._audit(db, "refresh_reuse_detected", target=row["session_id"])
                failure = AuthError()
            elif csrf_hash is not None and not hmac.compare_digest(row["csrf_hash"], csrf_hash):
                failure = AuthError("csrf_failed", "Vernieuw de pagina en probeer opnieuw.", 403)
            elif row["revoked_at"] is not None or row["session_revoked"] is not None or row["device_revoked"] is not None or not row["trusted"] or self.clock() >= min(row["expires_at"], row["session_expires"]):
                failure = AuthError()
            elif db.execute("SELECT count(*) FROM auth_refresh_tokens WHERE session_id=?", (row["session_id"],)).fetchone()[0] >= self.MAX_REFRESH_ROTATIONS:
                self._revoke(db, row["session_id"])
                self._audit(db, "refresh_rotation_limit", target=row["session_id"])
                failure = AuthError()
            else:
                db.execute("UPDATE auth_refresh_tokens SET consumed_at=? WHERE id=?", (self.clock(), row["id"]))
                result = self._credentials(db, row["device_id"], row["session_id"])
                self._audit(db, "token_refreshed", result.principal)
        # Revocation must commit even though a replay receives an error.
        if failure:
            raise failure
        return result

    def password(self, old_hash, new_hash, principal, revoke_all):
        with self.db(True) as db:
            self._require_live(db, principal)
            row = db.execute("SELECT password_hash FROM auth_users WHERE id=1").fetchone()
            if not hmac.compare_digest(row[0], old_hash):
                raise AuthError("invalid_credentials", "De wijziging kon niet worden uitgevoerd.")
            db.execute("UPDATE auth_users SET password_hash=? WHERE id=1", (new_hash,))
            if revoke_all:
                for row in db.execute("SELECT id FROM auth_sessions WHERE revoked_at IS NULL").fetchall():
                    self._revoke(db, row[0])
            self._audit(db, "password_changed", principal, reason="all_sessions_revoked" if revoke_all else "sessions_retained")

    def sessions(self, principal):
        with self.db() as db:
            rows = db.execute("SELECT s.id,s.device_id,s.created_at,s.last_seen,s.expires_at,s.revoked_at,d.name AS device_name,d.type AS device_type FROM auth_sessions s JOIN auth_devices d ON d.id=s.device_id ORDER BY s.revoked_at IS NOT NULL,s.last_seen DESC,s.created_at DESC LIMIT 200").fetchall()
        return {"items": [{**dict(row), "current": row["id"] == principal.session_id} for row in rows]}

    def own_device(self, principal):
        with self.db(True) as db:
            self._require_live(db, principal)
            row = db.execute("SELECT id,name,type,created_at,last_seen,trusted,revoked_at FROM auth_devices WHERE id=?", (principal.device_id,)).fetchone()
            return {**dict(row), "permissions": sorted(principal.permissions)}

    def devices(self):
        with self.db() as db:
            rows = db.execute("SELECT * FROM auth_devices ORDER BY revoked_at IS NOT NULL,last_seen DESC,created_at DESC LIMIT 200").fetchall()
            items = []
            for row in rows:
                scopes = [r[0] for r in db.execute("SELECT permission FROM auth_permissions WHERE device_id=? ORDER BY permission", (row["id"],))]
                items.append({**dict(row), "permissions": scopes})
        return {"items": items}

    def change_device(self, identifier, principal, name=None):
        with self.db(True) as db:
            self._require_live(db, principal)
            if not db.execute("SELECT 1 FROM auth_devices WHERE id=?", (identifier,)).fetchone():
                raise AuthError("not_found", "Apparaat niet gevonden.", 404)
            if name is not None:
                db.execute("UPDATE auth_devices SET name=? WHERE id=?", (name, identifier))
                self._audit(db, "device_renamed", principal, identifier)
            else:
                db.execute("UPDATE auth_devices SET revoked_at=coalesce(revoked_at,?),trusted=0 WHERE id=?", (self.clock(), identifier))
                for row in db.execute("SELECT id FROM auth_sessions WHERE device_id=?", (identifier,)).fetchall():
                    self._revoke(db, row[0])
                self._audit(db, "device_revoked", principal, identifier)

    def request_pair(self, name, kind, scopes, challenge):
        if not scopes or not set(scopes) <= DEVICE_SCOPES or kind not in DEVICE_TYPES:
            raise AuthError("invalid_scope", "Deze apparaatrechten of dit apparaattype zijn niet toegestaan.", 422)
        identifier, device_code = str(uuid.uuid4()), token()
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        user_code = "".join(secrets.choice(alphabet) for _ in range(10))
        now = self.clock()
        with self.db(True) as db:
            if not db.execute("SELECT 1 FROM auth_users").fetchone():
                raise AuthError("setup_required", "Voer eerst de lokale eigenaarssetup uit.", 503)
            db.execute("DELETE FROM auth_pairing WHERE expires_at < ?", (now - 86400,))
            db.execute("UPDATE auth_pairing SET status='expired' WHERE expires_at<=? AND status IN ('pending','approved')", (now,))
            if db.execute("SELECT count(*) FROM auth_pairing WHERE status IN ('pending','approved')").fetchone()[0] >= 20:
                raise AuthError("busy", "Te veel open koppelverzoeken. Probeer later opnieuw.", 429)
            db.execute("INSERT INTO auth_pairing(id,device_hash,user_code_hash,challenge,name,type,requested_scopes,created_at,expires_at,status,poll_interval) VALUES (?,?,?,?,?,?,?,?,?,'pending',?)",
                       (identifier, digest(device_code), digest(user_code), challenge, name, kind, json.dumps(sorted(scopes)), now, now + self.settings.pairing_seconds, self.settings.pairing_poll_seconds))
            self._audit(db, "pairing_requested", target=identifier)
        return {"request_id": identifier, "device_code": device_code, "user_code": user_code[:5] + "-" + user_code[5:], "expires_in": self.settings.pairing_seconds, "interval": self.settings.pairing_poll_seconds}

    def remove_device(self, identifier, principal):
        with self.db(True) as db:
            self._require_live(db, principal)
            if not db.execute("SELECT 1 FROM auth_devices WHERE id=?", (identifier,)).fetchone():
                raise AuthError("not_found", "Apparaat niet gevonden.", 404)
            self._audit(db, "device_deleted", principal, identifier)
            db.execute("DELETE FROM auth_refresh_tokens WHERE session_id IN (SELECT id FROM auth_sessions WHERE device_id=?)", (identifier,))
            db.execute("DELETE FROM auth_sessions WHERE device_id=?", (identifier,))
            db.execute("DELETE FROM auth_permissions WHERE device_id=?", (identifier,))
            db.execute("DELETE FROM auth_devices WHERE id=?", (identifier,))

    def pairs(self):
        with self.db() as db:
            rows = db.execute("SELECT id,name,type,requested_scopes,created_at,expires_at,status FROM auth_pairing WHERE status IN ('pending','approved') AND expires_at>? ORDER BY created_at", (self.clock(),)).fetchall()
        return {"items": [{**dict(row), "requested_scopes": json.loads(row["requested_scopes"])} for row in rows]}

    def decide_pair(self, identifier, principal, approved, user_code, scopes):
        failure = None
        with self.db(True) as db:
            self._require_live(db, principal)
            row = db.execute("SELECT * FROM auth_pairing WHERE id=?", (identifier,)).fetchone()
            if not row or row["status"] != "pending" or row["expires_at"] <= self.clock():
                failure = AuthError("invalid_pairing", "Dit koppelverzoek is niet meer geldig.", 409)
            elif not approved:
                db.execute("UPDATE auth_pairing SET status='denied' WHERE id=?", (identifier,))
                self._audit(db, "pairing_denied", principal, identifier)
            elif not hmac.compare_digest(row["user_code_hash"], digest(user_code.replace("-", "").upper())):
                db.execute("UPDATE auth_pairing SET attempts=attempts+1,status=CASE WHEN attempts>=4 THEN 'denied' ELSE status END WHERE id=?", (identifier,))
                self._audit(db, "pairing_code_rejected", principal, identifier)
                failure = AuthError("invalid_pairing", "De getoonde apparaatcode komt niet overeen.", 400)
            elif not scopes or not set(scopes) <= set(json.loads(row["requested_scopes"])):
                failure = AuthError("invalid_scope", "Kies alleen de aangevraagde rechten.", 422)
            else:
                db.execute("UPDATE auth_pairing SET status='approved',approved_scopes=? WHERE id=?", (json.dumps(sorted(scopes)), identifier))
                self._audit(db, "pairing_approved", principal, identifier)
        if failure:
            raise failure

    def redeem_pair(self, device_code, verifier):
        failure, result = None, None
        now = self.clock()
        with self.db(True) as db:
            row = db.execute("SELECT * FROM auth_pairing WHERE device_hash=?", (digest(device_code),)).fetchone()
            if not row or row["status"] == "consumed":
                failure = AuthError("invalid_grant", "Deze koppeling is niet geldig.", 400)
            elif row["expires_at"] <= now:
                failure = AuthError("expired_token", "Het koppelverzoek is verlopen.", 400)
            elif row["status"] == "denied":
                failure = AuthError("access_denied", "Het koppelverzoek is geweigerd.", 400)
            elif not hmac.compare_digest(row["challenge"], pkce(verifier)):
                db.execute("UPDATE auth_pairing SET attempts=attempts+1,status=CASE WHEN attempts>=4 THEN 'denied' ELSE status END WHERE id=?", (row["id"],))
                self._audit(db, "pairing_proof_rejected", target=row["id"])
                failure = AuthError("invalid_grant", "Deze koppeling is niet geldig.", 400)
            elif row["last_poll"] is not None and now - row["last_poll"] < row["poll_interval"]:
                db.execute("UPDATE auth_pairing SET last_poll=?,poll_interval=min(poll_interval+5,30) WHERE id=?", (now, row["id"]))
                failure = AuthError("slow_down", "Wacht langer voordat je de koppelstatus opnieuw opvraagt.", 400)
            elif row["status"] == "pending":
                db.execute("UPDATE auth_pairing SET last_poll=? WHERE id=?", (now, row["id"]))
                failure = AuthError("authorization_pending", "Wacht op goedkeuring door de eigenaar.", 400)
            else:
                device = self._device(db, row["name"], row["type"], json.loads(row["approved_scopes"]))
                result = self._credentials(db, device)
                db.execute("UPDATE auth_pairing SET status='consumed' WHERE id=?", (row["id"],))
                self._audit(db, "device_paired", result.principal, row["id"])
        if failure:
            raise failure
        return result

    def audits(self, limit, offset):
        with self.db() as db:
            db.execute("DELETE FROM auth_audit WHERE occurred_at<?", (self.clock() - self.settings.audit_days * 86400,))
            rows = db.execute("SELECT * FROM auth_audit ORDER BY id DESC LIMIT ? OFFSET ?", (limit + 1, offset)).fetchall()
        return {"items": [dict(row) for row in rows[:limit]], "has_more": len(rows) > limit}
