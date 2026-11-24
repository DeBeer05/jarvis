"""Synthetic TCP fixture, never the user's personal database or provider keys."""
import sys
import asyncio
import base64
import io
import wave
from pathlib import Path

import uvicorn

from server.app import create_app
from server.ai.router import AIRouter
from server.config import load_settings
from server.database import Database
from server.security.store import SecurityStore
from tests.ai_helpers import FakeProvider
from tests.auth_helpers import owner_hash


if __name__ == "__main__":
    root, port = Path(sys.argv[1]), int(sys.argv[2])
    settings = load_settings(root=root, environ={"JARVIS_DATABASE_PATH": str(root / "test.sqlite3"), "JARVIS_PORT": str(port), "JARVIS_LOG_PATH": str(root / "test.log"), "GEMINI_API_KEY": "", "GROQ_API_KEY": ""})
    database = Database(settings.database_path)
    database.initialize()
    store = SecurityStore(database, settings)
    store.create_owner("owner", owner_hash())
    app = create_app(settings, ai_router=AIRouter(settings, {name: FakeProvider() for name in ("gemini", "groq", "ollama")}))
    audio_buffer=io.BytesIO()
    with wave.open(audio_buffer,"wb") as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000);wav.writeframes(b"\0\0"*1600)
    class SyntheticSpeech:
        active=False
        cancelled=0
        async def request(self,operation,payload):
            if operation=="stt":return {"text":"Synthetic native transcription","seconds":.01}
            if payload.get("text")=="Synthetic slow synthesis":
                self.active=True
                try:await asyncio.sleep(60)
                except asyncio.CancelledError:self.cancelled+=1;raise
                finally:self.active=False
            return {"audio":base64.b64encode(audio_buffer.getvalue()).decode()}
    app.state.speech=SyntheticSpeech()
    @app.get("/api/v1/test/speech-status")
    async def speech_status():return {"active":app.state.speech.active,"cancelled":app.state.speech.cancelled}
    async def calendars():return {"items":[{"id":"primary","summary":"Synthetic calendar"}]}
    async def events(payload):return {"items":[{"id":"synthetic-event","etag":"v1","summary":"Synthetic native appointment","start":{"dateTime":"2030-01-01T10:00:00+01:00"},"end":{"dateTime":"2030-01-01T11:00:00+01:00"}}]}
    async def search(query):return {"messages":[{"id":"synthetic-mail"}]}
    async def read(identifier,include_body=False):
        import base64
        return {"id":identifier,"payload":{"headers":[{"name":"Subject","value":"Synthetic mail"}],**({"mimeType":"text/plain","body":{"data":base64.urlsafe_b64encode(b'Synthetic native email body').decode()}} if include_body else {})}}
    e=app.state.automation;e.integrations.calendar_list=calendars;e.integrations.events=events;e.integrations.mail_search=search;e.integrations.mail_read=read
    original=app.state.chat.router.bounded_result
    async def planned(messages,mode=None):
        if "toolplanner" in messages[0]["content"]:
            import json
            return json.dumps({"tool":"CalendarRead","input":{"start":"2030-01-01T00:00:00+01:00","end":"2030-01-02T00:00:00+01:00"}}),{"type":"provider","provider":"ollama","model":"synthetic"}
        return await original(messages,mode)
    app.state.chat.router.bounded_result=planned
    uvicorn.run(app, host="127.0.0.1", port=port, access_log=False, log_level="warning")
