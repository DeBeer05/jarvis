"""Full authenticated conversations, synthetic Calendar API and no model calls."""
import copy
from datetime import datetime,timedelta

import pytest

from tests.test_chat_automation import tools_chat as tools_chat,call


@pytest.fixture
def calendar(tools_chat):
    app,client,router=tools_chat;events={};writes=[]
    document=client.get('/api/v1/natural/settings').json()
    assert client.patch('/api/v1/natural/settings/autonomy',json={'revision':document['revision'],'changes':{'actions':{}}}).status_code==200
    async def change(tool,payload,key):
        writes.append((tool,copy.deepcopy(payload),key))
        identifier=payload.get('event_id') or 'synthetic-event'
        event={**events.get(identifier,{}),'id':identifier,'etag':'v'+str(len(writes)),
            'summary':payload['summary'],'location':payload['location'],'description':payload.get('description'),
            'start':{'dateTime':payload['start']},'end':{'dateTime':payload['end']},'attendees':[]}
        events[identifier]=event;return copy.deepcopy(event)
    async def api(feature,path,**kwargs):return copy.deepcopy(events[path.rsplit('/',1)[1]])
    async def analyze(*args):return {'conflicts':[]}
    app.state.automation.integrations.change=change
    app.state.automation.integrations.api=api
    app.state.automation.reschedule.analyze=analyze
    return app,client,router,events,writes


def test_create_correct_time_location_and_date_keep_same_verified_event(calendar):
    app,c,router,events,writes=calendar
    response=call(c,"Kun je voor morgen om twee uur 's middags een afspraak maken die Uitje met Noah heet?").json()
    assert 'staat morgen om 14:00' in response['message'],response
    conversation=response['conversation_id']
    assert len(writes)==1 and writes[0][1]['summary']=='Uitje met Noah'
    payload=writes[0][1]
    assert datetime.fromisoformat(payload['end'])-datetime.fromisoformat(payload['start'])==timedelta(hours=1)
    events['synthetic-event']['description']='Bestaande beschrijving'
    for command in ('Maak daar drie uur van.','Zet Utrecht erbij.','Verplaats hem naar overmorgen.'):
        result=call(c,command,conversation).json()
        assert 'niet bevestigd' not in result['message'] and 'voorstel' not in result['message'].lower(),result
    assert len(writes)==4 and all(item[1]['event_id']=='synthetic-event' for item in writes[1:])
    latest=events['synthetic-event']
    assert datetime.fromisoformat(latest['start']['dateTime']).hour==15
    assert latest['location']=='Utrecht' and latest['description']=='Bestaande beschrijving'
    assert latest['summary']=='Uitje met Noah' and not router.planning_calls


def test_missing_title_is_the_only_question_and_survives_restart(calendar):
    app,c,router,events,writes=calendar
    first=call(c,'Maak morgen om 14:00 een afspraak.').json()
    assert 'titel' in first['message'].lower() and not writes
    app.state.chat.automation_chat.references.clear()
    second=call(c,'Teamoverleg',first['conversation_id']).json()
    assert 'Teamoverleg staat morgen om 14:00' in second['message'],second
    assert len(writes)==1 and not router.planning_calls


def test_missing_clock_followup_does_not_need_last_question_position(calendar):
    app,c,router,events,writes=calendar
    first=call(c,'Maak morgen een afspraak genaamd Controle.').json()
    assert 'begint' in first['message']
    call(c,'Hallo',first['conversation_id'])
    app.state.chat.automation_chat.references.clear()
    result=call(c,"Om half drie 's middags",first['conversation_id']).json()
    assert '14:30' in result['message'] and len(writes)==1,result


def test_failure_does_not_claim_calendar_success(calendar):
    app,c,router,events,writes=calendar
    async def failed(*args):raise ValueError('synthetic API failure')
    app.state.automation.integrations.change=failed
    result=call(c,'Maak morgen om 14:00 een afspraak met titel Controle.').json()
    assert 'staat morgen' not in result['message'] and 'Aangepast' not in result['message']


def test_approval_permission_is_never_granted_by_calendar_command(calendar):
    app,c,router,events,writes=calendar
    with app.state.automation.store.db(True) as db:db.execute("DELETE FROM auth_permissions WHERE permission='automation:approve'")
    result=call(c,'Maak morgen om 14:00 een afspraak genaamd Controle.').json()
    assert not writes and 'automation:approve' in result['message']


@pytest.mark.parametrize('command,summary,clock',[
    ('Plan Teamoverleg op 28 november 2026 om half drie in mijn agenda.','Teamoverleg','14:30'),
    ('Maak een afspraak voor 28 november 2026 om 16:10 genaamd Controle.','Controle','16:10'),
    ('Zet morgen om twee uur middags een afspraak met Anika in mijn agenda.','Afspraak met Anika','14:00'),
    ('Maak overmorgen, om half, drie, een afspraak met de titelcontrole.','controle','14:30'),
    ('Maak overmorgen, om half, drie, een afspraak met de titel, teamoverleg.','teamoverleg','14:30'),
    ('Maak morgen om 14:00 een afspraak die Geen uitje en plan maken heet.','Geen uitje en plan maken','14:00'),
    ('Ik wil dat je morgen om 14:00 een afspraak maakt die Controle heet.','Controle','14:00'),
    ('Jarvis, kun je voor 28 november 2026 een afspraak in mijn agenda zetten dat heet uit je met Noah om twee uur middags.','uit je met Noah','14:00'),
])
def test_generic_titles_dates_and_times_without_a_planner(calendar,command,summary,clock):
    app,c,router,events,writes=calendar
    response=call(c,command).json()
    assert len(writes)==1,response
    assert writes[0][1]['summary']==summary and clock in writes[0][1]['start']
    assert not router.planning_calls


