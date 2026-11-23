"""Owner/browser endpoints and a device grant based on RFC 8628 plus S256 proof."""
import asyncio
import hmac
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from server.api.routes import require_loopback
from server.security.gate import ACCESS_COOKIE, REFRESH_COOKIE, CSRF_COOKIE, csrf_value, require_permission
from server.security.types import AuthError, digest, token

router = APIRouter(dependencies=[Depends(require_loopback)])
STATIC = Path(__file__).resolve().parents[1] / "static"


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


def clean_name(value):
    value = value.strip()
    if not value or any(not character.isprintable() for character in value):
        raise ValueError("Invalid name")
    return value


class Login(Input):
    username: str = Field(min_length=1, max_length=64)
    password: SecretStr = Field(min_length=1, max_length=128)
    device_name: str = Field(default="Browser", min_length=1, max_length=80)
    _name = field_validator("device_name")(clean_name)


class Refresh(Input):
    refresh_token: SecretStr = Field(min_length=32, max_length=128)


class DesktopLogin(Login):
    device_id: UUID


class AndroidLogin(Login):
    code_challenge: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")


class Password(Input):
    current_password: SecretStr = Field(min_length=1, max_length=128)
    new_password: SecretStr = Field(min_length=12, max_length=128)
    revoke_all_sessions: bool | None = None


class Rename(Input):
    name: str = Field(min_length=1, max_length=80)
    _name = field_validator("name")(clean_name)


Scope = Literal["chat:read", "chat:write", "chat:delete", "status:read"]


class PairRequest(Input):
    device_name: str = Field(min_length=1, max_length=80)
    device_type: Literal["browser", "windows", "android", "other"]
    scopes: set[Scope] = Field(default_factory=lambda: {"chat:read", "chat:write"}, min_length=1, max_length=4)
    code_challenge: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")
    code_challenge_method: Literal["S256"]
    _name = field_validator("device_name")(clean_name)


class PairDecision(Input):
    approve: bool
    user_code: str = Field(default="", max_length=16, repr=False)
    scopes: set[Scope] = Field(default_factory=set, max_length=4)


class PairToken(Input):
    grant_type: Literal["urn:ietf:params:oauth:grant-type:device_code"]
    device_code: SecretStr = Field(min_length=32, max_length=128)
    code_verifier: str = Field(pattern=r"^[A-Za-z0-9._~-]{43,128}$", repr=False)


def service(request):
    return request.app.state.security


async def public_rate(request, prefix, maximum=None):
    security = service(request)
    await asyncio.to_thread(security.store.rate, prefix + ":" + digest(request.client.host), maximum or security.settings.auth_requests_per_minute)


def secure_cookie(request):
    if request.url.scheme != "https" and request.url.hostname not in ("127.0.0.1", "localhost"):
        raise AuthError("https_required", "Gebruik HTTPS voor deze servernaam.", 403)
    return service(request).settings.cookie_secure == "true" or request.url.scheme == "https"


def set_credentials(response, request, credentials):
    common = {"secure": secure_cookie(request), "samesite": "strict"}
    response.set_cookie("jarvis_device", credentials.principal.device_id, max_age=service(request).settings.session_seconds, httponly=True, path="/", **common)
    response.set_cookie(ACCESS_COOKIE, credentials.access_token, max_age=credentials.expires_in, httponly=True, path="/", **common)
    remaining = max(0, int(credentials.principal.session_expires_at - service(request).store.clock()))
    response.set_cookie(REFRESH_COOKIE, credentials.refresh_token, max_age=min(remaining, service(request).settings.refresh_seconds), httponly=True, path="/api/v1/auth", **common)
    response.set_cookie(CSRF_COOKIE, credentials.csrf_token, max_age=remaining, httponly=False, path="/", **common)


def clear_credentials(response, request):
    for name, path in ((ACCESS_COOKIE, "/"), (REFRESH_COOKIE, "/api/v1/auth"), (CSRF_COOKIE, "/")):
        response.delete_cookie(name, path=path, secure=secure_cookie(request), httponly=name != CSRF_COOKIE, samesite="strict")


@router.get("/api/v1/auth/status")
async def setup_status(request: Request):
    await public_rate(request, "setup-status")
    return {"setup_required": not bool(await asyncio.to_thread(service(request).store.owner))}


