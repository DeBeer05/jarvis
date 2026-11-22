import pytest

from server.config import ConfigurationError, load_settings


def test_safe_defaults(settings):
    assert settings.host == "127.0.0.1"
    assert settings.port == 8765
    assert settings.ai_provider == "none"
    assert not settings.gemini_api_key
    assert settings.database_path.is_absolute()


def test_env_file_and_environment_precedence(tmp_path):
    (tmp_path / ".env").write_text('JARVIS_PORT=9123\nJARVIS_ENV=production\nJARVIS_DATABASE_PATH="data/test.sqlite3"\n', encoding="utf-8")
    result = load_settings(root=tmp_path, environ={"JARVIS_PORT": "9124"})
    assert result.port == 9124
    assert result.environment == "production"
    assert result.database_path == tmp_path / "data" / "test.sqlite3"


@pytest.mark.parametrize("name,value", [
    ("JARVIS_HOST", "0.0.0.0"), ("JARVIS_HOST", "192.168.1.1"),
    ("JARVIS_PORT", "0"), ("JARVIS_PORT", "65536"), ("JARVIS_PORT", "not-a-number"),
    ("JARVIS_ENV", "unknown"), ("JARVIS_LOG_LEVEL", "verbose"),
    ("JARVIS_LOG_MAX_BYTES", "0"), ("JARVIS_LOG_BACKUP_COUNT", "99"),
    ("JARVIS_AI_PROVIDER", "invalid"), ("JARVIS_DATABASE_PATH", "//remote/share/db"),
    ("JARVIS_DATABASE_PATH", ""), ("JARVIS_ENABLE_EXTERNAL_ACCESS", "true"),
    ("JARVIS_ENABLE_AUTOMATIONS", "true"),
])
def test_invalid_configuration_is_rejected_without_values(tmp_path, name, value):
    with pytest.raises(ConfigurationError) as error:
        load_settings(root=tmp_path, environ={name: value})
    assert name in str(error.value)
    assert value not in str(error.value) or value == ""


def test_same_database_and_log_path_rejected(tmp_path):
    with pytest.raises(ConfigurationError):
        load_settings(root=tmp_path, environ={"JARVIS_DATABASE_PATH": "same", "JARVIS_LOG_PATH": "same"})


def test_secret_not_in_settings_repr(tmp_path):
    canary = "test-canary-" + "never-expose"
    settings = load_settings(root=tmp_path, environ={"GEMINI_API_KEY": canary})
    assert canary not in repr(settings)


def test_malformed_dotenv_is_rejected_without_echo(tmp_path):
    (tmp_path / ".env").write_text('BROKEN="test-canary-unterminated\n', encoding="utf-8")
    with pytest.raises(ConfigurationError, match="Invalid .env syntax"):
        load_settings(root=tmp_path, environ={})
