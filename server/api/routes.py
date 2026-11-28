import ipaddress
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from server import __version__

health_router = APIRouter(tags=["health"])
api_router = APIRouter(prefix="/api/v1", tags=["status"])
logger = logging.getLogger("jarvis.server")


def require_client_access(request:Request)->None:
    if bool(request.app.state.settings.public_origin) and request.scope.get('jarvis.trusted_https') is True:return
    require_loopback(request)


def require_loopback(request: Request) -> None:
    try:
        local = request.client is not None and ipaddress.ip_address(request.client.host).is_loopback
    except ValueError:
        local = False
    if not local:
        raise HTTPException(status_code=403)


@health_router.get("/health")
def health():
    return {"status": "ok", "service": "jarvis-server"}


@health_router.get("/ready")
def ready(request: Request):
    runtime = request.app.state.runtime
    available = runtime["ready"] and runtime["database"].check()
    if not available:
        logger.warning("readiness_failed")
    return JSONResponse(
        {"status": "ready" if available else "not_ready", "service": "jarvis-server"},
        status_code=200 if available else 503,
    )


@api_router.get("/status", dependencies=[Depends(require_client_access)])
def status(request: Request):
    runtime = request.app.state.runtime
    settings = request.app.state.settings
    ollama = request.app.state.chat.router.providers.get("ollama")
    snapshot = getattr(ollama, "_availability", None)
    database_ready = runtime["ready"] and runtime["database"].check()
    return {
        "status": "running" if database_ready else "degraded",
        "service": "jarvis-server",
        "version": __version__,
        "instance_id": runtime["instance_id"],
        "uptime_seconds": round(max(0, time.monotonic() - runtime["started_at"]), 3),
        "environment": settings.environment,
        "components": {"api": True, "database": bool(database_ready), "ai": hasattr(request.app.state, "chat")},
        "ai_providers": {
            "selected": settings.ai_provider,
            "gemini": {"configured": bool(settings.gemini_api_key), "available": None if settings.gemini_api_key else False},
            "groq": {"configured": bool(settings.groq_api_key), "available": None if settings.groq_api_key else False},
            "ollama": {"configured": True, "available": snapshot[1]["available"] if snapshot else None},
        },
    }
