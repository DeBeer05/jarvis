"""Request-local preferences; never mutate the shared router or provider settings."""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class RequestPolicy:
    provider: str
    fallback: str
    offline: bool
    automatic_selection: bool
    gemini_model: str
    groq_model: str
    ollama_model: str
    maximum_answer_tokens: int
    temperature: float
    timeout_seconds: float
    streaming: bool = True
    context_tokens: int = 6000
    oracle_model: str = ""
    processing: str = "hybrid"

    @classmethod
    def from_document(cls, document):
        # Unconfigured accounts retain existing .env policy and deadlines.
        if not document["revision"]:
            return None
        values = document["settings"]["ai"]
        if document['settings'].get('voice',{}).get('mode')=='offline':values={**values,'offline':True}
        return cls(**{name: values.get(name,field.default) for name,field in cls.__dataclass_fields__.items()})

    def order(self, mode, preferred):
        if self.offline:
            return ["ollama"]
        selected = self.provider if mode == "auto" else mode
        if mode=="auto" and self.processing=="local":return ["ollama"]
        if mode=="auto" and self.processing=="cloud":return ["oracle"]
        if selected == "auto":
            selected = preferred
        result = [selected]
        if mode == "auto" and self.automatic_selection and self.fallback not in ("none", selected):
            result.append(self.fallback)
        return result


current_policy = ContextVar("jarvis_ai_policy", default=None)
structured_schema:ContextVar[dict|None]=ContextVar('jarvis_structured_schema',default=None)


async def next_structured(source,schema):
    token=structured_schema.set(schema)
    try:return await anext(source)
    finally:structured_schema.reset(token)


@contextmanager
def use_policy(policy):
    token = current_policy.set(policy)
    try:
        yield
    finally:
        current_policy.reset(token)


async def next_with_policy(source, policy):
    # Set/reset within the same task, including cancellation and generator close.
    with use_policy(policy):
        return await anext(source)
