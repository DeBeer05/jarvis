import pytest

from server.config import load_settings


@pytest.fixture
def settings(tmp_path):
    return load_settings(root=tmp_path, environ={})
