"""Conversation contracts through authenticated HTTP; model quality is measured separately."""
import json

import pytest

from tests.test_chat_automation import tools_chat as tools_chat, call, calendar_plan, example_event
from tests.test_natural_context import patch


@pytest.mark.parametrize('message',[
    'Ik heb vandaag echt een lange dag gehad.',
    'Ik heb eigenlijk geen zin in die afspraak morgen.',
    'Die mail van gisteren maakte me aan het lachen.',
    'Mijn agenda voelt deze week wel erg vol.',
    'Misschien ga ik morgen iets leuks doen.',
    'Dat bericht deed me denken aan onze vakantie.',
    'Ik vind herinneringen aan vroeger mooi.',
])
def test_narrative_domain_words_do_not_start_a_tool_plan(tools_chat,message):
    app,c,router=tools_chat
    result=call(c,message).json()
    assert result['status']=='completed' and result['message']=='Gewone chat.'
    assert not router.planning_calls and not app.state.automation.store.items()


def test_planner_chat_rejoins_shared_context_and_streams_without_summary(tools_chat):
    app,c,router=tools_chat
    patch(c,'personality',{'profile':'classic_butler','honorific':'meneer','honorific_frequency':'occasionally'})
    first=call(c,'Ik ben vandaag aan het schilderen geweest.').json()
    provider=router.providers['ollama']
    provider.chunks=('Dat past bij het schilderen. ', 'U kunt daar rustig over nadenken. ',
                     'Een derde zin. ', 'Ook deze gedachte hoort bij het gesprek.')
    router.plans=[{'chat':True}]
    response=c.post('/api/v1/chat/stream',json={'message':'Kun je mijn afspraak toelichten?',
        'provider':'ollama','conversation_id':first['conversation_id'],'channel':'voice'})
    events=[json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
    assert events[-1]['status']=='completed'
    assert events[-1]['message']==''.join(provider.chunks)
    assert 'Ook deze gedachte' in ''.join(e['text'] for e in events if e['type']=='speech')
    first_speech=next(i for i,e in enumerate(events) if e['type']=='speech')
    last_delta=max(i for i,e in enumerate(events) if e['type']=='delta')
    assert first_speech<last_delta
    context=str(provider.calls[-1])
    assert 'schilderen geweest' in context and 'Classic Butler' in context
    assert len(router.planning_calls)==1 and not app.state.automation.store.items()


@pytest.mark.parametrize('kind',['read','write'])
def test_task_question_does_not_swallow_topic_change_or_later_yes(tools_chat,kind):
    app,c,router=tools_chat
    router.plans=[{'clarification':'Welke agenda bedoel je?' if kind=='read' else 'Welke titel wil je?'}]
    first=call(c,'Welke afspraken staan in mijn andere agenda?' if kind=='read' else 'Maak een afspraak in mijn agenda').json()
    expected=1 if kind=='read' else 0
    assert len(router.planning_calls)==expected
    second=call(c,'Ik ben moe en wil even over mijn hobby praten.',first['conversation_id']).json()
    assert second['message']=='Gewone chat.' and len(router.planning_calls)==expected
    third=call(c,'Ja',first['conversation_id']).json()
    assert third['status']=='completed' and len(router.planning_calls)==expected
    assert 'geen voorstel ter bevestiging' in third['message'] if kind=='read' else 'datum en begintijd' in third['message']
    assert not app.state.automation.store.items()


def test_text_receives_the_same_personality_values_as_voice(tools_chat):
    _,c,router=tools_chat
    patch(c,'personality',{'profile':'professional','humor':12,'sarcasm':7})
    for channel in ('text','voice'):
        result=c.post('/api/v1/chat',json={'message':'Een rustige dag vandaag.','provider':'ollama','channel':channel}).json()
        assert result['status']=='completed'
        context=str(router.providers['ollama'].calls[-1])
        assert 'Professioneel' in context and '"humor":12' in context and '"sarcasm":7' in context


@pytest.mark.parametrize('turn_count',[20,50])
def test_long_conversation_keeps_topics_and_provider_context_without_planning(tools_chat,turn_count):
    app,c,router=tools_chat
    # Raise only synthetic fixture rate limits; production admission limits stay intact.
    from dataclasses import replace
    app.state.chat.settings=replace(app.state.chat.settings,requests_per_minute=100)
    cid=None
    for index in range(turn_count):
        message='Mijn schilderproject heet Koperlicht.' if index==0 else f'Ik vertel verder over kleur en muziek, deel {index}.'
        response=call(c,message,cid,provider='gemini' if index==turn_count-1 else 'ollama')
        assert response.status_code==200,response.text
        result=response.json();cid=result['conversation_id']
        assert result['status']=='completed'
    context=router.providers['gemini'].calls[-1]
    assert 'Koperlicht' in str(context) and f'deel {turn_count-2}' in str(context)
    assert context[-1]['content']==f'Ik vertel verder over kleur en muziek, deel {turn_count-1}.'
    assert sum(len(m['content']) for m in context)<=app.state.chat.settings.max_context_chars
    assert not router.planning_calls and not app.state.automation.store.items()


def test_conversation_to_read_task_and_back_preserves_history(tools_chat):
    app,c,router=tools_chat
    async def events(_):return {'items':[example_event()]}
    app.state.automation.integrations.events=events
    first=call(c,'Ik wil morgen tijd overhouden om te schilderen.').json()
    router.plans=[calendar_plan()]
    task=call(c,'Welke afspraken staan er morgen in mijn agenda?',first['conversation_id']).json()
    assert 'Tandarts' in task['message']
    reply=call(c,'Dat vind ik een prettig vooruitzicht.',first['conversation_id']).json()
    assert reply['message']=='Gewone chat.'
    context=str(router.providers['ollama'].calls[-1])
    assert 'schilderen' in context and 'Tandarts' in context
    assert not app.state.automation.store.items()


@pytest.mark.parametrize('message',['Morgen nog afspraken?','Nee, ik wil weten wat er morgen in mijn agenda staat.'])
def test_read_request_does_not_require_a_fixed_command_prefix(tools_chat,message):
    app,c,router=tools_chat
    async def events(_):return {'items':[example_event()]}
    app.state.automation.integrations.events=events
    router.plans=[calendar_plan()]
    result=call(c,message).json()
    assert result['status']=='completed' and 'Tandarts' in result['message']
    assert not app.state.automation.store.items()
