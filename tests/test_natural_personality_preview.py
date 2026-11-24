from tests.test_natural_context import build,client,patch
from server.natural.models import Personality


def test_preview_is_ephemeral_offline_and_cannot_execute_tools(settings):
    app,providers=build(settings)
    with client(app) as c:
        patch(c,"ai",{"offline":True})
        before=c.get("/api/v1/natural/settings").json()
        personality=Personality().model_dump();personality["profile"]="concise"
        response=c.post("/api/v1/natural/personality/preview",json={"personality":personality})
        assert response.status_code==200
        assert response.json()=={"message":"Antwoord.","saved":False,"actions_executed":False}
        assert providers["ollama"].calls and not providers["gemini"].calls
        assert '"brevity": 100' in str(providers["ollama"].calls[-1])
        assert c.get("/api/v1/natural/settings").json()==before
        assert c.get("/api/v1/chat/conversations").json()["items"]==[]
        assert app.state.automation.store.items()==[]
        assert c.post("/api/v1/natural/personality/preview",json={"personality":{**personality,"humor":101}}).status_code==422
