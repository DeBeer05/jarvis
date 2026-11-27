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
from server.http_security import RequestGuard,SecurityHeaders
from server.security.service import SecurityService
from server.security.gate import SecurityGate
from server.security.api import router as security_router
from server.security.types import AuthError
from server.mobile import router as mobile_router, SpeechBridge
from server.automation.api import router as automation_router
from server.automation.engine import AutomationEngine
from server.automation.chat import AutomationChat
from server.natural.service import NaturalService
from server.natural.api import router as natural_router
from server.natural.store import Conflict

logger = logging.getLogger("jarvis.server")


def create_app(
    settings: Settings | None = None, *, instance_id: str | None = None,
    control_token: str | None = None, shutdown: Callable[[], None] | None = None,
    ai_router: AIRouter | None = None,
) -> FastAPI:
    settings = settings or load_settings()
    database = Database(settings.database_path)
    store = ChatStore(database, secret=settings.gemini_api_key, secrets=(settings.groq_api_key,settings.elevenlabs_api_key), max_conversations=settings.max_conversations, max_turns=settings.max_turns)
    chat = ChatService(settings, store, ai_router or AIRouter(settings))
    security = SecurityService(database, settings)
    runtime = {
        "ready": False, "database": database, "started_at": time.monotonic(),
        "instance_id": instance_id or secrets.token_hex(16),
    }

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            database.initialize()
            security.initialize()
            app.state.automation.store.recover()
            app.state.natural.conversations.recover()
            app.state.natural.context.private.clear()
            app.state.natural.retention.start()
            if settings.automations_enabled:
                app.state.automation.scheduler.start()
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
            await app.state.natural.retention.close()
            await app.state.automation.close()
            await chat.shutdown()
            app.state.natural.context.private.clear()
            if hasattr(app.state.speech,"close"):await app.state.speech.close()
            database.close()
            logger.info("server_stopped")

    app = FastAPI(
        title="JARVIS headless server", version=__version__, lifespan=lifespan,
        debug=False, docs_url=None, redoc_url=None,
        openapi_url="/openapi.json" if settings.environment == "development" else None,
    )
    app.state.settings = settings
    @app.exception_handler(Conflict)
    async def natural_conflict(request,error):
        return JSONResponse({"error":{"code":"conversation_conflict","message":"Gegevens of spraaksessie elders gewijzigd. Vernieuw of neem het gesprek expliciet over."}},status_code=409)
    app.state.runtime = runtime
    app.state.chat = chat
    app.state.security = security
    app.state.speech = SpeechBridge()
    app.state.mobile_push = {}
    app.state.automation = AutomationEngine(database, security)
    app.state.natural = NaturalService(database,security,chat,app.state.automation)
    chat.automation_chat = AutomationChat(app.state.automation, security, chat.router, store.clean, conversation_context=chat.context)
    chat.automation_chat.task_memory = app.state.natural.tasks
    chat.automation_chat.contacts = app.state.natural.contacts
    chat.automation_chat.response_manager = app.state.natural.responses
    app.add_middleware(SecurityGate, service=security)
    app.add_middleware(RequestGuard, port=settings.port, allowed_origins=settings.allowed_origins)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.trusted_hosts))
    app.include_router(health_router)
    app.include_router(api_router)
    app.include_router(chat_router)
    app.include_router(security_router)
    app.include_router(mobile_router)
    app.include_router(automation_router)
    app.include_router(natural_router)

    @app.exception_handler(ValueError)
    async def invalid_automation(request: Request, error: ValueError):
        return JSONResponse({"error":{"code":"invalid_action","message":"Controleer actie, tijdzone, accountkoppeling en actuele afspraakgegevens."}},status_code=400)

    app.add_middleware(SecurityHeaders)

    @app.exception_handler(AuthError)
    async def auth_error(request: Request, error: AuthError):
        return JSONResponse({"error": {"code": error.code, "message": error.message}}, status_code=error.status)

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

    @app.get("/internal/status", include_in_schema=False, dependencies=[Depends(require_loopback)])
    async def private_status(request: Request):
        if not control_token or not hmac.compare_digest(request.headers.get("authorization", "").encode(), ("Bearer " + control_token).encode()):
            raise HTTPException(status_code=401)
        from server.api.routes import status
        return status(request)

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
