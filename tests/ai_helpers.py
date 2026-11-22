import asyncio

from server.ai.providers import ProviderError


class FakeProvider:
    def __init__(self, chunks=("Hallo", " daar."), *, failure=None, fail_after=0, wait=False):
        self.model = "test-model"
        self.chunks, self.failure, self.fail_after, self.wait = chunks, failure, fail_after, wait
        self.calls, self.closed = [], False
        self.waiting = asyncio.Event()

    async def stream(self, messages):
        self.calls.append(messages)
        try:
            for index, chunk in enumerate(self.chunks):
                if self.failure and index == self.fail_after:
                    raise ProviderError(self.failure)
                yield chunk
            if self.failure:
                raise ProviderError(self.failure)
            if self.wait:
                self.waiting.set()
                await asyncio.Event().wait()
        finally:
            self.closed = True

    async def availability(self):
        return {"configured": True, "available": True, "state": "available", "model": self.model}
