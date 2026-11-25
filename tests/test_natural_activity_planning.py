"""Authenticated draft planning using synthetic providers/calendars only."""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from tests.test_chat_automation import tools_chat as tools_chat,call
from tests.ai_helpers import FakeProvider
from server.natural.planning_models import PlanningState,Fact,Cost
from server.natural.planning_extract import extract
from server.natural.planning_math import cost_summary,free_blocks,fuel_cost,rebuild
from server.natural.models import UserSettings


@pytest.fixture
def planner(tools_chat):
    app,c,router=tools_chat
    async def events(payload):return {'items':[]}
    app.state.automation.integrations.events=events
    reply=json.dumps({'spoken':'Ik stel een ontspannen activiteit voor; de tijden blijven voorlopig.','options':[{'title':'Museum','reason':'Een binnenactiviteit met ruimte voor een pauze.','environment':'inside'},{'title':'Wandeling','reason':'Buiten op uw eigen tempo.','environment':'outside'}],'proposals':{}},ensure_ascii=False)
    for provider in router.providers.values():provider.chunks=(reply,)
    return app,c,router


def document(c,conversation):
    response=c.get('/api/v1/natural/planning/'+conversation)
    assert response.status_code==200,response.text
    return response.json()['planning']


def test_brainstorm_is_not_a_calendar_form_or_write(planner):
    app,c,router=planner
    answer=call(c,'Ik wil dit weekend iets leuks doen met mijn vriend.').json()
    assert answer['status']=='completed',answer
    plan=document(c,answer['conversation_id'])
    assert len(plan['state']['alternatives'])==2
    assert plan['state']['facts']['participants']['value']==['mijn vriend']
    assert not app.state.automation.store.items() and not router.planning_calls


def test_multi_slot_and_flexible_afternoon_are_source_bound(planner):
    _,c,_=planner
    reply=call(c,'Ik wil zaterdagmiddag rond twee uur met Sam naar een dierentuin, maar maximaal honderd euro uitgeven.').json()
    plan=document(c,reply['conversation_id'])['state'];facts=plan['facts']
    assert facts['activity']['value']=='dierentuin'
    assert facts['clock']['value']=='14:00'
    assert facts['participants']['value']==['Sam']
    assert facts['budget']['value']==100 and facts['budget']['origin']=='user'
    assert facts['flexible']['value'] is True
    assert facts['duration_minutes']['origin']=='proposal'
    assert datetime.fromisoformat(facts['date']['value']).weekday()==5


def test_modifications_keep_other_slots_and_no_preference_can_be_proposed(planner):
    _,c,_=planner
    first=call(c,'Ik wil zaterdagmiddag met Sam naar een museum. Maximaal honderd euro samen.').json()
    second=call(c,'Doe toch maar zondag en een uurtje later.',first['conversation_id']).json()
    facts=document(c,second['conversation_id'])['state']['facts']
    assert datetime.fromisoformat(facts['date']['value']).weekday()==6
    assert facts['budget']['value']==100 and facts['participants']['value']==['Sam']
    assert facts['clock']['value']=='14:00'


def test_liking_an_option_never_authorizes_booking_or_calendar(planner):
    app,c,_=planner
    first=call(c,'Bedenk iets leuks voor zondag.').json()
    call(c,'Een museum klinkt leuk.',first['conversation_id'])
    call(c,'Dat klinkt leuk.',first['conversation_id'])
    assert not app.state.automation.store.items()


def test_selected_plan_commits_only_via_full_existing_preview(planner):
    app,c,_=planner
    first=call(c,'Ik wil zondagmiddag met Sam naar een museum.').json()
    preview=call(c,'Zet het maar in mijn agenda.',first['conversation_id']).json()
    assert 'Voorstel-ID' in preview['message'],preview
    assert len(app.state.automation.store.items())==1
    assert app.state.automation.store.items()[0]['status']=='approval'
    denied=call(c,'Nee.',first['conversation_id']).json()
    assert 'geweigerd' in denied['message']
    assert app.state.automation.store.items()[0]['status']=='denied'


def test_calendar_unavailable_is_not_free_time(planner):
    app,c,_=planner
    async def unavailable(payload):raise ValueError('not configured')
    app.state.automation.integrations.events=unavailable
    first=call(c,'Ik wil zondag iets leuks doen.').json()
    plan=document(c,first['conversation_id'])
    assert plan['state']['calendar']['status']=='unavailable'
    assert 'niet bevestigd' in plan['overview']


def test_decimal_costs_budget_and_unknown_total():
    state=PlanningState(facts={'budget':Fact(value=30.0,origin='user')},costs=[Cost(name='tickets',amount=19.95,quantity=2),Cost(name='parkeren',amount=3.5)])
    summary=cost_summary(state)
    assert summary['known_subtotal']==43.4 and summary['over_budget']
    assert summary['total'] is None and not summary['complete']
    assert fuel_cost(120,6.5,1.87)==14.59


