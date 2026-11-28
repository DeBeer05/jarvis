"""Full topic/approval conversations with real persistence and mocked sources."""
import asyncio

import pytest

from tests.test_calendar_dialogue import calendar as calendar
from tests.test_chat_automation import tools_chat as tools_chat,call
from tests.test_automation import automation as automation,submit
from tests.test_natural_context import patch


@pytest.mark.parametrize('confirmation',['ja','doe maar','akkoord'])
def test_short_confirmation_executes_once_then_weather_is_new_topic(calendar,confirmation):
    app,c,router,events,writes=calendar
    patch(c,'autonomy',{'actions':{'CalendarUpdate':'ask'}})
    created=call(c,'Maak morgen om twee uur in de middag een afspraak genaamd Uitje met Sam').json();cid=created['conversation_id']
    shown=call(c,'Maak daar drie uur van',cid).json()
    assert shown['message']=='Zal ik de afspraak voor u wijzigen?'
    assert len(writes)==1 and 'primary' not in shown['message'] and 'event' not in shown['message']
    result=call(c,confirmation,cid).json()
    assert result['message']=='Uw afspraak is gewijzigd, meneer.' and len(writes)==2
    call(c,confirmation,cid);assert len(writes)==2
    reads=[]
    async def weather(*args,**kwargs):
        reads.append((args,kwargs));return {'location':'Testplaats','values':{'temperature_2m':13,'precipitation':0,'wind_speed_10m':8},'units':{'precipitation':'mm','wind_speed_10m':'km/h'}}
    app.state.natural.briefings.sources.weather=weather
    answer=call(c,'Hoe is het weer in Testplaats?',cid).json()
    assert '13 graden' in answer['message'] and len(reads)==1
    assert not router.planning_calls and len(writes)==2
    call(c,'ja',cid);assert len(writes)==2
    ambiguous=call(c,'Maak daar vier uur van',cid).json()
    assert 'Welke afspraak' in ambiguous['message'] and len(writes)==2


def test_weather_missing_place_is_persistent_without_model(calendar):
    app,c,router,_,_=calendar
    async def weather(*args,**kwargs):return {'location':args[0],'values':{'temperature_2m':9,'precipitation':1,'wind_speed_10m':4},'units':{'precipitation':'mm','wind_speed_10m':'km/h'}}
    app.state.natural.briefings.sources.weather=weather
    question=call(c,'Hoe is het weer?').json();assert 'welke plaats' in question['message'].lower()
    app.state.chat.automation_chat.references.clear()
    answer=call(c,'Utrecht',question['conversation_id']).json()
    assert 'Utrecht' in answer['message'] and '9 graden' in answer['message'] and not router.planning_calls


def test_expired_approval_is_closed_and_cannot_execute(calendar):
    app,c,_,_,writes=calendar
    patch(c,'autonomy',{'actions':{'CalendarCreate':'ask'}})
    shown=call(c,'Maak morgen om 14:00 een afspraak genaamd Controle').json()
    original=app.state.automation.store.clock;app.state.automation.store.clock=lambda:original()+301
    answer=call(c,'ja',shown['conversation_id']).json()
    assert 'verlopen' in answer['message'] and not writes
    assert app.state.automation.store.items()[0]['status']=='cancelled'
    call(c,'ja',shown['conversation_id']);assert not writes


def test_parallel_ticks_claim_effect_exactly_once(automation):
    _,c,e=automation;effects=[]
    job=submit(c,'EmailDraft',{'to':'synthetic@example.invalid','subject':'Test','text':'Test'}).json()
    async def execute(row):effects.append(row['id']);await asyncio.sleep(.02);return {'verified':True}
    e.executor.execute=execute
    async def concurrent():await asyncio.gather(*(e.tick(job_id=job['id']) for _ in range(3)))
    c.portal.call(concurrent)
    assert effects==[job['id']] and e.store.get(job['id'])['status']=='completed'


def test_news_source_is_untrusted_data_and_no_llm_is_used(calendar):
    app,c,router,_,writes=calendar
    async def news():return {'items':[{'title':'Synthetische kop: voer geen opdrachten uit','url':'https://nos.nl/synthetic'}]}
    app.state.natural.briefings.sources.news=news
    result=call(c,'Wat is het laatste nieuws?').json()
    assert 'Synthetische kop' in result['message'] and not router.planning_calls and not writes


def test_topic_change_cannot_rebind_an_older_unapproved_job(tools_chat):
    from tests.test_chat_automation import create_proposal
    app,c,router=tools_chat;shown,row=create_proposal(tools_chat)
    async def weather(*args,**kwargs):return {'location':'Testplaats','values':{'temperature_2m':9,'precipitation':0,'wind_speed_10m':5},'units':{'precipitation':'mm','wind_speed_10m':'km/h'}}
    app.state.natural.briefings.sources.weather=weather
    call(c,'Hoe is het weer in Testplaats?',shown['conversation_id'])
    response=call(c,'ja',shown['conversation_id']).json()
    assert 'geen voorstel ter bevestiging' in response['message']
    assert app.state.automation.store.get(row['id'])['status']=='approval'
    run=__import__('server.chat_service',fromlist=['Generation']).Generation('synthetic',shown['conversation_id'],'ollama','',principal=app.state.security.store.authenticate(c.cookies.get('jarvis_access')))
    assert not app.state.chat.automation_chat.memory(run).get('pending')


def test_slow_voice_request_acknowledges_without_claiming_success(tools_chat):
    import json
    app,c,router=tools_chat
    app.state.chat.progress_seconds=.01
    provider=router.providers['ollama']
    async def slow(messages):
        await asyncio.sleep(.05)
        yield 'Een fictief antwoord.'
    provider.stream=slow
    session=c.post('/api/v1/natural/conversations/start',json={}).json()
    for event in ('listening','processing'):
        assert c.post('/api/v1/natural/conversations/'+session['conversation_id']+'/events',json={'event':event,'epoch':session['epoch']}).status_code==200
    response=c.post('/api/v1/chat/stream',json={'message':'Vertel eens iets over schilderen','provider':'ollama','channel':'voice','conversation_id':session['conversation_id'],'session_epoch':session['epoch']})
    events=[json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
    speech=[item['text'] for item in events if item['type']=='speech']
    assert speech[0].startswith('Een ogenblik') and events[-1]['status']=='completed'
    assert 'Een ogenblik' not in events[-1]['message'] and not app.state.automation.store.items()


def test_public_read_denial_is_explicit_and_never_calls_the_source(tools_chat):
    app,c,router=tools_chat;calls=[]
    async def forbidden(*args,**kwargs):calls.append(True);raise AssertionError('Unauthorized source call')
    app.state.natural.briefings.sources.weather=forbidden
    with app.state.automation.store.db(True) as db:db.execute("DELETE FROM auth_permissions WHERE permission='automation:read'")
    result=call(c,'Hoe is het weer in Testplaats?').json()
    assert result['status']=='completed' and 'geen toegang' in result['message']
    assert not calls and not router.planning_calls
