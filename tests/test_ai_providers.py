import asyncio
import json
from dataclasses import replace

import httpx
import pytest

from providers.llm_openai import OpenAICompatLLM
from server.ai.providers import ProviderError, TextProvider


def factory(handler):
    return lambda **kwargs: httpx.AsyncClient(transport=httpx.MockTransport(handler), **kwargs)


def response_stream(text="Hallo", *, complete=True):
    result = 'data: ' + json.dumps({"choices": [{"delta": {"content": text}}]}) + '\n\n'
    if complete:
        result += 'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n'
    return httpx.Response(200, text=result)


def test_gemini_official_rest_transport_and_limits(settings):
    canary = "test-canary-" + "not-a-real-key"
    settings = replace(settings, gemini_api_key=canary)
    calls = []

    def handler(request):
        calls.append(request)
        assert str(request.url) == "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        assert request.headers["authorization"] == "Bearer " + canary
        body = json.loads(request.content)
        assert body["model"] == "gemini-3.8-flash" and body["stream"] is True
        assert body["max_tokens"] == settings.max_output_tokens
        assert "tools" not in body and canary not in request.content.decode()
        return response_stream()

    async def check():
        provider = TextProvider("gemini", settings, factory(handler))
        assert [text async for text in provider.stream([{"role": "user", "content": "Hallo"}])] == ["Hallo"]
    asyncio.run(check())
    assert len(calls) == 1


@pytest.mark.parametrize("status,body,expected", [
    (429, {"error": {"message": "quota exhausted"}}, "quota_exceeded"),
    (429, {"error": {"message": "too many requests"}}, "rate_limited"),
    (429, [{"error": {"message": "quota exhausted"}}], "quota_exceeded"),
    (503, [{"error": {"status": "UNAVAILABLE", "message": "high demand"}}], "overloaded"),
    (401, {}, "authentication"), (403, {}, "authentication"),
    (404, {}, "model_missing"), (500, {}, "provider_error"), (503, {}, "overloaded"),
])
def test_provider_http_failures_sanitized(settings, status, body, expected):
    settings = replace(settings, gemini_api_key="test-canary-" + "do-not-expose")
    async def check():
        provider = TextProvider("gemini", settings, factory(lambda request: httpx.Response(status, json=body)))
        with pytest.raises(ProviderError) as error:
            _ = [text async for text in provider.stream([])]
        assert error.value.code == expected
        assert settings.gemini_api_key not in str(error.value)
        assert settings.gemini_api_key not in error.value.message
    asyncio.run(check())


def test_missing_gemini_key_does_not_read_desktop_credentials(settings):
    async def check():
        def unexpected(request):
            pytest.fail("A missing key must not make network requests")
        provider = TextProvider("gemini", settings, factory(unexpected))
        with pytest.raises(ProviderError, match="not_configured"):
            _ = [text async for text in provider.stream([])]
    asyncio.run(check())


def test_ollama_model_probe_cache_and_stream(settings):
    calls = []
    def handler(request):
        calls.append(request.url.path)
        assert "authorization" not in request.headers
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "qwen2.5:3b"}]})
        body = json.loads(request.content)
        assert request.url.path == '/api/chat'
        assert body["model"] == "qwen2.5:3b" and body['think'] is False
        assert body['options']=={'temperature':0.2,'num_ctx':8192,'num_predict':settings.max_output_tokens}
        return httpx.Response(200,text=json.dumps({'message':{'content':'Lokaal antwoord'},'done':True})+'\n')
    async def check():
        provider = TextProvider("ollama", settings, factory(handler))
        assert (await provider.availability())["available"]
        assert (await provider.availability())["available"]
        assert [text async for text in provider.stream([])] == ["Lokaal antwoord"]
    asyncio.run(check())
    assert calls == ["/api/tags", "/api/chat"]


def test_missing_ollama_model(settings):
    async def check():
        provider = TextProvider("ollama", settings, factory(lambda request: httpx.Response(200, json={"models": []})))
        assert (await provider.availability())["state"] == "model_missing"
        with pytest.raises(ProviderError, match="model_missing"):
            _ = [text async for text in provider.stream([])]
    asyncio.run(check())


@pytest.mark.parametrize('frames',[
    ['{bad}'],
    ['[]'],
    [json.dumps({'message':{'content':[]},'done':True})],
    [json.dumps({'message':{'content':'x'},'done':'true'})],
    [json.dumps({'message':{'content':'x'}})],
    [json.dumps({'message':{'thinking':'hidden'}})],
    [json.dumps({'message':{'content':'','tool_calls':[{}]},'done':True})],
])
def test_native_ollama_rejects_malformed_or_unfinished_output(settings,frames):
    def handler(request):
        if request.url.path=='/api/tags':return httpx.Response(200,json={'models':[{'name':settings.ollama_model}]})
        return httpx.Response(200,text='\n'.join(frames)+'\n')
    async def scenario():
        provider=TextProvider('ollama',settings,factory(handler))
        with pytest.raises(ProviderError,match='invalid_response'):
            _=[part async for part in provider.stream([{'role':'user','content':'Hallo'}])]
    asyncio.run(scenario())


