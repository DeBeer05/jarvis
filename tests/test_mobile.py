import base64
import io
import wave

import pytest
from tests.test_security import make_app, client_for
from tests.auth_helpers import TEST_PASSWORD, owner_hash
from server.security.types import pkce, token


def wav():
    data=io.BytesIO()
    with wave.open(data,"wb") as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(16000);out.writeframes(b"\0\0"*1600)
    return data.getvalue()


def paired(app, native, *, scopes=None):
    security=app.state.security
    security.store.create_owner("owner",owner_hash())
    verifier=token()
    response=native.post("/api/v1/auth/android-login",json={"username":"owner","password":TEST_PASSWORD,"device_name":"Synthetic Android","code_challenge":pkce(verifier)})
    assert response.status_code==200
    pair=response.json()
    assert "access_token" not in pair and not security.store.devices()["items"]
    owner=security.store.login(owner_hash(),"Synthetic owner")
    security.store.decide_pair(pair["request_id"],owner.principal,True,pair["user_code"],scopes or {"chat:read","chat:write","chat:delete","status:read"})
    # First redeem after approval doesn't require an earlier pending poll.
    result=native.post("/api/v1/pairing/token",json={"grant_type":"urn:ietf:params:oauth:grant-type:device_code","device_code":pair["device_code"],"code_verifier":verifier})
    assert result.status_code==200
    native.headers["Authorization"]="Bearer "+result.json()["access_token"]
    return result.json()


def test_android_password_login_still_requires_owner_pairing(settings):
    app=make_app(settings)
    with client_for(app) as native:
        result=paired(app,native)
        assert native.get("/api/v1/auth/device").json()["type"]=="android"
        assert not any(x.startswith("admin:") for x in result["scope"].split())
        assert native.get("/api/v1/devices").status_code==403


def test_android_wrong_password_does_not_create_pair_or_session(settings):
    app=make_app(settings)
    with client_for(app) as native:
        app.state.security.store.create_owner("owner",owner_hash())
        for _ in range(5):
            response=native.post("/api/v1/auth/android-login",json={"username":"owner","password":"incorrect","device_name":"Android","code_challenge":pkce(token())})
            assert response.status_code==401
        assert not app.state.security.store.pairs()["items"]
        assert not app.state.security.store.devices()["items"]


def test_mobile_routes_default_deny_and_content_bounds(settings):
    app=make_app(settings)
    with client_for(app) as native:
        assert native.post("/api/v1/mobile/speech/transcribe",content=wav(),headers={"Content-Type":"audio/wav"}).status_code==401
        assert native.post("/api/v1/mobile/speech/synthesize",json={"text":"Hallo"}).status_code==401
        assert native.post("/api/v1/mobile/push",json={"token":"synthetic"*4}).status_code==401
        paired(app,native)
        assert native.post("/api/v1/mobile/speech/transcribe",content=b"x"*2_000_001,headers={"Content-Type":"audio/wav"}).status_code==413
        assert native.post("/api/v1/mobile/speech/transcribe",content=b"invalid",headers={"Content-Type":"audio/wav"}).status_code==422
        assert native.post("/api/v1/mobile/speech/transcribe",json={"audio":"bad"}).status_code==415
        assert native.post("/api/v1/mobile/speech/synthesize",json={"text":"x"*701}).status_code==422
        assert native.post("/api/v1/mobile/speech/transcribe",content=wav(),headers={"Content-Type":"audio/wav","Origin":"https://attacker.invalid"}).status_code==403


def test_mobile_speech_reuses_bridge_without_audio_files(settings, tmp_path):
    app=make_app(settings)
    calls=[]
    class Bridge:
        async def request(self,operation,payload):
            calls.append(operation)
            if operation=="stt":
                assert base64.b64decode(payload["audio"])==wav()
                return {"text":"Hallo Jarvis","seconds":.1}
            return {"audio":base64.b64encode(wav()).decode()}
    app.state.speech=Bridge()
    with client_for(app) as native:
        paired(app,native)
        assert native.post("/api/v1/mobile/speech/transcribe",content=wav(),headers={"Content-Type":"audio/wav"}).json()["text"]=="Hallo Jarvis"
        result=native.post("/api/v1/mobile/speech/synthesize",json={"text":"Hallo"})
        assert result.status_code==200 and result.content==wav()
        assert result.headers["cache-control"]=="no-store"
        assert calls==["stt","tts"]


def test_audio_requires_explicit_chat_rights_and_revocation_is_effective(settings):
    app=make_app(settings)
    with client_for(app) as native:
        paired(app,native,scopes={"status:read"})
        assert native.post("/api/v1/mobile/speech/synthesize",json={"text":"Hallo"}).status_code==403
        assert native.post("/api/v1/mobile/speech/transcribe",content=wav(),headers={"Content-Type":"audio/wav"}).status_code==403
        assert native.post("/api/v1/auth/disconnect").status_code==200
        assert native.post("/api/v1/mobile/push",json={"token":"synthetic"*4}).status_code==401


def test_push_registration_is_bound_to_device_and_keeps_only_digest(settings):
    app=make_app(settings)
    with client_for(app) as native:
        credentials=paired(app,native)
        raw="synthetic-fcm-token-not-a-real-secret"
        result=native.post("/api/v1/mobile/push",json={"token":raw,"categories":["urgent","news"]})
        assert result.status_code==200 and not result.json()["external_delivery_available"]
        assert raw not in repr(app.state.mobile_push)
        assert len(app.state.mobile_push[credentials["device_id"]]["digest"])==64
        assert native.post("/api/v1/mobile/push",json={"token":raw,"categories":["calls"]}).status_code==422
        assert native.delete("/api/v1/mobile/push").status_code==200
        assert not app.state.mobile_push


def test_session_revoked_during_inference_cannot_receive_result(settings):
    app=make_app(settings)
    with client_for(app) as native:
        credentials=paired(app,native)
        principal=app.state.security.store.authenticate(credentials["access_token"])
        class RevokingBridge:
            async def request(self, operation, payload):
                app.state.security.store.change_device(principal.device_id,principal)
                return {"text":"private synthetic transcript", "seconds":.1}
        app.state.speech=RevokingBridge()
        result=native.post("/api/v1/mobile/speech/transcribe",content=wav(),headers={"Content-Type":"audio/wav"})
        assert result.status_code==401 and "private synthetic transcript" not in result.text
