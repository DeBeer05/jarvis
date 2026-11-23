import asyncio
import re
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError, InvalidHashError

from server.security.store import SecurityStore
from server.security.types import AuthError, digest, token


class SecurityService:
    def __init__(self, database, settings, *, clock=None, hasher=None):
        self.settings = settings
        self.store = SecurityStore(database, settings, **({"clock": clock} if clock else {}))
        self.hasher = hasher or PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2, type=Type.ID)
        self.hash_slots = asyncio.Semaphore(2)
        # Same expensive verification path for unknown and existing usernames.
        self.dummy_hash = None

    def initialize(self):
        self.store.prune()
        self.dummy_hash = self.hasher.hash(token())

    @staticmethod
    def validate_password(password):
        if not 12 <= len(password) <= 128 or "\0" in password:
            raise AuthError("invalid_password", "Gebruik een wachtwoord van 12 tot en met 128 tekens.", 422)

    def setup_owner(self, username, password):
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", username):
            raise AuthError("invalid_username", "Gebruik 1 tot 64 letters, cijfers, punten of streepjes.", 422)
        self.validate_password(password)
        self.store.create_owner(username, self.hasher.hash(password))

    def verify(self, encoded, password):
        try:
            return self.hasher.verify(encoded, password)
        except (VerificationError, InvalidHashError):
            return False

    async def login(self, username, password, name, client_key, device_hint=None, *, desktop=False):
        encoded, bucket = await self.verify_owner(username, password, client_key)
        result = await asyncio.to_thread(self.store.login, encoded, name, device_hint, desktop=desktop)
        await asyncio.to_thread(self.store.reset_rate, bucket)
        return result

    async def verify_owner(self, username, password, client_key):
        bucket = "login:" + digest(client_key)
        await asyncio.to_thread(self.store.rate, bucket, self.settings.login_attempts, self.settings.login_window_seconds)
        owner = await asyncio.to_thread(self.store.owner)
        encoded = owner["password_hash"] if owner and owner["username"] == username else self.dummy_hash
        async with self.hash_slots:
            valid = await asyncio.to_thread(self.verify, encoded, password)
        if not valid or not owner or owner["username"] != username:
            await asyncio.to_thread(self.store.audit, "login_failed")
            raise AuthError("invalid_credentials", "Inloggen mislukt. Controleer je gegevens.")
        return encoded, bucket

    async def change_password(self, principal, current, new, revoke_all=None):
        self.validate_password(new)
        await asyncio.to_thread(self.store.rate, "password:" + principal.session_id, self.settings.login_attempts, self.settings.login_window_seconds)
        owner = await asyncio.to_thread(self.store.owner)
        async with self.hash_slots:
            valid = await asyncio.to_thread(self.verify, owner["password_hash"], current)
            encoded = await asyncio.to_thread(self.hasher.hash, new) if valid else None
        if not valid:
            await asyncio.to_thread(self.store.audit, "password_change_failed", principal)
            raise AuthError("invalid_credentials", "De wijziging kon niet worden uitgevoerd.")
        revoke = self.settings.password_revoke_all if revoke_all is None else revoke_all
        await asyncio.to_thread(self.store.password, owner["password_hash"], encoded, principal, revoke)
        return revoke
