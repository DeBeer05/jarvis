import json

from tests.test_natural_settings_memory import natural as natural
from tests.test_natural_context import patch
from tests.test_security import client_for


def test_diagnostics_are_numeric_bounded_and_never_export_memory_or_prompt(natural,monkeypatch):
    app,c=natural
    monkeypatch.setattr(app.state.natural.diagnostics,"gpu",lambda:None)
    c.post("/api/v1/natural/memory",json={"content":"Privé project lantaarn"})
    principal=app.state.security.store.authenticate(c.cookies.get("jarvis_access"))
    patch(c,"diagnostics",{"maximum_events":10})
    manager=app.state.natural.diagnostics
    for index in range(20):manager.record(principal,"stt_ms",index)
    manager.record(principal,"error",code="timeout")
    response=c.get("/api/v1/natural/diagnostics");assert response.status_code==200
    snapshot=response.json();assert snapshot["database"]=="read_write_ok" and len(snapshot["events"])==10
    assert snapshot["latency"]["stt_ms"]==19 and snapshot["memory_counts"]["active"]==1
    assert "Privé project lantaarn" not in json.dumps(snapshot)
    assert snapshot["contains_conversation_content"] is False and snapshot["resources"]["resident_bytes"]>0
    assert snapshot["resources"]["gpu_percent"] is None and snapshot["websocket"]=="not_configured"
    assert c.get("/api/v1/natural/diagnostics").json()["resources"]["cpu_one_core_percent"] is not None


def test_native_metrics_validate_types_codes_permissions_and_privacy_toggle(natural):
    app,c=natural
    body={"items":[{"event":"native_first_audio_ms","value":1234.5}]}
    assert c.post("/api/v1/natural/diagnostics/metrics",json=body).status_code==200
    assert c.get("/api/v1/natural/diagnostics").json()["latency"]["native_first_audio_ms"]==1234.5
    assert c.post("/api/v1/natural/diagnostics/metrics",json={"items":[{"event":"prompt","value":1}]}).status_code==422
    assert c.post("/api/v1/natural/diagnostics/metrics",json={"items":[{"event":"interruption","value":1,"text":"private"}]}).status_code==422
    assert c.post("/api/v1/natural/diagnostics/metrics",json={"items":[{"event":"interruption","value":-1}]}).status_code==422
    patch(c,"diagnostics",{"enabled":False})
    before=c.get("/api/v1/natural/diagnostics").json()["events"]
    assert c.post("/api/v1/natural/diagnostics/metrics",json=body).status_code==200
    assert c.get("/api/v1/natural/diagnostics").json()["events"]==before
    with client_for(app) as anonymous:assert anonymous.get("/api/v1/natural/diagnostics").status_code==401
    principal=app.state.security.store.authenticate(c.cookies.get("jarvis_access"))
    with app.state.natural.store.transaction(principal,write=True) as (db,user):db.execute("DELETE FROM auth_permissions WHERE device_id=? AND permission='status:read'",(principal.device_id,))
    assert c.get("/api/v1/natural/diagnostics").status_code==403


def test_response_records_real_timings_without_response_content(natural):
    app,c=natural
    c.post("/api/v1/chat",json={"message":"Synthetische persoonlijke vraag"})
    data=c.get("/api/v1/natural/diagnostics").json()
    assert data["latency"]["response_total_ms"]>0 and data["latency"]["ai_first_token_ms"]>=0
    assert data["latency"]["context_tokens"]>0
    assert "Synthetische persoonlijke vraag" not in json.dumps(data)


def test_disabled_diagnostics_never_probe_hardware(natural,monkeypatch):
    app,c=natural
    patch(c,"diagnostics",{"enabled":False,"resources":True})
    def unexpected(*args,**kwargs):raise AssertionError("Diagnostics are disabled")
    monkeypatch.setattr(app.state.natural.diagnostics,"resources",unexpected)
    snapshot=c.get("/api/v1/natural/diagnostics").json()
    assert snapshot["enabled"] is False and snapshot["resources"] is None


def test_optional_gpu_probe_is_bounded_cached_and_does_not_run_user_commands(natural,monkeypatch):
    from types import SimpleNamespace
    app,c=natural;manager=app.state.natural.diagnostics;calls=[]
    monkeypatch.setattr("server.natural.diagnostics.shutil.which",lambda _:"synthetic-nvidia-smi")
    def execute(command,**kwargs):
        calls.append(command);assert kwargs["timeout"]==2
        return SimpleNamespace(stdout="7, 1024\n")
    monkeypatch.setattr("server.natural.diagnostics.subprocess.run",execute)
    assert manager.gpu()==[{"utilization_percent":7.,"memory_used_mib":1024.}]
    assert manager.gpu()==manager.gpu() and len(calls)==1
    assert calls[0]==["synthetic-nvidia-smi","--query-gpu=utilization.gpu,memory.used","--format=csv,noheader,nounits"]
