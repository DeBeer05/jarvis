import base64
import hashlib
import secrets
from dataclasses import dataclass, field

AUTH_SCHEME = "Bearer"
OWNER_SCOPES = frozenset(("chat:read", "chat:write", "chat:delete", "status:read", "admin:devices", "admin:sessions", "admin:account", "audit:read", "automation:read", "automation:write", "automation:approve", "integrations:manage"))
DEVICE_SCOPES = frozenset(("chat:read", "chat:write", "chat:delete", "status:read"))
DEVICE_TYPES = frozenset(("browser", "windows", "android", "other"))


class AuthError(Exception):
    def __init__(self, code="authentication_required", message="Log opnieuw in om verder te gaan.", status=401):
        super().__init__(code)
        self.code, self.message, self.status = code, message, status


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def token() -> str:
    return secrets.token_urlsafe(32)


def pkce(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")


@dataclass(repr=False)
class Principal:
    session_id: str
    device_id: str
    username: str
    permissions: frozenset[str]
    access_expires_at: float
    session_expires_at: float
    csrf_hash: str = field(repr=False)

    def public(self):
        return {"session_id": self.session_id, "device_id": self.device_id,
                "username": self.username, "permissions": sorted(self.permissions),
                "access_expires_at": self.access_expires_at, "session_expires_at": self.session_expires_at}


@dataclass(repr=False)
class Credentials:
    principal: Principal
    access_token: str
    refresh_token: str
    csrf_token: str
    expires_in: int

    def native(self):
        return {"token_type": AUTH_SCHEME, "access_token": self.access_token,
                "refresh_token": self.refresh_token, "expires_in": self.expires_in,
                "scope": " ".join(sorted(self.principal.permissions)),
                "session_id": self.principal.session_id, "device_id": self.principal.device_id}