def test_relative_date_uses_server_clock_in_amsterdam(calendar):
    app,c,router,events,writes=calendar
    app.state.automation.store.clock=lambda:datetime.fromisoformat('2026-11-27T23:30:00+00:00').timestamp()
    result=call(c,'Maak morgen om 14:00 een afspraak genaamd Controle.').json()
    assert writes and writes[0][1]['start']=='2026-11-29T14:00:00+01:00',result


def test_conflicting_stt_day_is_clarified_once_without_guessing(calendar):
    app,c,router,events,writes=calendar
    first=call(c,"Maak vanmorgen om twee uur 's middags een afspraak genaamd Controle.").json()
    assert 'vandaag of morgen' in first['message'] and not writes
    second=call(c,'Morgen',first['conversation_id']).json()
    assert 'staat morgen om 14:00' in second['message'] and len(writes)==1,second


def test_optional_fields_and_title_before_date_do_not_add_questions(calendar):
    app,c,router,events,writes=calendar
    response=call(c,'Maak een afspraak genaamd Controle voor morgen om 14:00, locatie Utrecht, beschrijving Korte wandeling.').json()
    assert len(writes)==1,response
    payload=writes[0][1]
    assert payload['summary']=='Controle' and payload['location']=='Utrecht' and payload['description']=='Korte wandeling'


def test_changed_payload_cannot_inherit_direct_request_authority(calendar):
    app,c,router,events,writes=calendar;manager=app.state.automation.approvals
    original=manager.challenge
    def change(identifier,principal):
        with app.state.automation.store.db(True) as db:
            row=db.execute('SELECT payload FROM automation_jobs WHERE id=?',(identifier,)).fetchone()
            import json
            value=json.loads(row[0]);value['summary']='Changed after instruction'
            db.execute('UPDATE automation_jobs SET payload=? WHERE id=?',(json.dumps(value),identifier))
        return original(identifier,principal)
    manager.challenge=change
    response=call(c,'Maak morgen om 14:00 een afspraak genaamd Controle.').json()
    assert not writes and 'Voorstel-ID' in response['message']


@pytest.mark.parametrize('message',[
    'Ik wilde morgen om 14:00 een afspraak maken die Controle heet.',
    'Hoe maak ik morgen om 14:00 een afspraak die Controle heet?',
    'Ik wil weten hoe ik morgen om 14:00 een afspraak kan maken die Controle heet.',
])
def test_mentions_and_how_to_questions_do_not_authorize_creation(calendar,message):
    app,c,router,events,writes=calendar
    router.plans=[{'chat':True}]
    call(c,message)
    assert not writes and not app.state.automation.store.items()


def test_unclear_followup_time_is_asked_once_and_updates_same_event(calendar):
    app,c,router,events,writes=calendar
    first=call(c,'Maak morgen om 14:00 een afspraak genaamd Controle.').json()
    unclear=call(c,'Verplaats hem naar morgen om kort over vier.',first['conversation_id']).json()
    assert 'exact tijdstip' in unclear['message'] and len(writes)==1
    final=call(c,'Kwart over vier',first['conversation_id']).json()
    assert len(writes)==2 and '16:15' in writes[-1][1]['start'],final
    assert writes[-1][1]['event_id']=='synthetic-event'


def test_new_mail_proposal_cannot_make_a_followup_edit_the_old_calendar_event(calendar):
    app,c,router,events,writes=calendar
    first=call(c,'Maak morgen om 14:00 een afspraak genaamd Controle.').json()
    principal=app.state.security.store.authenticate(c.cookies.get('jarvis_access'))
    app.state.automation.submit(principal.device_id,'EmailSend',{'draft_id':'synthetic-draft','message_hash':'a'*64,'preview':'Aan: example@example.invalid\nOnderwerp: Test\nHallo'},'synthetic-mail')
    call(c,'Toon mijn voorstellen',first['conversation_id'])
    call(c,'Zet Utrecht erbij',first['conversation_id'])
    assert len(writes)==1 and events['synthetic-event']['location']==''


def test_named_calendar_keeps_existing_verified_lookup_instead_of_default(tools_chat):
    app,c,router=tools_chat
    router.plans=[{'tool':'CalendarList','input':{}},{'tool':'CalendarCreate','input':{'calendar_id':'selected','summary':'Controle'}}]
    async def calendars():return {'items':[{'id':'selected','summary':'Werk','accessRole':'owner'}]}
    app.state.automation.integrations.calendar_list=calendars
    response=call(c,'Maak morgen om 14:00 een afspraak genaamd Controle in de agenda genaamd Werk.').json()
    import json
    jobs=app.state.automation.store.items()
    assert len(jobs)==1 and json.loads(jobs[0]['payload'])['calendar_id']=='selected',response