def test_verified_calendar_blocks_conflicts_and_incomplete_results():
    zone=ZoneInfo('Europe/Amsterdam')
    begin=datetime(2030,1,1,9,tzinfo=zone);end=begin.replace(hour=18)
    item={'start':{'dateTime':begin.replace(hour=11).isoformat()},'end':{'dateTime':begin.replace(hour=13).isoformat()}}
    free=free_blocks([item],begin,end,buffer_minutes=15)
    assert free['status']=='verified' and len(free['blocks'])==2
    assert free['blocks'][1]['start'].endswith('13:15:00+01:00')
    assert free_blocks([item],begin,end,incomplete=True)['status']=='incomplete'


def test_private_planning_never_creates_durable_plan(planner):
    app,c,_=planner
    config=c.get('/api/v1/natural/settings').json()
    assert c.patch('/api/v1/natural/settings/memory',json={'revision':config['revision'],'changes':{'history':False}}).status_code==200
    first=call(c,'Bedenk iets leuks voor zondag.').json()
    assert document(c,first['conversation_id']) is not None
    with app.state.natural.store.database.connection() as db:
        assert db.execute("SELECT count(*) FROM natural_pending WHERE kind='activity_plan'").fetchone()[0]==0


@pytest.mark.parametrize('turns,key,value',[
    (['Ik wil dit weekend iets leuks doen.','Een museum klinkt leuk.','Niet te ver weg.'],'activity','museum'),
    (['Ik wil zaterdagmiddag met Sam naar een museum, maximaal honderd euro.','Doe toch maar zondag.','Een uurtje later.'],'clock','14:00'),
    (['Verzin een leuke date voor zondag.','Maakt me niet uit, verras me.','Het moet betaalbaar blijven.'],'activity','date'),
    (['Ik wil morgen met Alex iets binnen doen.','Liever een museum.','Haal het museum eruit.'],'environment','inside'),
    (['Bedenk iets leuks voor morgen.','Een museum klinkt leuk.','Dat klinkt leuk.'],'activity','museum'),
    (['Ik wil zondag een dagtrip naar Utrecht met Sam.','Laten we met de trein gaan.','Ik wil eerst Alex ophalen.'],'pickup','Alex'),
    (['Wat kunnen we morgen doen? Het regent.','Een museum klinkt leuk.','Maak het iets goedkoper.'],'environment','inside'),
    (['Ik wil dit weekend iets leuks doen met Sam.','Hoe werkt een database-index?','Ga terug naar de planning, liever zondag.'],'participants',['Sam']),
    (['Ik wil zaterdag met Sam naar een museum. Tickets 20 euro per persoon.','Parkeren 5 euro totaal. Maximaal veertig euro samen.','Laten we toch met de trein gaan.'],'transport','train'),
    (['Ik wil zondag iets romantisch doen.','Kunnen we daarna ergens eten?','Doe toch maar zondag.'],'meal','eten'),
])
def test_ten_complete_conversations_preserve_shared_state(planner,turns,key,value):
    app,c,_=planner;conversation=None
    for text in turns:
        response=call(c,text,conversation).json()
        assert response['status']=='completed',response
        conversation=response['conversation_id']
    state=document(c,conversation)['state']
    assert state['facts'][key]['value']==value
    assert not app.state.automation.store.items()


def test_cost_change_and_participant_change_recompute_without_invented_total():
    config={**UserSettings().planning.model_dump(),'timezone':'Europe/Amsterdam'}
    state=extract(PlanningState(),'Ik wil zaterdag met Sam naar een museum. Tickets 20 euro per persoon. Maximaal 40 euro samen.',config)
    assert cost_summary(state)['known_subtotal']==40
    extract(state,'Voeg Alex toe.',config)
    assert cost_summary(state)['known_subtotal']==60 and cost_summary(state)['over_budget']
    extract(state,'Zonder Alex.',config)
    assert cost_summary(state)['known_subtotal']==40
    rebuild(state,config)
    assert cost_summary(state)['total'] is None


def test_invalid_or_authoritative_model_json_cannot_write(planner):
    app,c,router=planner
    router.providers['ollama']=FakeProvider((json.dumps({'spoken':'Geboekt!','options':[],'tool':'CalendarCreate','approved':True}),))
    answer=call(c,'Bedenk iets leuks voor zondag.').json()
    plan=document(c,answer['conversation_id'])
    assert plan['state']['model_status']=='invalid' and not app.state.automation.store.items()
    assert 'geen bruikbaar voorstel' in answer['message']


