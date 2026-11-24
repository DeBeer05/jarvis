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
from server.ai.policy import next_with_policy
from server.natural.store import Conflict
from server.natural.conversation import State

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
    channel: str = "text"
    session_epoch: int | None = None
    natural_context: dict | None = field(default=None, repr=False)
    context_messages: list | None = field(default=None, repr=False)
    context_metrics: dict = field(default_factory=dict)
    ai_policy: object | None = field(default=None, repr=False)
    wait_state: object | None = field(default=None, repr=False)

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
        self.natural = None

    async def prepare(self, message: str, mode: str | None = None, conversation_id: str | None = None, request_id: str | None = None, *, principal=None,channel="text",session_epoch=None) -> Generation:
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
        run.channel,run.session_epoch=channel,session_epoch
        self.active[request_id] = run  # Reserve before the first await; no unbounded wait queue.
        self.admissions.append(tick)
        try:
            if self.natural and principal and conversation_id:
                await asyncio.to_thread(self.natural.authorize_conversation,principal,conversation_id)
                await asyncio.to_thread(self.natural.check_audio,run)
            run.conversation_id, run.history = await asyncio.to_thread(self.store.start, request_id, conversation_id, run.message)
        except BaseException:
            self.active.pop(request_id, None)
            raise
        try:
            if self.natural and principal:
                run.natural_context,run.context_messages,run.context_metrics=await asyncio.to_thread(self.natural.prepare,run)
                run.ai_policy=run.natural_context["policy"]
                await self.natural.phase(run,State.THINKING)
        except BaseException:
            # start succeeded: finish only this new turn, never a duplicate ID.
            await asyncio.to_thread(self.store.finish,request_id,"",None,None,"error","context_rejected")
            self.active.pop(request_id,None)
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
        if run.context_messages is not None:
            return run.context_messages
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
        memory_command=bool(self.natural and run.natural_context and self.natural.is_command(run))
        cancellation = asyncio.create_task(run.cancel.wait())
        try:
            yield {"type": "meta", "request_id": run.request_id, "conversation_id": run.conversation_id}
            if run.cancel.is_set():
                raise GenerationCancelled
            if memory_command:
                source=self.natural.stream_command(run)
            else:
                source = self.automation_chat.stream(run) if self.automation_chat and self.automation_chat.candidate(run) else self.router.stream(self.context(run), run.mode)
            async with aclosing(source) as stream:
                try:
                    async with asyncio.timeout(run.ai_policy.timeout_seconds if run.ai_policy else self.settings.ai_timeout_seconds):
                        while True:
                            pending = asyncio.create_task(next_with_policy(stream,run.ai_policy))
                            done, _ = await asyncio.wait((pending, cancellation), return_when=asyncio.FIRST_COMPLETED)
                            if cancellation in done:
                                run.status = "cancelled"
                                break
                            try:
                                event = pending.result()
                            except StopAsyncIteration:
                                run.status = "completed"
                                break
                            if self.natural and run.session_epoch is not None:
                                await asyncio.to_thread(self.natural.check_audio,run)
                                if event["type"]=="delta" and not run.text:
                                    await self.natural.phase(run,State.ASSISTANT_SPEAKING)
                            if self.natural and run.natural_context and not memory_command:
                                version=await asyncio.to_thread(self.natural.context.memory_version,run.principal)
                                if version!=run.natural_context["memory_version"]:
                                    run.status="cancelled"
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
        except Conflict:
            run.status="cancelled"
            run.error={"code":"conversation_taken_over","message":"Dit spraakgesprek is verlopen of overgenomen. Start of hervat het gesprek opnieuw."}
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
            if self.natural and run.session_epoch is not None:
                try:
                    target=run.wait_state if run.status=="completed" and run.wait_state else State.ERROR if run.status=="error" else State.LISTENING if run.status=="cancelled" else None
                    if target:await self.natural.phase(run,target)
                except Exception:
                    logger.debug("conversation_phase_unavailable")
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
            if self.natural and run.principal and run.status=="completed":
                try:
                    await asyncio.to_thread(self.natural.context.summarize,run.principal,run.conversation_id)
                except Exception as error:
                    logger.warning("summary_unavailable",extra={"error_type":type(error).__name__})
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
