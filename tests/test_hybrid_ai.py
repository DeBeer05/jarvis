"""Oracle pooling/policy, compact prompts and deterministic outage fallback."""
import asyncio,json
import httpx
import pytest
from server.ai.providers import TextProvider,ProviderError
from server.ai.policy import RequestPolicy,use_policy
from server.natural.models import UserSettings
from server.natural.compact import prompt
from server.config import load_settings,ConfigurationError


def test_oracle_uses_loopback_pool_and_preserves_request_timeout(settings):
    requests=[]
    def handle(request):
        requests.append(request)
        assert request.url.host=='127.0.0.1' and request.url.port==11435
        if request.url.path=='/api/tags':return httpx.Response(200,json={'models':[{'name':'qwen2.5:3b'}]})
        body=json.loads(request.content);assert body['think'] is False and 'tools' not in body
        return httpx.Response(200,text=json.dumps({'message':{'content':'Welkom, meneer.'},'done':False})+'\n'+json.dumps({'done':True})+'\n')
    async def check():
        provider=TextProvider('oracle',settings)
        provider._http=httpx.AsyncClient(transport=httpx.MockTransport(handle))
        pool=provider._http
        for _ in range(2):assert ''.join([text async for text in provider.stream([{'role':'user','content':'Hallo'}])])=='Welkom, meneer.'
        assert provider._http is pool and not pool.is_closed
        assert all(request.extensions['timeout']['read'] in (2,settings.provider_timeout_seconds) for request in requests)
        await provider.close();assert pool.is_closed
    asyncio.run(check());assert len(requests)==3


def test_offline_never_enters_oracle_transport(settings):
    async def check():
        provider=TextProvider('oracle',settings)
        document={'revision':1,'settings':UserSettings().model_dump(mode='json')};document['settings']['ai']['offline']=True
        with use_policy(RequestPolicy.from_document(document)):
            with pytest.raises(ProviderError):_=[part async for part in provider.stream([])]
        assert provider._http is None
    asyncio.run(check())


def test_compact_context_preserves_custom_owner_instructions():
    config=UserSettings().model_dump(mode='json');config['personality']['custom_instructions']='Noem mijn project Koperlicht.'
    text=prompt('Een expliciete eigen systeeminstructie.',config,'Hallo',False)
    assert text.startswith('Een expliciete eigen systeeminstructie.') and 'Koperlicht' in text
    assert 'serverbewijs' in text and 'onbetrouwbare' in text and 'u en uw' in text


@pytest.mark.parametrize('address',['http://example.org','https://127.0.0.1:11435','http://127.0.0.1:11435/secret','http://user:secret@127.0.0.1:11435'])
def test_remote_inference_cannot_bypass_ssh_origin(tmp_path,address):
    with pytest.raises(ConfigurationError):load_settings(root=tmp_path,environ={'JARVIS_ORACLE_BASE_URL':address})
