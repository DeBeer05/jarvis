"""Public traffic data cannot authorize actions or masquerade as route timings."""
import gzip
from datetime import datetime,UTC
import pytest
from server.natural.traffic import records,nearby
from tests.test_calendar_dialogue import calendar as calendar
from tests.test_chat_automation import tools_chat as tools_chat,call

NOW=datetime(2030,1,1,tzinfo=UTC).timestamp()
XML=b'''<root xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><publicationTime>2030-01-01T00:00:00Z</publicationTime><situationRecord xsi:type="sit:Accident"><latitude>52.4</latitude><longitude>4.6</longitude><roadNumber>A9</roadNumber></situationRecord></root>'''

def test_current_incidents_are_filtered_and_never_claim_delay():
    data=records(gzip.compress(XML),NOW)
    result=nearby(data,{'name':'Testplaats','latitude':52.4,'longitude':4.6})
    assert result['items']==[{'text':'Ongeval op A9','distance_km':0.0}] and result['route_delay_verified'] is False
    assert nearby(data,{'name':'Andere plaats','latitude':1.,'longitude':1.})['items']==[]

@pytest.mark.parametrize('raw',[b'invalid',gzip.compress(XML.replace(b'2030-01-01',b'2000-01-01')),gzip.compress(b'<!DOCTYPE x [<!ENTITY x "bad">]><root/>'),gzip.compress(b'x'*12_000_001)])
def test_bad_stale_or_expanding_feed_is_rejected(raw):
    with pytest.raises(ValueError):records(raw,NOW)

def test_traffic_topic_uses_read_grant_without_model(calendar):
    app,c,router,_,_=calendar;calls=[]
    async def traffic(location):
        calls.append(location);return {'location':location,'items':[{'text':'Ongeval op A9','distance_km':3.0}]}
    app.state.natural.briefings.sources.traffic=traffic
    answer=call(c,'Hoe is het verkeer rond Testplaats?').json()
    assert 'Ongeval op A9' in answer['message'] and calls==['Testplaats']
    assert not router.planning_calls and not app.state.automation.store.items()


def test_independent_public_sources_run_in_parallel_and_same_key_is_shared():
    import asyncio
    from server.natural.public_sources import PublicSources
    async def check():
        sources=PublicSources();started={'a':asyncio.Event(),'b':asyncio.Event()};calls=[]
        async def load(name,other):
            calls.append(name);started[name].set();await started[other].wait();await asyncio.sleep(.01);return {'name':name}
        result=await asyncio.wait_for(asyncio.gather(sources.cached(('a',),lambda:load('a','b'),60),sources.cached(('b',),lambda:load('b','a'),60),sources.cached(('a',),lambda:load('a','b'),60)),1)
        assert [item['name'] for item in result]==['a','b','a'] and sorted(calls)==['a','b']
        assert not sources.loads
    asyncio.run(check())
