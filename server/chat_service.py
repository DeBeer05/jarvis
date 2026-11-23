"""Admission, cancellation, context budgets and exactly one persisted turn per request."""
import asyncio
import logging
import time
import uuid
from collections import deque
from contextlib import aclosing, suppress
from dataclasses import dataclass, field

from server.ai.providers import ProviderError
from server.ai.router import AIRouter
from server.chat_store import ChatError, ChatStore
from server.config import Settings

logger = logging.getLogger("jarvis.server")


class GenerationCancelled(Exception):
    pass


@dataclass
class Generation:
    request_id: str
    conversation_id: str | None
    mode: str
    message: str
    history: list = field(default_factory=list)
    cancel: asyncio.Event = field(default_factory=asyncio.Event)
    text: str = ""
    provider: str | None = None
    model: str | None = None
    status: str = "running"
    error: dict | None = None
    started: bool = False
    expiry: asyncio.TimerHandle | None = field(default=None, repr=False)
    principal: object | None = field(default=None, repr=False)

    def public(self) -> dict:
        return {"request_id": self.request_id, "conversation_id": self.conversation_id,
                "provider": self.provider, "model": self.model, "status": self.status,
                "message": self.text, "error": self.error}


class ChatService:
    def __init__(self, settings: Settings, store: ChatStore, router: AIRouter):
        self.settings, self.store, self.router = settings, store, router
        self.active: dict[str, Generation] = {}
        self.admissions = deque()
        self.persistence_tasks: set[asyncio.Task] = set()
        self.automation_chat = None

    async def prepare(self, message: str, mode: str | None = None, conversation_id: str | None = None, request_id: str | None = None, *, principal=None) -> Generation:
        if len(message) > self.settings.max_message_chars or not message.strip():
            raise ChatError("invalid_message", "Het bericht is leeg of te lang.", 422)
        if len(message) + len(self.settings.system_prompt) > self.settings.max_context_chars:
            raise ChatError("invalid_message", "Dit bericht past niet binnen het ingestelde contextbudget.", 422)
        if len(self.active) >= self.settings.max_concurrent_ai:
            raise ChatError("busy", "JARVIS verwerkt al het maximale aantal antwoorden. Wacht even.", 429)
        if conversation_id and any(run.conversation_id == conversation_id for run in self.active.values()):
            raise ChatError("conversation_busy", "In dit gesprek wordt al een antwoord gemaakt.", 409)
        tick = time.monotonic()
        while self.admissions and tick - self.admissions[0] >= 60:
            self.admissions.popleft()
        if len(self.admissions) >= self.settings.requests_per_minute:
            raise ChatError("rate_limited", "Te veel chatverzoeken. Probeer over een minuut opnieuw.", 429)
        request_id = request_id or str(uuid.uuid4())
        if request_id in self.active:
            raise ChatError("duplicate_request", "Dit verzoek loopt al.", 409)
        run = Generation(request_id, conversation_id, mode or self.settings.ai_provider, self.store.clean(message.strip()))
        run.principal = principal
        self.active[request_id] = run  # Reserve before the first await; no unbounded wait queue.
        self.admissions.append(tick)
        try:
            run.conversation_id, run.history = await asyncio.to_thread(self.store.start, request_id, conversation_id, run.message)
        except BaseException:
            self.active.pop(request_id, None)
            raise
        run.expiry = asyncio.get_running_loop().call_later(self.settings.ai_timeout_seconds + 5, self.expire, run)
        return run

    def expire(self, run: Generation):
        """Release a reserved request even if an HTTP client never starts reading."""
        if self.active.get(run.request_id) is not run:
            return
        run.cancel.set()
        if not run.started:
            run.status = "cancelled"
            self.active.pop(run.request_id, None)
            task = asyncio.create_task(asyncio.to_thread(self.store.finish, run.request_id, "", None, None, "cancelled", "request_expired"))
            self.persistence_tasks.add(task)
            task.add_done_callback(self.persistence_tasks.discard)

    def context(self, run: Generation) -> list[dict]:
        # Keep complete user/assistant pairs, newest first within a strict character budget.
        remaining = self.settings.max_context_chars - len(run.message) - len(self.settings.system_prompt)
        kept = []
        for index in range(len(run.history) - 2, -1, -2):
            pair = run.history[index:index + 2]
            size = sum(len(message["content"]) for message in pair)
            if size > remaining:
                break
            kept[0:0] = pair
            remaining -= size
        return [{"role": "system", "content": self.store.clean(self.settings.system_prompt)}, *kept,
                {"role": "user", "content": run.message}]

    async def events(self, run: Generation):
        run.started = True
        pending = None
        cancellation = asyncio.create_task(run.cancel.wait())
        try:
            yield {"type": "meta", "request_id": run.request_id, "conversation_id": run.conversation_id}
            if run.cancel.is_set():
                raise GenerationCancelled
            source = self.automation_chat.stream(run) if self.automation_chat and self.automation_chat.candidate(run) else self.router.stream(self.context(run), run.mode)
            async with aclosing(source) as stream:
                try:
                    async with asyncio.timeout(self.settings.ai_timeout_seconds):
                        while True:
                            pending = asyncio.create_task(anext(stream))
                            done, _ = await asyncio.wait((pending, cancellation), return_when=asyncio.FIRST_COMPLETED)
                            if cancellation in done:
                                run.status = "cancelled"
                                break
                            try:
                                event = pending.result()
                            except StopAsyncIteration:
                                run.status = "completed"
                                break
                            if event["type"] == "delta":
                                if len(run.text) + len(event["text"]) > self.settings.max_response_chars:
                                    raise ProviderError("response_limit", retryable=False)
                                run.text += event["text"]
                            elif event["type"] == "provider":
                                run.provider, run.model = event["provider"], event["model"]
                            yield event
                finally:
                    # Stop the pending __anext__ before closing nested async generators.
                    if pending and not pending.done():
                        pending.cancel()
                        with suppress(asyncio.CancelledError, StopAsyncIteration):
                            await pending
        except GenerationCancelled:
            run.status = "cancelled"
        except ProviderError as error:
            run.status = "error"
            run.error = {"code": error.code, "message": error.message}
            logger.warning("chat_provider_failed", extra={"error_code": error.code, "request_id": run.request_id})
        except TimeoutError:
            run.status = "error"
            run.error = {"code": "timeout", "message": "Het antwoord duurde te lang. Probeer opnieuw."}
            logger.warning("chat_timeout")
        except (asyncio.CancelledError, GeneratorExit):
            run.status = "cancelled"
            raise
        except Exception as error:
            run.status = "error"
            run.error = {"code": "internal_error", "message": "Het antwoord kon niet worden verwerkt."}
            logger.error("chat_failed", extra={"error_type": type(error).__name__})
        finally:
            if run.expiry:
                run.expiry.cancel()
            if pending and not pending.done():
                pending.cancel()
                with suppress(asyncio.CancelledError, StopAsyncIteration):
                    await pending
            cancellation.cancel()
            with suppress(asyncio.CancelledError):
                await cancellation
            run.text = self.store.clean(run.text)
            persistence = asyncio.create_task(asyncio.to_thread(
                self.store.finish, run.request_id, run.text, run.provider, run.model,
                run.status, run.error["code"] if run.error else None,
            ))
            self.persistence_tasks.add(persistence)
            persistence.add_done_callback(self.persistence_tasks.discard)
            try:
                await asyncio.shield(persistence)
            except asyncio.CancelledError:
                # Shielded database cleanup continues even after an HTTP disconnect.
                pass
            finally:
                self.active.pop(run.request_id, None)
        if run.error:
            yield {"type": "error", **run.error}
        yield {"type": "done", **run.public()}

    def cancel(self, request_id: str) -> bool:
        run = self.active.get(request_id)
        if run is None:
            return False
        run.cancel.set()
        return True

    def busy(self, conversation_id: str) -> bool:
        return any(run.conversation_id == conversation_id for run in self.active.values())

    async def shutdown(self):
        for run in list(self.active.values()):
            if run.expiry:
                run.expiry.cancel()
            self.expire(run)
        # Uvicorn normally drains requests before lifespan shutdown.
        if self.persistence_tasks:
            await asyncio.gather(*self.persistence_tasks, return_exceptions=True)