@router.get("/api/v1/auth/csrf")
async def csrf(request: Request):
    await public_rate(request, "csrf")
    security = service(request)
    try:
        principal = await asyncio.to_thread(security.store.authenticate, request.cookies.get(ACCESS_COOKIE, ""))
    except AuthError:
        value = await asyncio.to_thread(security.store.nonce)
    else:
        value = token()
        await asyncio.to_thread(security.store.bind_csrf, principal, value)
    response = JSONResponse({"status": "ready"})
    response.set_cookie(CSRF_COOKIE, value, max_age=600, httponly=False, secure=secure_cookie(request), samesite="strict", path="/")
    return response


@router.post("/api/v1/auth/login")
async def login(request: Request, body: Login):
    value = csrf_value(request.scope)
    if not await asyncio.to_thread(service(request).store.valid_nonce, value):
        try:
            principal = await asyncio.to_thread(service(request).store.authenticate, request.cookies.get(ACCESS_COOKIE, ""))
        except AuthError:
            raise AuthError("csrf_failed", "Vernieuw de pagina en probeer opnieuw.", 403) from None
        if not hmac.compare_digest(principal.csrf_hash, digest(value)):
            raise AuthError("csrf_failed", "Vernieuw de pagina en probeer opnieuw.", 403)
    credentials = await service(request).login(body.username, body.password.get_secret_value(), body.device_name, request.client.host, request.cookies.get("jarvis_device"))
    response = JSONResponse(credentials.principal.public())
    set_credentials(response, request, credentials)
    return response


@router.get("/api/v1/auth/session")
async def me(request: Request):
    return request.state.principal.public()


@router.post("/api/v1/auth/desktop-login")
async def desktop_login(request: Request, body: DesktopLogin):
    if request.cookies.get(ACCESS_COOKIE) or request.cookies.get(REFRESH_COOKIE):
        raise AuthError("csrf_failed", "Gebruik de browserlogin voor een browsersessie.", 403)
    credentials = await service(request).login(body.username, body.password.get_secret_value(), body.device_name,
                                             request.client.host, str(body.device_id), desktop=True)
    return credentials.native()


@router.post("/api/v1/auth/android-login")
async def android_login(request: Request, body: AndroidLogin):
    if request.cookies.get(ACCESS_COOKIE) or request.cookies.get(REFRESH_COOKIE):
        raise AuthError("csrf_failed", "Gebruik de browserlogin voor een browsersessie.", 403)
    security = service(request)
    _, bucket = await security.verify_owner(body.username, body.password.get_secret_value(), request.client.host)
    await public_rate(request, "pair-request", 5)
    result = await asyncio.to_thread(security.store.request_pair, body.device_name, "android",
                                    {"chat:read", "chat:write", "chat:delete", "status:read"}, body.code_challenge)
    await asyncio.to_thread(security.store.reset_rate, bucket)
    result["verification_uri"] = str(request.base_url).rstrip("/") + "/security"
    return result


@router.post("/api/v1/auth/refresh")
async def refresh_browser(request: Request):
    await public_rate(request, "refresh")
    value = csrf_value(request.scope)
    refresh_token = request.cookies.get(REFRESH_COOKIE, "")
    if not 32 <= len(refresh_token) <= 128:
        raise AuthError()
    try:
        credentials = await asyncio.to_thread(service(request).store.refresh, refresh_token, digest(value))
    except AuthError as error:
        response = JSONResponse({"error": {"code": error.code, "message": error.message}}, status_code=error.status)
        if error.status == 401:
            clear_credentials(response, request)
        return response
    response = JSONResponse(credentials.principal.public())
    set_credentials(response, request, credentials)
    return response


@router.post("/api/v1/auth/token")
async def refresh_native(request: Request, body: Refresh):
    if request.cookies.get(ACCESS_COOKIE) or request.cookies.get(REFRESH_COOKIE):
        raise AuthError("csrf_failed", "Gebruik de browserroute voor deze sessie.", 403)
    await public_rate(request, "refresh")
    result = await asyncio.to_thread(service(request).store.refresh, body.refresh_token.get_secret_value())
    return result.native()


@router.post("/api/v1/auth/logout")
async def logout(request: Request):
    principal = request.state.principal
    await asyncio.to_thread(service(request).store.revoke_session, principal.session_id, principal, "logout")
    response = JSONResponse({"status": "logged_out"})
    clear_credentials(response, request)
    return response


@router.get("/api/v1/auth/device")
async def own_device(request: Request):
    return await asyncio.to_thread(service(request).store.own_device, request.state.principal)


@router.post("/api/v1/auth/disconnect")
async def disconnect_device(request: Request):
    principal = request.state.principal
    await asyncio.to_thread(service(request).store.change_device, principal.device_id, principal)
    response = JSONResponse({"status": "revoked"})
    if request.state.auth_via_cookie:
        clear_credentials(response, request)
    return response


