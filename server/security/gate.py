"""Default-deny access gate for all routes, including newly added API routers."""
import asyncio
import hmac
import ipaddress
import re
import sqlite3
from http.cookies import SimpleCookie, CookieError

from starlette.responses import JSONResponse

from server.security.types import AuthError, digest

ACCESS_COOKIE = "jarvis_access"
REFRESH_COOKIE = "jarvis_refresh"
CSRF_COOKIE = "jarvis_csrf"

PUBLIC = {
    "/automations": {"GET"}, "/chat/assets/automations.js": {"GET"},
    "/oauth/google/callback": {"GET"},
    "/health": {"GET", "HEAD"}, "/ready": {"GET", "HEAD"},
    "/chat": {"GET"}, "/login": {"GET"}, "/security": {"GET"},
    "/chat/assets/chat.css": {"GET"}, "/chat/assets/chat.js": {"GET"},
    "/chat/assets/auth.js": {"GET"}, "/chat/assets/login.js": {"GET"},
    "/chat/assets/security.js": {"GET"},
    "/api/v1/auth/status": {"GET"}, "/api/v1/auth/csrf": {"GET"},
    "/api/v1/auth/login": {"POST"}, "/api/v1/auth/refresh": {"POST"},
    "/api/v1/auth/desktop-login": {"POST"},
    "/api/v1/auth/android-login": {"POST"},
    "/api/v1/auth/token": {"POST"},
    "/api/v1/pairing/requests": {"POST"}, "/api/v1/pairing/token": {"POST"},
    "/internal/status": {"GET"}, "/internal/shutdown": {"POST"},
}


def cookies(scope):
    jar = SimpleCookie()
    try:
        for key, value in scope.get("headers", []):
            if key == b"cookie":
                jar.load(value.decode("latin-1"))
    except CookieError:
        return {}
    return {key: value.value for key, value in jar.items()}


def csrf_value(scope):
    headers = dict(scope.get("headers", []))
    cookie = cookies(scope).get(CSRF_COOKIE, "")
    supplied = headers.get(b"x-jarvis-csrf", b"").decode("latin-1")
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", cookie) or not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", supplied) or not hmac.compare_digest(cookie, supplied):
        raise AuthError("csrf_failed", "Vernieuw de pagina en probeer opnieuw.", 403)
    return cookie


class SecurityGate:
    def __init__(self, app, service):
        self.app, self.service = app, service

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path, method = scope["path"], scope["method"]
        if method in PUBLIC.get(path, ()):
            return await self.app(scope, receive, send)
        try:
            address = scope.get("client")
            if not address or not ipaddress.ip_address(address[0]).is_loopback:
                raise AuthError("access_denied", "Toegang geweigerd.", 403)
            values = dict(scope.get("headers", []))
            bearer = values.get(b"authorization", b"").decode("latin-1")
            via_cookie = not bearer
            access = cookies(scope).get(ACCESS_COOKIE, "") if via_cookie else bearer.removeprefix("Bearer ") if bearer.startswith("Bearer ") else ""
            if not 32 <= len(access) <= 128:
                raise AuthError()
            principal = await asyncio.to_thread(self.service.store.authenticate, access)
            if via_cookie and method not in ("GET", "HEAD", "OPTIONS"):
                if not hmac.compare_digest(principal.csrf_hash, digest(csrf_value(scope))):
                    raise AuthError("csrf_failed", "Vernieuw de pagina en probeer opnieuw.", 403)
            if path.startswith("/api/v1/automation"):
                if path.endswith("/grants"): required = "admin:devices"
                elif path.endswith("/rules"): required = "admin:account"
                elif "/integrations" in path: required = "integrations:manage"
                elif path.endswith(("/challenge", "/decision")): required = "automation:approve"
                elif method in ("GET", "HEAD") or path.endswith(("/calendar/search", "/email/search", "/reschedule", "/summarize", "/email-priority")): required = "automation:read"
                else: required = "automation:write"
            elif path == "/api/v1/mobile/speech/transcribe":
                required = "chat:write"
            elif path == "/api/v1/mobile/speech/synthesize":
                required = "chat:read"
            elif path == "/api/v1/mobile/push":
                required = "status:read"
            elif path.startswith("/api/v1/natural/"):
                required = "status:read" if path.startswith("/api/v1/natural/diagnostics") else "chat:read" if method in ("GET","HEAD") or path.endswith("/memory/search") else "chat:write"
            elif path.startswith("/api/v1/chat"):
                required = "chat:read" if method in ("GET", "HEAD") else "chat:delete" if method == "DELETE" else "chat:write"
            elif path in ("/api/v1/status", "/api/v1/ai/providers"):
                required = "status:read"
            elif path in ("/api/v1/auth/session", "/api/v1/auth/logout", "/api/v1/auth/device", "/api/v1/auth/disconnect"):
                required = None
            elif path.startswith("/api/v1/auth/sessions"):
                required = "admin:sessions"
            elif path.startswith(("/api/v1/devices", "/api/v1/pairing")):
                required = "admin:devices"
            elif path.startswith("/api/v1/security/audit"):
                required = "audit:read"
            else:
                required = "admin:account"
            if required and required not in principal.permissions:
                raise AuthError("permission_denied", "Dit apparaat heeft hiervoor geen rechten.", 403)
            scope.setdefault("state", {})["principal"] = principal
            scope["state"]["auth_via_cookie"] = via_cookie
        except AuthError as error:
            try:
                address = scope.get("client")
                await asyncio.to_thread(self.service.store.rate, "denied:" + digest(address[0] if address else "unknown"), 120)
                await asyncio.to_thread(self.service.store.audit, "access_denied", reason=error.code)
            except (AuthError, sqlite3.Error):
                pass
            return await JSONResponse({"error": {"code": error.code, "message": error.message}}, status_code=error.status, headers={"WWW-Authenticate": "Bearer"} if error.status == 401 else {})(scope, receive, send)
        except (ValueError, sqlite3.Error):
            return await JSONResponse({"error": {"code": "authentication_unavailable", "message": "Aanmelden is tijdelijk niet beschikbaar."}}, status_code=503)(scope, receive, send)
        return await self.app(scope, receive, send)


def require_permission(permission):
    from fastapi import Request

    async def check(request: Request):
        principal = getattr(request.state, "principal", None)
        if principal is None:
            raise AuthError()
        if permission not in principal.permissions:
            await asyncio.to_thread(request.app.state.security.store.audit, "access_denied", principal, reason="permission_denied")
            raise AuthError("permission_denied", "Dit apparaat heeft hiervoor geen rechten.", 403)
        return principal
    return check
