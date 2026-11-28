from dataclasses import replace
import sys

import pytest

from scripts.migrate_to_oracle import Migration,environment
from server.config import load_settings


def test_cloud_configuration_keeps_providers_and_fences_scheduler(settings):
    configured=replace(settings,groq_api_key='synthetic-provider-secret')
    text=environment(configured,'https://example.test',google=True)
    assert 'JARVIS_ENABLE_AUTOMATIONS="false"' in text
    assert 'JARVIS_ORACLE_BASE_URL="http://127.0.0.1:11434"' in text
    cloud=load_settings(root=settings.database_path.parent,environ=__import__('dotenv').dotenv_values(stream=__import__('io').StringIO(text)))
    assert cloud.profile=='oracle-production' and cloud.groq_api_key==configured.groq_api_key and not cloud.automations_enabled
    assert cloud.google_client_file=='/var/lib/jarvis/secrets/google-client.json'
    with pytest.raises(ValueError):environment(configured,'http://example.test')


def test_credential_transfer_output_is_never_logged(tmp_path):
    migration=Migration.__new__(Migration);migration.stage=tmp_path;migration.counter=0
    result=migration.run([sys.executable,'-c',"print('SYNTHETIC_PRIVATE_OUTPUT')"],sensitive=True)
    assert b'SYNTHETIC_PRIVATE_OUTPUT' in result
    assert 'SYNTHETIC_PRIVATE_OUTPUT' not in (tmp_path/'step-01.log').read_text()
