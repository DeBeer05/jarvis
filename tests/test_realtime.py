import io
import wave

import pytest
from starlette.websockets import WebSocketDisconnect

from tests.test_natural_settings_memory import natural as natural


def headers(c):return {'Authorization':'Bearer '+c.cookies.get('jarvis_access')}


def test_realtime_auth_origin_ping_and_one_connection_per_device(natural):
    app,c=natural
    with c.websocket_connect('ws://127.0.0.1:8765/api/v1/realtime',headers=headers(c)) as ws:
        assert ws.receive_json()['type']=='ready'
        ws.send_json({'type':'ping'});assert ws.receive_json()['type']=='pong'
        with pytest.raises(WebSocketDisconnect):
            with c.websocket_connect('ws://127.0.0.1:8765/api/v1/realtime',headers=headers(c)) as second:second.receive_json()
        assert len(app.state.realtime_slots)==1
        ws.send_json({'type':'ping'});assert ws.receive_json()['type']=='pong'
    with pytest.raises(WebSocketDisconnect):
        with c.websocket_connect('ws://127.0.0.1:8765/api/v1/realtime',headers={**headers(c),'Origin':'https://untrusted.test'}) as ws:ws.receive_json()
    with pytest.raises(WebSocketDisconnect):
        with c.websocket_connect('ws://127.0.0.1:8765/api/v1/realtime') as ws:
            ws.send_json({'type':'ping'});ws.receive_json()


def test_partial_transcript_never_executes_and_same_socket_is_reused(natural):
    app,c=natural;calls=[]
    class Speech:
        async def request(self,operation,payload):calls.append(operation);return {'text':'Morgen om twee uur.','seconds':.01}
    app.state.speech=Speech();output=io.BytesIO()
    with wave.open(output,'wb') as audio:
        audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(16000);audio.writeframes(b'\0\0'*5000)
    with c.websocket_connect('ws://127.0.0.1:8765/api/v1/realtime',headers=headers(c)) as ws:
        ws.receive_json()
        for _ in range(2):
            ws.send_json({'type':'audio.start'});assert ws.receive_json()['type']=='audio.ready'
            ws.send_bytes(output.getvalue());ws.send_json({'type':'audio.partial'})
            result=ws.receive_json();assert result['type']=='transcript' and result['final'] is False
            ws.send_json({'type':'audio.commit'});assert ws.receive_json()['final'] is True
        assert calls==['stt']*4 and not app.state.automation.store.items()


def test_oversize_audio_and_missing_permissions_close_without_execution(natural):
    app,c=natural
    with pytest.raises(WebSocketDisconnect):
        with c.websocket_connect('ws://127.0.0.1:8765/api/v1/realtime',headers=headers(c)) as ws:
            ws.receive_json();ws.send_bytes(b'0'*65537);ws.receive_json()
    assert not app.state.automation.store.items()


def test_realtime_rechecks_revoked_write_permission(natural):
    app,c=natural
    principal=app.state.security.store.authenticate(c.cookies.get('jarvis_access'))
    with c.websocket_connect('ws://127.0.0.1:8765/api/v1/realtime',headers=headers(c)) as ws:
        ws.receive_json()
        with app.state.natural.store.transaction(principal,write=True) as (db,user):
            db.execute("DELETE FROM auth_permissions WHERE device_id=? AND permission='chat:write'",(principal.device_id,))
        ws.send_json({'type':'audio.start'})
        with pytest.raises(WebSocketDisconnect):ws.receive_json()
    assert not app.state.automation.store.items()
