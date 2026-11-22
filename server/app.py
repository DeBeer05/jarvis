"""App factory and resource lifetime; no GUI, device or provider imports."""

import hmac
import logging
import secrets
import time
from contextlib import asynccontextmanager
from http import HTTPStatus
from typing import Callable

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from server import __version__
from server.api.routes import api_router, health_router, require_loopback
from server.config import Settings, load_settings
from server.database import Database, SCHEMA_VERSION
from server.ai.router import AIRouter
from server.chat_store import ChatError, ChatStore
from server.chat_service import ChatService
from server.api.chat import router as chat_router
from server.http_security import RequestGuard

logger = logging.getLogger("jarvis.server")


def create_app(
    settings: Settings | None = None, *, instance_id: str | None = None,
    control_token: str | None = None, shutdown: Callable[[], None] | None = None,
    ai_router: AIRouter | None = None,
) -> FastAPI:
    settings = settings or load_settings()
    database = Database(settings.database_path)
    store = ChatStore(database, secret=settings.gemini_api_key, max_conversations=settings.max_conversations, max_turns=settings.max_turns)
    chat = ChatService(settings, store, ai_router or AIRouter(settings))
    runtime = {
        "ready": False, "database": database, "started_at": time.monotonic(),
        "instance_id": instance_id or secrets.token_hex(16),
    }

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            database.initialize()
            runtime["ready"] = True
            runtime["started_at"] = time.monotonic()
            logger.info("server_started", extra={"environment": settings.environment, "schema_version": SCHEMA_VERSION})
            yield
        except Exception as error:
            logger.error("server_lifecycle_failed", extra={"error_type": type(error).__name__})
            # Do not propagate raw config/path/SQLite exception text to Uvicorn logs.
            raise RuntimeError("Server lifecycle failed; inspect structured event logs") from None
        finally:
            runtime["ready"] = False
            await chat.shutdown()
            database.close()
            logger.info("server_stopped")

    app = FastAPI(
        title="JARVIS headless server", version=__version__, lifespan=lifespan,
        debug=False, docs_url=None, redoc_url=None,
        openapi_url="/openapi.json" if settings.environment == "development" else None,
    )
    app.state.settings = settings
    app.state.runtime = runtime
    app.state.chat = chat
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    app.add_middleware(RequestGuard, port=settings.port)
    app.include_router(health_router)
    app.include_router(api_router)
    app.include_router(chat_router)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(ChatError)
    async def chat_error(request: Request, error: ChatError):
        return JSONResponse({"error": {"code": error.code, "message": error.message}}, status_code=error.status)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, error: StarletteHTTPException):
        logger.warning("api_http_error", extra={"status_code": error.status_code})
        phrase = HTTPStatus(error.status_code).phrase if error.status_code in HTTPStatus._value2member_map_ else "Request failed"
        return JSONResponse({"detail": phrase}, status_code=error.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError):
        logger.warning("api_validation_error", extra={"status_code": 422})
        return JSONResponse({"detail": "Invalid request"}, status_code=422)

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, error: Exception):
        logger.error("api_exception", extra={"error_type": type(error).__name__})
        return JSONResponse({"detail": "Internal server error"}, status_code=500)

    @app.post("/internal/shutdown", include_in_schema=False, dependencies=[Depends(require_loopback)])
    async def request_shutdown(request: Request, tasks: BackgroundTasks):
        if shutdown is None or not control_token:
            raise HTTPException(status_code=404)
        provided = request.headers.get("authorization", "")
        if not hmac.compare_digest(provided.encode("utf-8"), ("Bearer " + control_token).encode("utf-8")):
            raise HTTPException(status_code=401)
        logger.info("shutdown_requested")
        tasks.add_task(shutdown)
        return JSONResponse({"status": "stopping"}, status_code=202)

    return app
