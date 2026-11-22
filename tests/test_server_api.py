import json
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from server.app import create_app


def client(app, **kwargs):
    return TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 50000), **kwargs)


def test_lifespan_health_ready_status_and_shutdown(settings):
    app = create_app(settings)
    with client(app) as http:
        assert http.get("/health").json() == {"status": "ok", "service": "jarvis-server"}
        assert http.get("/ready").status_code == 200
        data = http.get("/api/v1/status").json()
        assert data["status"] == "running"
        assert data["version"] == "0.2.0"
        assert data["uptime_seconds"] >= 0
        assert data["components"] == {"api": True, "database": True, "ai": True}
        assert data["ai_providers"]["selected"] == "auto"
        assert not data["ai_providers"]["gemini"]["available"]
        assert http.get("/openapi.json").status_code == 200
    assert not app.state.runtime["ready"]
    assert not app.state.runtime["database"].check()


def test_ready_returns_503_when_components_unavailable(settings):
    app = create_app(settings)
    http = client(app)
    assert http.get("/ready").status_code == 503
    with http:
        app.state.runtime["database"].close()
        assert http.get("/health").status_code == 200
        assert http.get("/ready").status_code == 503
        assert http.get("/api/v1/status").json()["status"] == "degraded"


def test_status_contains_no_secret_or_local_paths(settings):
    canary = "test-canary-" + "never-expose"
    with client(create_app(replace(settings, gemini_api_key=canary, ai_provider="gemini"))) as http:
        text = http.get("/api/v1/status").text
        assert canary not in text
        assert str(settings.database_path) not in text
        assert str(settings.log_path) not in text
        assert json.loads(text)["ai_providers"]["gemini"] == {"configured": True, "available": None}


def test_status_refuses_remote_client_and_forwarded_header(settings):
    app = create_app(settings)
    with TestClient(app, base_url="http://127.0.0.1", client=("203.0.113.8", 50000)) as http:
        assert http.get("/api/v1/status", headers={"X-Forwarded-For": "127.0.0.1"}).status_code == 403


def test_untrusted_host_is_refused(settings):
    with client(create_app(settings)) as http:
        assert http.get("/health", headers={"Host": "untrusted.example"}).status_code == 400


def test_production_has_no_openapi(settings):
    with client(create_app(replace(settings, environment="production"))) as http:
        assert http.get("/openapi.json").status_code == 404


def test_unexpected_exception_is_sanitized(settings, caplog):
    app = create_app(settings)
    canary = "test-canary-" + "never-expose"

    @app.get("/test-failure")
    def fail():
        raise RuntimeError(canary)

    with client(app, raise_server_exceptions=False) as http:
        response = http.get("/test-failure")
        assert response.status_code == 500
        assert response.json() == {"detail": "Internal server error"}
    assert canary not in caplog.text
    assert "api_exception" in caplog.text


def test_startup_failure_closes_resources_and_hides_values(settings):
    settings.database_path.parent.mkdir(parents=True)
    settings.database_path.write_bytes(b"not a database")
    app = create_app(settings)
    with pytest.raises(RuntimeError, match="Server lifecycle failed"):
        with client(app):
            pass
    assert not app.state.runtime["ready"]


def test_shutdown_requires_local_client_and_token(settings):
    stopped = []
    token = "test-" + "local-control-token"
    app = create_app(settings, control_token=token, shutdown=lambda: stopped.append(True))
    with client(app) as http:
        assert http.post("/internal/shutdown").status_code == 401
        assert http.post("/internal/shutdown", headers={"Authorization": "Bearer wrong"}).status_code == 401
        assert not stopped
        assert http.post("/internal/shutdown", headers={"Authorization": "Bearer " + token}).status_code == 202
        assert stopped == [True]
        assert "/internal/shutdown" not in http.get("/openapi.json").json()["paths"]