def test_brainstorm_speech_uses_actual_options_instead_of_model_factual_claims(planner):
    _,c,router=planner
    router.providers['ollama']=FakeProvider((json.dumps({'spoken':'Morgen om 16:00 is uw afspraak bevestigd in de kelder.','options':[{'title':'museum','environment':'inside'},{'title':'bioscoop','environment':'inside'}]}),))
    answer=call(c,'Bedenk iets leuks voor zondag.').json()
    assert answer['message'].startswith('Ik denk aan museum, bioscoop.')
    assert 'kelder' not in answer['message'] and 'afspraak bevestigd' not in answer['message']


def test_repeated_commit_reuses_exact_preview_and_one_yes(planner):
    app,c,_=planner
    first=call(c,'Ik wil zondagmiddag met Sam naar een museum.').json()
    preview=call(c,'Zet het maar in mijn agenda.',first['conversation_id']).json()
    repeated=call(c,'Zet het maar in mijn agenda.',first['conversation_id']).json()
    assert len(app.state.automation.store.items())==1
    assert 'Voorstel-ID' in repeated['message'] and 'Voorstel-ID' in preview['message']
    call(c,'Ja.',first['conversation_id'])
    assert app.state.automation.store.items()[0]['status']=='queued'


def test_changed_plan_replaces_old_preview_and_needs_new_approval(planner):
    app,c,_=planner
    first=call(c,'Ik wil zondagmiddag met Sam naar een museum.').json()
    call(c,'Zet het maar in mijn agenda.',first['conversation_id'])
    call(c,'Een uurtje later.',first['conversation_id'])
    call(c,'Zet het maar in mijn agenda.',first['conversation_id'])
    rows=app.state.automation.store.items()
    assert sorted(row['status'] for row in rows)==['approval','cancelled']


def test_no_calendar_permission_never_reads_or_claims_availability(planner):
    app,c,_=planner;called=[]
    async def forbidden(payload):called.append(payload);return {'items':[]}
    app.state.automation.integrations.events=forbidden
    with app.state.automation.store.db(True) as db:db.execute("DELETE FROM auth_permissions WHERE permission='automation:read'")
    first=call(c,'Bedenk iets leuks voor zondag.').json()
    assert document(c,first['conversation_id'])['state']['calendar']['status']=='unavailable' and not called


def test_conditional_confirmation_is_waiting_and_not_execution(planner):
    app,c,_=planner
    first=call(c,'Ik wil zondag met Sam naar een museum.').json()
    answer=call(c,'Als hij bevestigt zet het in mijn agenda.',first['conversation_id']).json()
    assert 'niet beschikbaar' in answer['message']
    assert document(c,first['conversation_id'])['state']['status']=='waiting'
    assert not app.state.automation.store.items()


def test_missing_contact_asks_once_without_fabricating_address(planner):
    app,c,_=planner
    first=call(c,'Ik wil zondag met Sam naar een museum.').json()
    answer=call(c,'Vraag Sam maar of hij kan.',first['conversation_id']).json()
    assert 'geen bericht verstuurd' in answer['message']
    assert not app.state.automation.store.items()


def test_combined_itinerary_and_known_travel_bind_full_calendar_preview(planner):
    app,c,_=planner
    first=call(c,'Ik wil zondagmiddag met Sam naar een museum.').json()
    call(c,'Kunnen we ook nog naar de bioscoop?',first['conversation_id'])
    call(c,'Kunnen we daarna ergens eten?',first['conversation_id'])
    state=document(c,first['conversation_id'])['state']
    assert state['facts']['activity']['value']=='museum' and state['facts']['extra_activities']['value']==['bioscoop']
    assert len(state['timeline'])==3
    call(c,'Zet het maar in mijn agenda.',first['conversation_id'])
    payload=json.loads(app.state.automation.store.items()[0]['payload'])
    assert payload['start']==state['timeline'][0]['start'] and payload['end']==state['timeline'][-1]['end']


def test_known_fuel_inputs_are_calculated_and_transport_change_invalidates_them():
    config={**UserSettings().planning.model_dump(),'timezone':'Europe/Amsterdam'}
    state=extract(PlanningState(),'Ik wil zondag met de auto naar een museum. 120 kilometer. Verbruik 6,5 liter per 100 km, 1,87 euro per liter.',config)
    rebuild(state,config)
    assert next(cost for cost in state.costs if cost.name=='berekende brandstof').amount==14.59
    extract(state,'Laten we met de trein gaan.',config);rebuild(state,config)
    assert not state.costs and 'distance_km' not in state.facts
    rating=extract(PlanningState(),'Ik wil met de auto een uitje doen. Verbruik 6,5 liter per 100 km, 1,87 euro per liter.',config)
    rebuild(rating,config)
    assert 'distance_km' not in rating.facts and not rating.costs


