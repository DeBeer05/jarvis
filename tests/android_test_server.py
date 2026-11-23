"""Ephemeral Android instrumentation fixture, never used by production start scripts."""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import sys

import uvicorn
from fastapi import Request
from server.app import create_app
from server.config import load_settings
from server.ai.router import AIRouter
from server.database import Database
from server.security.store import SecurityStore
from server.security.gate import PUBLIC
from tests.auth_helpers import owner_hash
from tests.ai_helpers import FakeProvider


def fixture(root, port):
    if not root.name.startswith("android-fixture-"):
        raise ValueError("Explicit synthetic fixture directory required")
    root.mkdir(parents=True, exist_ok=False)
    settings=load_settings(root=root, environ={"JARVIS_PORT":str(port), "JARVIS_DATABASE_PATH":str(root/"test.sqlite3"), "GEMINI_API_KEY":"", "GROQ_API_KEY":""})
    database=Database(settings.database_path);database.initialize()
    store=SecurityStore(database,settings);store.create_owner("owner",owner_hash())
    app=create_app(settings,ai_router=AIRouter(settings,{name:FakeProvider() for name in ("gemini","groq","ollama")}))
    PUBLIC["/api/test/approve"]={"POST"}  # this isolated test process only
    PUBLIC["/api/test/grant"]={"POST"}
    owner_device=[None]
    @app.post("/api/test/approve")
    async def approve(request: Request):
        data=await request.json()
        owner=await asyncio.to_thread(app.state.security.store.login,owner_hash(),"Synthetic fixture owner",owner_device[0])
        owner_device[0]=owner.principal.device_id
        await asyncio.to_thread(app.state.security.store.decide_pair,data["request_id"],owner.principal,True,data["user_code"],{"chat:read","chat:write","chat:delete","status:read"})
        return {"approved":True}
    @app.post("/api/test/grant")
    async def grant(request:Request):
        # Synthetic fixture only; this router is never imported by server.app.
        access=request.headers.get("authorization","").removeprefix("Bearer ")
        principal=app.state.security.store.authenticate(access)
        with app.state.automation.store.db(True) as db:
            for scope in ("automation:read","automation:write","automation:approve"):
                db.execute("INSERT OR IGNORE INTO auth_permissions VALUES (?,?)",(principal.device_id,scope))
        return {"granted":True}
    return app


if __name__=="__main__":
    uvicorn.run(fixture(Path(sys.argv[1]),int(sys.argv[2])),host="127.0.0.1",port=int(sys.argv[2]),access_log=False,log_level="warning")
