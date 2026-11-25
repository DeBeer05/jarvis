"""Synthetic end-to-end outing proposals, never real Calendar account changes."""
import json
from datetime import datetime

import pytest

from server.natural.calendar import create_parameters,outing_title
from server.automation.chat import AutomationChat
from tests.test_chat_automation import tools_chat as tools_chat,call


@pytest.mark.parametrize('part',["'s middags",'smiddags','Schmiddags','in de middag','middag'])
def test_spoken_afternoon_applies_to_both_clocks(part):
    payload=create_parameters({'summary':'Uitje met Sam'},f'Plan een uitje op 26 november 2030 om 2 uur {part} tot 5 uur {part}.')
    assert payload['start']=='2030-11-26T14:00:00+01:00'
    assert payload['end']=='2030-11-26T17:00:00+01:00'


@pytest.mark.parametrize('reply',["'s middags",'Schmiddag.','De middag.'])
def test_daypart_reply_is_applied_before_replaying_ambiguous_clock(reply):
    payload=create_parameters({'summary':'Uitje'},'Plan een uitje op 26 november 2030 van 2 tot 5\nAanvullende gegevens van dezelfde gebruiker: '+reply,{'calendar':{'work_start':'00:00','work_end':'23:59'}})
    assert datetime.fromisoformat(payload['start']).hour==14
    assert datetime.fromisoformat(payload['end']).hour==17


def test_start_and_end_keep_their_own_dayparts():
    payload=create_parameters({'summary':'Uitje'},'Plan op 26 november 2030 van 9 uur in de ochtend tot 5 uur in de middag een uitje')
    assert datetime.fromisoformat(payload['start']).hour==9
    assert datetime.fromisoformat(payload['end']).hour==17


def test_complete_spoken_outing_goes_directly_to_exact_preview_then_one_approval(tools_chat):
    app,c,router=tools_chat
    answer=call(c,'Ik wil graag een uitje met Sam toevoegen voor 26 november 2030 om 2 uur smiddags tot 5 uur smiddags.').json()
    assert 'Voorstel-ID' in answer['message'],answer
    assert not router.planning_calls
    jobs=app.state.automation.store.items()
    assert len(jobs)==1 and jobs[0]['status']=='approval'
    payload=json.loads(jobs[0]['payload'])
    assert payload['summary']=='Uitje met Sam'
    assert payload['start']=='2030-11-26T14:00:00+01:00'
    assert payload['end']=='2030-11-26T17:00:00+01:00'
    accepted=call(c,'Ja.',answer['conversation_id']).json()
    assert 'ochtends' not in accepted['message'] and 'goedgekeurd' in accepted['message']
    assert app.state.automation.store.get(jobs[0]['id'])['status']=='queued'
    assert len(app.state.automation.store.items())==1 and not router.planning_calls


def test_one_daypart_followup_then_preview_without_model_or_writes(tools_chat):
    app,c,router=tools_chat
    first=call(c,'Plan een uitje met Sam op 26 november 2030 van 2 tot 5').json()
    assert 'ochtends' in first['message']
    second=call(c,'Schmiddags.',first['conversation_id']).json()
    assert 'Voorstel-ID' in second['message'],second
    assert not router.planning_calls
    rejected=call(c,'Nee.',first['conversation_id']).json()
    assert 'geweigerd' in rejected['message']
    assert app.state.automation.store.items()[0]['status']=='denied'


def test_asking_for_outing_ideas_never_creates_a_calendar_proposal(tools_chat):
    app,c,router=tools_chat
    result=call(c,'Bedenk een aantal leuke uitjes voor zaterdag.').json()
    assert result['status']=='completed'
    assert not router.planning_calls and not app.state.automation.store.items()


@pytest.mark.parametrize('permission',['automation:write','automation:approve'])
def test_fast_outing_path_preserves_current_device_permissions(tools_chat,permission):
    app,c,router=tools_chat
    if permission=='automation:write':
        with app.state.automation.store.db(True) as db:db.execute('DELETE FROM auth_permissions WHERE permission=?',(permission,))
    answer=call(c,'Plan een uitje met Sam op 26 november 2030 van 14:00 tot 17:00').json()
    if permission=='automation:write':
        assert not app.state.automation.store.items()
    else:
        with app.state.automation.store.db(True) as db:db.execute('DELETE FROM auth_permissions WHERE permission=?',(permission,))
        call(c,'Ja.',answer['conversation_id'])
        assert app.state.automation.store.items()[0]['status']=='approval'
    assert not router.planning_calls