def test_planning_get_is_authenticated_and_bound_to_conversation_owner(planner):
    from tests.test_security import client_for
    _,c,_=planner
    first=call(c,'Bedenk iets leuks voor zondag.').json()
    with client_for(planner[0]) as anonymous:assert anonymous.get('/api/v1/natural/planning/'+first['conversation_id']).status_code==401
    assert c.get('/api/v1/natural/planning/00000000-0000-0000-0000-000000000000').status_code==404


def test_model_change_and_new_manager_share_durable_draft(planner):
    from server.natural.planning import ActivityPlanningManager
    app,c,_=planner
    first=call(c,'Ik wil zaterdag met Sam naar een museum.').json()
    second=call(c,'Doe toch maar zondag.',first['conversation_id'],provider='gemini').json()
    principal=app.state.security.store.authenticate(c.cookies.get('jarvis_access'))
    state=ActivityPlanningManager(app.state.natural).get(principal,second['conversation_id'])['state']
    assert state['facts']['participants']['value']==['Sam'] and state['facts']['activity']['value']=='museum'
    assert datetime.fromisoformat(state['facts']['date']['value']).weekday()==6


def test_source_forgetting_clears_derived_plan_and_retention_removes_old_draft(planner):
    app,c,_=planner
    first=call(c,'Ik wil zondag met Sam naar een museum.').json()
    with app.state.natural.store.database.connection() as db:
        user=db.execute('SELECT id FROM auth_users').fetchone()[0]
        db.execute('INSERT INTO natural_forgotten VALUES (?,?,?,?)',(user,first['request_id'],'a'*64,app.state.natural.store.clock()));db.commit()
    assert document(c,first['conversation_id'])['state']['facts']=={}
    with app.state.natural.store.database.connection() as db:
        db.execute("UPDATE natural_pending SET updated=0 WHERE kind='activity_plan'");db.commit()
    app.state.natural.retention.sweep()
    assert document(c,first['conversation_id']) is None


def test_known_contact_draft_only_reuses_verified_gmail_path_without_send(planner):
    import asyncio
    app,c,_=planner;engine=app.state.automation;captured=[]
    assert c.post('/api/v1/natural/contacts',json={'name':'Sam','email':'sam@example.invalid'}).status_code==200
    async def draft(payload):
        captured.append(payload)
        return {'draft_id':'synthetic1','message_hash':'b'*64,'preview':'Aan: sam@example.invalid\nOnderwerp: Samen een uitje plannen\n\nKun je zondag?'}
    engine.integrations.draft=draft
    first=call(c,'Ik wil zondagmiddag met Sam naar een museum.').json()
    async def finish():
        for _ in range(300):
            if any(row['tool']=='EmailDraft' for row in engine.store.items()):await engine.tick();return
            await asyncio.sleep(.01)
    task=c.portal.start_task_soon(finish)
    answer=call(c,'Vraag Sam maar of hij zondag kan.',first['conversation_id']).json();task.result(timeout=10)
    assert captured and captured[0]['to']=='sam@example.invalid' and 'museum' in captured[0]['text']
    assert all(row['tool']=='EmailDraft' for row in engine.store.items()),answer
    repeated=call(c,'Vraag Sam maar of hij zondag kan.',first['conversation_id']).json()
    assert 'geen dubbel bericht' in repeated['message'] and len(captured)==1


def test_settings_control_selection_environment_and_disabled_route(planner):
    _,c,_=planner
    settings=c.get('/api/v1/natural/settings').json()
    changed=c.patch('/api/v1/natural/settings/planning',json={'revision':settings['revision'],'changes':{'environment':'inside','initiative':'choose','suggest_restaurants':False}}).json()
    first=call(c,'Bedenk iets leuks voor zondag.').json()
    state=document(c,first['conversation_id'])['state']
    assert state['facts']['activity']['value']=='museum' and all(item['environment']=='inside' for item in state['alternatives'])
    assert c.patch('/api/v1/natural/settings/planning',json={'revision':changed['revision'],'changes':{'enabled':False}}).status_code==200
    second=call(c,'Bedenk iets leuks voor zondag.').json()
    assert document(c,second['conversation_id']) is None


def test_disliking_restaurant_and_short_cancel_keep_intent_local(planner):
    app,c,router=planner
    for provider in router.providers.values():
        reply=json.loads(provider.chunks[0]);reply['proposals']={'meal':'restaurant'};provider.chunks=(json.dumps(reply),)
    first=call(c,'Ik wil zondag naar een museum en daarna ergens eten.').json()
    call(c,'Dat restaurant lijkt me niks.',first['conversation_id'])
    state=document(c,first['conversation_id'])['state']
    assert 'restaurant' in state['excluded'] and 'meal' not in state['facts']
    stopped=call(c,'Laat maar.',first['conversation_id']).json()
    assert document(c,stopped['conversation_id'])['state']['status']=='cancelled'
    assert not app.state.automation.store.items()
