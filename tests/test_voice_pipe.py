import asyncio
from pathlib import Path
import sys

import pytest

from providers.voice_pipe import OwnedVoicePipe
from server.mobile import SpeechBridge
from server.security.types import AuthError

COMMAND=[sys.executable,"-u",str(Path(__file__).with_name("voice_pipe_stub.py"))]


def cleanup(worker):
    worker.cancel()
    for thread in worker.cleanup_threads:thread.join(8)


def test_private_pipe_keeps_loaded_worker_between_serial_requests():
    worker=OwnedVoicePipe(COMMAND)
    try:
        first=worker.exchange({"operation":"stt"})["result"]
        worker.cancel_pending()
        second=worker.exchange({"operation":"tts"})["result"]
        assert first["pid"]==second["pid"] and second["count"]==2
        assert not worker.busy
    finally:cleanup(worker)


def test_timeout_reaps_only_owned_process_and_next_request_is_fresh():
    worker=OwnedVoicePipe(COMMAND)
    try:
        first=worker.exchange({})["result"]
        with pytest.raises(TimeoutError):worker.exchange({"wait":True},timeout=.1)
        second=worker.exchange({})["result"]
        assert first["pid"]!=second["pid"] and second["count"]==1
    finally:cleanup(worker)


def test_bad_protocol_is_not_reported_as_success():
    worker=OwnedVoicePipe(COMMAND)
    try:assert worker.exchange({"malformed":True})=={"ok":False,"code":"voice_failed"}
    finally:cleanup(worker)


def test_mobile_bridge_reuses_worker_rejects_overlap_and_cancels_pending_audio():
    async def scenario():
        bridge=SpeechBridge(COMMAND)
        try:
            first=await bridge.request("stt",{})
            second=await bridge.request("tts",{})
            assert first["pid"]==second["pid"] and second["count"]==2
            task=asyncio.create_task(bridge.request("stt",{"wait":True}))
            for _ in range(200):
                if bridge.worker.inflight.is_set():break
                await asyncio.sleep(.01)
            with pytest.raises(AuthError) as error:await bridge.request("tts",{})
            assert error.value.status==429
            task.cancel()
            with pytest.raises(asyncio.CancelledError):await task
            fresh=await bridge.request("stt",{})
            assert fresh["pid"]!=first["pid"] and fresh["count"]==1
        finally:await bridge.close()
    asyncio.run(scenario())
