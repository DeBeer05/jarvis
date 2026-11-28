import asyncio
from types import SimpleNamespace

from tests.test_natural_elevenlabs import premium as premium,PCM
from tests.test_natural_settings_memory import natural as natural


def test_authenticated_pcm_route_uses_premium_voice_and_records_first_chunk(premium):
    app,c,provider,calls=premium
    response=c.post('/api/v1/mobile/speech/stream',json={'text':'Goedemorgen, meneer.'})
    assert response.status_code==200 and response.content==PCM
    assert response.headers['X-JARVIS-Audio-Rate']=='24000'
    assert len([request for request in calls if request.method=='POST'])==1
    metrics=c.get('/api/v1/natural/diagnostics').json()['distributions']
    assert metrics['tts_first_chunk_ms']['count']==1


def test_tts_generator_yields_before_the_last_pcm_chunk(premium):
    app,c,provider,calls=premium
    principal=app.state.security.store.authenticate(c.cookies.get('jarvis_access'))
    config=app.state.natural.settings.runtime(principal)['settings']
    completed=[]
    async def source(*args):
        yield b'\0\0'*100
        await asyncio.sleep(10)
        completed.append(True)
    provider.stream_pcm=source
    async def run():
        request=SimpleNamespace(state=SimpleNamespace(principal=principal))
        stream=app.state.natural.tts.stream_pcm(request,'Een test.',config)
        try:
            rate,pcm=await asyncio.wait_for(anext(stream),.5)
            assert rate==24000 and pcm and not completed
        finally:await stream.aclose()
    asyncio.run(run())


def test_stream_rejects_secret_text_before_premium_call(premium):
    app,c,provider,calls=premium
    response=c.post('/api/v1/mobile/speech/stream',json={'text':'Mijn wachtwoord is: geheim123'})
    assert response.status_code==422 and not [request for request in calls if request.method=='POST']