def test_native_ollama_context_allocation_tracks_request_and_keeps_roles(settings):
    from server.ai.policy import RequestPolicy,use_policy
    from server.natural.models import UserSettings
    config=UserSettings().model_dump(mode='json')
    config['ai'].update(context_tokens=10000,maximum_answer_tokens=2048)
    policy=RequestPolicy.from_document({'revision':1,'settings':config})
    messages=[{'role':'system','content':'Stijl'},{'role':'user','content':'Eerder'},
              {'role':'assistant','content':'Reactie'},{'role':'user','content':'Nu'}]
    def handler(request):
        if request.url.path=='/api/tags':return httpx.Response(200,json={'models':[{'name':settings.ollama_model}]})
        body=json.loads(request.content)
        assert body['messages']==messages and body['options']['num_ctx']==13312
        assert body['options']['num_predict']==2048 and 'max_tokens' not in body
        return httpx.Response(200,text=json.dumps({'message':{'content':'Antwoord','thinking':'never spoken'},'done':True})+'\n')
    async def scenario():
        with use_policy(policy):
            provider=TextProvider('ollama',settings,factory(handler))
            assert [part async for part in provider.stream(messages)]==['Antwoord']
    asyncio.run(scenario())


def test_native_ollama_is_explicit_opt_in_for_shared_transport():
    transport=OpenAICompatLLM({'base_url':'http://127.0.0.1:11434/v1','model':'example','strict_text':True})
    assert not transport._ollama_chat
    assert 'options' not in transport._body([{'role':'user','content':'Hallo'}],None,True,.2)


def test_planning_schema_is_request_local_and_transport_opt_in(settings):
    from server.ai.policy import next_structured,structured_schema
    from server.natural.planning_models import PlanningReply
    schema=PlanningReply.model_json_schema();bodies=[]
    def handler(request):
        if request.url.path=='/api/tags':return httpx.Response(200,json={'models':[{'name':settings.ollama_model}]})
        bodies.append(json.loads(request.content))
        return httpx.Response(200,text=json.dumps({'message':{'content':'{}'},'done':True})+'\n')
    async def scenario():
        provider=TextProvider('ollama',settings,factory(handler))
        source=provider.stream([{'role':'user','content':'Ideeën'}])
        assert await next_structured(source,schema)=='{}'
        assert structured_schema.get() is None
        await source.aclose()
        assert [part async for part in provider.stream([{'role':'user','content':'Hallo'}])]==['{}']
        async def failure():
            assert structured_schema.get()==schema
            raise asyncio.CancelledError()
            yield ''
        with pytest.raises(asyncio.CancelledError):await next_structured(failure(),schema)
        assert structured_schema.get() is None
    asyncio.run(scenario())
    assert bodies[0]['format']==schema and 'format' not in bodies[1]
    legacy=OpenAICompatLLM({'base_url':'http://127.0.0.1:11434/v1','model':'example','json_schema':schema})
    assert 'response_format' not in legacy._body([{'role':'user','content':'Hallo'}],None,True,.2)


@pytest.mark.parametrize("problem,expected", [(httpx.ReadTimeout, "timeout"), (httpx.ConnectError, "unavailable")])
def test_provider_network_errors(settings, problem, expected):
    def fail(request):
        raise problem("private upstream diagnostic", request=request)
    async def check():
        provider = TextProvider("gemini", replace(settings, gemini_api_key="canary"), factory(fail))
        with pytest.raises(ProviderError, match=expected) as error:
            _ = [text async for text in provider.stream([])]
        assert "private" not in error.value.message
    asyncio.run(check())


@pytest.mark.parametrize("response", [response_stream(complete=False), httpx.Response(200, text="data: {invalid}\n\n")])
def test_incomplete_or_malformed_stream_is_an_error(settings, response):
    async def check():
        provider = TextProvider("gemini", replace(settings, gemini_api_key="canary"), factory(lambda request: response))
        with pytest.raises(ProviderError, match="invalid_response"):
            _ = [text async for text in provider.stream([])]
    asyncio.run(check())


def test_strict_transport_does_not_silently_switch_models(settings):
    legacy = OpenAICompatLLM({"base_url": "https://generativelanguage.googleapis.com/v1beta/openai", "api_key": "canary", "model": "gemini-3.8-flash"})
    strict = OpenAICompatLLM({"base_url": legacy.base, "api_key": "canary", "model": legacy.model, "strict_text": True})
    assert len(legacy._gemini_order()) > 1
    assert strict._gemini_order() == ["gemini-3.8-flash"]


def test_content_filter_does_not_become_technical_fallback(settings):
    frame = httpx.Response(200, text='data: {"choices":[{"delta":{},"finish_reason":"content_filter"}]}\n\n')
    async def check():
        provider = TextProvider("gemini", replace(settings, gemini_api_key="canary"), factory(lambda request: frame))
        with pytest.raises(ProviderError) as error:
            _ = [text async for text in provider.stream([])]
        assert error.value.code == "content_filtered" and not error.value.retryable
    asyncio.run(check())