@pytest.mark.parametrize('text',['Plan een uitje in agenda Werk morgen om 14:00','Plan een uitje morgen om 14:00 en nodig Sam uit','Plan een uitje morgen om 14:00 op locatie Utrecht'])
def test_complex_calendar_fields_keep_the_existing_planner(text):assert outing_title(text) is None


@pytest.mark.parametrize('text',['Wat betekent een uitje plannen?','Ik heb gisteren een uitje gepland.','Ik wil geen uitje plannen.','Bedenk leuke uitjes.'])
def test_outing_discussion_does_not_authorize_calendar_creation(text):
    assert not AutomationChat.write_intent('CalendarCreate',text)


def test_real_voice_sse_keeps_overview_text_and_only_announces_it(tools_chat):
    app,c,router=tools_chat
    for provider in router.providers.values():provider.chunks=(json.dumps({'spoken':'Ik stel museum en wandeling voor.','options':[{'title':'museum','reason':'Rustig binnen.','environment':'inside'},{'title':'wandeling','reason':'Buiten op eigen tempo.','environment':'outside'}]}),)
    initial=call(c,'Hallo').json()
    session=c.post('/api/v1/natural/conversations/start',json={'conversation_id':initial['conversation_id']}).json()
    for event in ('listening','processing'):
        assert c.post('/api/v1/natural/conversations/'+session['conversation_id']+'/events',json={'event':event,'epoch':session['epoch']}).status_code==200
    response=c.post('/api/v1/chat/stream',json={'message':'Bedenk vijf leuke uitjes voor morgen.','channel':'voice','provider':'ollama','conversation_id':session['conversation_id'],'session_epoch':session['epoch']})
    assert response.status_code==200
    events=[json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
    assert events[0]['speech_protocol']==1 and events[-1]['status']=='completed'
    speech=''.join(e['text'] for e in events if e['type']=='speech')
    assert speech.startswith('Ik werk een passend voorstel voor u uit.')
    assert 'Gewone chat.' not in speech
    written=''.join(e['text'] for e in events if e['type']=='delta')
    assert 'Voorlopige uitjesplanning' in written and 'Mogelijkheden' in written
    assert 'Voorlopige uitjesplanning' not in speech and any(e['type']=='planning' for e in events)
    assert not router.planning_calls and not app.state.automation.store.items()


def test_spoken_put_outing_in_my_calendar_uses_default_without_planner(tools_chat):
    app,c,router=tools_chat
    result=call(c,'Ik wil dat je voor 26 november om twee uur smiddag een uitje met Sam in mijn agenda zet.').json()
    assert 'Voorstel-ID' in result['message'],result
    rows=app.state.automation.store.items()
    assert len(rows)==1 and rows[0]['status']=='approval'
    payload=json.loads(rows[0]['payload'])
    assert payload['summary']=='Uitje met Sam'
    assert datetime.fromisoformat(payload['start']).hour==14
    assert payload['calendar_id']=='primary'
    assert not router.planning_calls


def test_named_calendar_suffix_is_not_dropped():
    assert outing_title('Plan een uitje met Sam morgen om 14:00 in mijn agenda Werk') is None


def test_switch_to_activity_ideas_then_new_agenda_command_keeps_tasks_separate(tools_chat):
    app,c,router=tools_chat
    old=call(c,'Plan een uitje met Alex op 26 november 2030 van 2 tot 5').json()
    assert 'ochtends' in old['message']
    ideas=call(c,'Wat zijn leuke uiten soms te doen in Duitsland met een budget van 50 euro?',old['conversation_id']).json()
    assert 'Voorlopige uitjesplanning' in ideas['message']
    assert not app.state.automation.store.items()
    new=call(c,'Ik wil dat je voor 26 november om twee uur smiddag een uitje met Sam in mijn agenda zet.',old['conversation_id']).json()
    assert 'Voorstel-ID' in new['message'],new
    payload=json.loads(app.state.automation.store.items()[0]['payload'])
    assert payload['summary']=='Uitje met Sam' and datetime.fromisoformat(payload['start']).hour==14
    assert not router.planning_calls
