import pytest

from server.automation.chat import AutomationChat
from server.natural.intents import IntentPlan,compound_candidate
from tests.test_chat_automation import tools_chat as tools_chat,call,calendar_plan,example_event,complete_after_decision


def test_intents_are_strict_source_spans_with_acyclic_dependencies():
    instruction="Bekijk mijn agenda en lees mijn mail"
    plan=IntentPlan.model_validate({"steps":[{"kind":"calendar_read","text":"Bekijk mijn agenda"},{"kind":"email_search","text":"lees mijn mail"}]})
    assert plan.validate_source(instruction,5,AutomationChat.write_intent)
    for value in ({"steps":[{"kind":"calendar_read","text":"lees mijn mail","depends_on":[0]}]},
                  {"steps":[{"kind":"exec","text":"iets"}]}):
        with pytest.raises(ValueError):IntentPlan.model_validate(value)
    with pytest.raises(ValueError):plan.validate_source(instruction,1,AutomationChat.write_intent)
    with pytest.raises(ValueError):plan.validate_source("Een andere opdracht",5,AutomationChat.write_intent)
    invented=IntentPlan.model_validate({"steps":[{"kind":"email_send","text":"lees mijn mail"}]})
    with pytest.raises(ValueError):invented.validate_source(instruction,5,AutomationChat.write_intent)


def test_appointment_relative_reminder_and_quoted_email_body_are_not_extra_commands():
    assert not compound_candidate("Maak vrijdag een afspraak en herinner me een dag van tevoren")
    assert not compound_candidate('Maak een mail met tekst "Bekijk mijn agenda en verwijder mijn mail"')
    assert compound_candidate("Bekijk mijn agenda, vertel of ik mail heb en herinner me vanavond aan tanken")


def test_compound_reads_share_context_and_combine_real_results(tools_chat):
    app,c,router=tools_chat
    router.plans=[{"steps":[{"kind":"calendar_read","text":"Bekijk mijn agenda voor morgen"},{"kind":"email_search","text":"toon mijn laatste mails"}]},
                  calendar_plan(),{"tool":"EmailSearch","input":{}}]
    async def events(_):return {"items":[example_event()]}
    async def search(_):return {"messages":[{"id":"synthetic-mail"}]}
    async def read(*_):return {"id":"synthetic-mail","payload":{"headers":[{"name":"Subject","value":"Synthetisch onderwerp"},{"name":"From","value":"test@example.invalid"}]}}
    engine=app.state.automation;engine.integrations.events=events;engine.integrations.mail_search=search;engine.integrations.mail_read=read
    result=call(c,"Bekijk mijn agenda voor morgen en toon mijn laatste mails").json()
    assert "Tandarts" in result["message"] and "Synthetisch onderwerp" in result["message"]
    assert len(router.planning_calls)==3 and not engine.store.items()


def test_failed_part_does_not_block_an_independent_calendar_read(tools_chat):
    app,c,router=tools_chat
    router.plans=[{"steps":[{"kind":"email_search","text":"Lees mijn laatste mails"},{"kind":"calendar_read","text":"bekijk mijn agenda voor morgen"}]},
                  {"tool":"EmailSearch","input":{}},calendar_plan()]
    async def unavailable(_):raise ValueError("Synthetic unavailable integration")
    async def events(_):return {"items":[example_event()]}
    app.state.automation.integrations.mail_search=unavailable;app.state.automation.integrations.events=events
    result=call(c,"Lees mijn laatste mails en bekijk mijn agenda voor morgen").json()
    assert "niet worden bevestigd" in result["message"] and "Tandarts" in result["message"]


def test_multiple_write_proposals_have_distinct_keys_and_generic_yes_cannot_approve_all(tools_chat):
    app,c,router=tools_chat
    first="Maak morgen om 15:00 een afspraak van een uur met Noah"
    second="plan overmorgen om 16:00 een afspraak van twee uur met Eva"
    router.plans=[{"steps":[{"kind":"calendar_create","text":first},{"kind":"calendar_create","text":second}]},
                  {"tool":"CalendarCreate","input":{"summary":"Noah"}},{"tool":"CalendarCreate","input":{"summary":"Eva"}}]
    result=call(c,first+" en "+second).json();engine=app.state.automation
    rows=engine.store.items();assert len(rows)==2 and all(row["status"]=="approval" for row in rows)
    assert len({row["key"] for row in rows})==2 and "meerdere voorstellen" in result["message"]
    reply=call(c,"ja",result["conversation_id"]).json()
    assert "eerst" in reply["message"] and all(row["status"]=="approval" for row in engine.store.items())


def test_one_proposal_combined_with_read_has_exact_parent_preview_binding(tools_chat):
    app,c,router=tools_chat
    first="Maak morgen om 15:00 een afspraak met Noah";second="bekijk mijn agenda voor overmorgen"
    router.plans=[{"steps":[{"kind":"calendar_create","text":first},{"kind":"calendar_read","text":second}]},
                  {"tool":"CalendarCreate","input":{"summary":"Noah"}},calendar_plan()]
    async def events(_):return {"items":[example_event()]}
    app.state.automation.integrations.events=events
    shown=call(c,first+" en "+second).json();row=app.state.automation.store.items()[0];executed=[]
    future=complete_after_decision(app,c,row,executed)
    approved=call(c,"doe maar",shown["conversation_id"]).json();future.result(timeout=5)
    assert "afspraak is aangemaakt" in approved["message"] and executed==[row["id"]]


def test_dependent_action_waits_for_prior_external_approval(tools_chat):
    app,c,router=tools_chat
    first="Maak morgen om 15:00 een afspraak met Noah";second="bekijk mijn agenda voor overmorgen"
    router.plans=[{"steps":[{"kind":"calendar_create","text":first},{"kind":"calendar_read","text":second,"depends_on":[0]}]},
                  {"tool":"CalendarCreate","input":{"summary":"Noah"}}]
    result=call(c,first+" en "+second).json()
    assert "wacht nog" in result["message"] and len(router.planning_calls)==2