@router.get("/api/v1/auth/sessions", dependencies=[Depends(require_permission("admin:sessions"))])
async def sessions(request: Request):
    return await asyncio.to_thread(service(request).store.sessions, request.state.principal)


@router.delete("/api/v1/auth/sessions/{identifier}", dependencies=[Depends(require_permission("admin:sessions"))])
async def revoke_session(request: Request, identifier: UUID):
    await asyncio.to_thread(service(request).store.revoke_session, str(identifier), request.state.principal)
    response = JSONResponse({"status": "revoked"})
    if str(identifier) == request.state.principal.session_id:
        clear_credentials(response, request)
    return response


@router.post("/api/v1/auth/password", dependencies=[Depends(require_permission("admin:account"))])
async def password(request: Request, body: Password):
    revoked = await service(request).change_password(request.state.principal, body.current_password.get_secret_value(), body.new_password.get_secret_value(), body.revoke_all_sessions)
    response = JSONResponse({"status": "password_changed", "all_sessions_revoked": revoked})
    if revoked:
        clear_credentials(response, request)
    return response


@router.get("/api/v1/devices", dependencies=[Depends(require_permission("admin:devices"))])
async def devices(request: Request):
    return await asyncio.to_thread(service(request).store.devices)


@router.patch("/api/v1/devices/{identifier}", dependencies=[Depends(require_permission("admin:devices"))])
async def rename_device(request: Request, identifier: UUID, body: Rename):
    await asyncio.to_thread(service(request).store.change_device, str(identifier), request.state.principal, body.name)
    return {"status": "renamed"}


@router.post("/api/v1/devices/{identifier}/revoke", dependencies=[Depends(require_permission("admin:devices"))])
async def revoke_device(request: Request, identifier: UUID):
    await asyncio.to_thread(service(request).store.change_device, str(identifier), request.state.principal)
    response = JSONResponse({"status": "revoked"})
    if str(identifier) == request.state.principal.device_id:
        clear_credentials(response, request)
    return response


@router.delete("/api/v1/devices/{identifier}", dependencies=[Depends(require_permission("admin:devices"))])
async def remove_device(request: Request, identifier: UUID):
    await asyncio.to_thread(service(request).store.remove_device, str(identifier), request.state.principal)
    response = JSONResponse({"status": "deleted"})
    if str(identifier) == request.state.principal.device_id:
        clear_credentials(response, request)
    return response


@router.post("/api/v1/pairing/requests")
async def request_pair(request: Request, body: PairRequest):
    await public_rate(request, "pair-request", 5)
    result = await asyncio.to_thread(service(request).store.request_pair, body.device_name, body.device_type, body.scopes, body.code_challenge)
    result["verification_uri"] = str(request.base_url).rstrip("/") + "/security"
    return result


@router.get("/api/v1/pairing/requests", dependencies=[Depends(require_permission("admin:devices"))])
async def pairs(request: Request):
    return await asyncio.to_thread(service(request).store.pairs)


@router.post("/api/v1/pairing/requests/{identifier}/decision", dependencies=[Depends(require_permission("admin:devices"))])
async def decide_pair(request: Request, identifier: UUID, body: PairDecision):
    await asyncio.to_thread(service(request).store.rate, "pair-approval:" + request.state.principal.session_id, 20)
    await asyncio.to_thread(service(request).store.decide_pair, str(identifier), request.state.principal, body.approve, body.user_code, body.scopes)
    return {"status": "approved" if body.approve else "denied"}


@router.post("/api/v1/pairing/token")
async def pair_token(request: Request, body: PairToken):
    if request.cookies.get(ACCESS_COOKIE) or request.cookies.get(REFRESH_COOKIE):
        raise AuthError("csrf_failed", "Gebruik een afzonderlijke nieuwe client voor koppeling.", 403)
    await public_rate(request, "pair-poll")
    result = await asyncio.to_thread(service(request).store.redeem_pair, body.device_code.get_secret_value(), body.code_verifier)
    return result.native()


@router.get("/api/v1/security/audit", dependencies=[Depends(require_permission("audit:read"))])
async def audit(request: Request, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0, le=10000)):
    return await asyncio.to_thread(service(request).store.audits, limit, offset)


@router.get("/login", include_in_schema=False)
async def login_page():
    return FileResponse(STATIC / "login.html")


@router.get("/security", include_in_schema=False)
async def security_page():
    return FileResponse(STATIC / "security.html")
