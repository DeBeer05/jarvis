import base64
import json
import struct
import zlib
import asyncio
from dataclasses import replace
from uuid import uuid4

import pytest
import httpx

from server.natural.vision import validate_png
from tests.test_chat_automation import tools_chat as tools_chat
from tests.test_natural_context import patch
from tests.test_natural_presence import consent
from server.ai.providers import TextProvider,ProviderError


def png():
    def chunk(kind,body):return struct.pack('>I',len(body))+kind+body+struct.pack('>I',zlib.crc32(kind+body))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\0\x20\x40\x60'))+chunk(b'IEND',b'')


def body(c=None):return {'request_id':str(uuid4()),'settings_revision':c.get('/api/v1/natural/settings').json()['revision'] if c else 0,'image':base64.b64encode(png()).decode(),'question':'Beschrijf deze fictieve testkleur.'}


def setup(app,c,router):
    from server.ai.router import AIRouter
    # This fixture's bounded_result normally mocks a tool planner; image analysis
    # exercises the real router against its synthetic text providers instead.
    router.bounded_result=lambda messages,mode=None:AIRouter.bounded_result(router,messages,mode)
    consent(c,screen_allowed=True)
    patch(c,'vision',{'enabled':True,'provider':'gemini','cloud_allowed':True,'daily_requests':1})
    provider=router.providers['gemini']
    async def image_message(question,image):
        assert base64.b64decode(image)==png()
        return {'role':'user','content':[{'type':'text','text':question},{'type':'image_url','image_url':{'url':'data:image/png;base64,'+image}}]}
    provider.image_message=image_message
    provider.chunks=(json.dumps({'observations':['Een fictief kleurvlak.'],'uncertainty':[],'suggestions':[]}),)
    return provider


def test_bounded_png_rejects_metadata_polyglots_and_expansion():
    assert validate_png(png())==(1,1)
    for raw in (png()+b'private trailing data',png()[:-1],b'not an image',png().replace(b'IHDR',b'tEXt')):
        with pytest.raises(ValueError):validate_png(raw)


def test_image_analysis_needs_both_consents_and_cannot_run_in_private_mode(tools_chat):
    app,c,router=tools_chat
    assert c.post('/api/v1/natural/vision',json=body(c)).status_code==403
    setup(app,c,router)
    patch(c,'vision',{'cloud_allowed':False})
    assert c.post('/api/v1/natural/vision',json=body(c)).status_code==403
    patch(c,'vision',{'cloud_allowed':True});patch(c,'presence',{'mode':'private'})
    assert c.post('/api/v1/natural/vision',json=body(c)).status_code==403
    assert not any(provider.calls for provider in router.providers.values())


def test_image_is_not_stored_no_tools_and_atomic_daily_budget_replay(tools_chat):
    app,c,router=tools_chat;provider=setup(app,c,router);request=body(c)
    response=c.post('/api/v1/natural/vision',json=request)
    assert response.status_code==200,response.text
    result=response.json()
    assert result['report']['observations']==['Een fictief kleurvlak.'] and not result['image_stored'] and not result['actions_executed']
    assert c.post('/api/v1/natural/vision',json=request).status_code==400
    assert c.post('/api/v1/natural/vision',json=body(c)).status_code==429
    assert len(provider.calls)==1 and not router.planning_calls and not app.state.automation.store.items()
    assert c.get('/api/v1/natural/vision/usage').json()['used_today']==1
    with app.state.natural.store.database.connection() as db:
        rows=db.execute('SELECT * FROM natural_vision_requests').fetchall()
        assert len(rows)==1 and request['image'] not in repr(rows) and request['question'] not in repr(rows)


def test_invalid_provider_report_cannot_be_presented_as_success(tools_chat):
    app,c,router=tools_chat;provider=setup(app,c,router)
    provider.chunks=('Niet het afgesproken beeldrapport.',)
    response=c.post('/api/v1/natural/vision',json=body(c))
    assert response.status_code==400
    assert c.get('/api/v1/natural/vision/usage').json()['used_today']==1


def test_changed_provider_preferences_reject_stale_preview_before_any_model_call(tools_chat):
    app,c,router=tools_chat;provider=setup(app,c,router);request=body(c)
    patch(c,'vision',{'daily_requests':2})
    assert c.post('/api/v1/natural/vision',json=request).status_code==400
    assert not provider.calls and c.get('/api/v1/natural/vision/usage').json()['used_today']==0


def test_actual_provider_adapter_checks_local_capability_without_model_load(settings):
    calls=[]
    def handler(request):
        calls.append(request.url.path)
        assert request.url.path=='/api/show'
        return httpx.Response(200,json={'capabilities':['completion']})
    provider=TextProvider('ollama',settings,client_factory=lambda **options:httpx.AsyncClient(transport=httpx.MockTransport(handler),**options))
    with pytest.raises(ProviderError,match='vision_unsupported'):
        asyncio.run(provider.image_message('test',body()['image']))
    assert calls==['/api/show']
    cloud=TextProvider('gemini',replace(settings,gemini_api_key='synthetic-key'))
    message=asyncio.run(cloud.image_message('test',body()['image']))
    assert message['content'][1]['image_url']['url'].startswith('data:image/png;base64,')
