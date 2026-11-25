import asyncio
from types import SimpleNamespace

import pytest

from server.natural.models import UserSettings
from server.natural.presentation import outing_overview,ANNOUNCEMENT
from server.natural.responses import IntelligentResponseManager,response_prompt


@pytest.mark.parametrize('text',['Bedenk vijf leuke uitjes voor ons.','Welke uitjes zijn leuk in Haarlem?','Ik wil een lijst met uitjes voor morgen.','Geef een paar bezienswaardigheden voor een dagtrip.'])
def test_outing_ideas_request_a_screen_overview(text):assert outing_overview(text)


@pytest.mark.parametrize('text',[
    'Wat zijn leuke uiten soms te doen in Duitsland met een budget van 50 euro?',
    'Wat kunnen we voor leuks doen met een klein budget?',
    'Welke activiteiten raad je aan voor morgen?',
])
def test_activity_question_does_not_depend_on_perfect_outing_transcription(text):
    assert outing_overview(text)


@pytest.mark.parametrize('text',['Ik vond die uitjes leuk.','Plan een uitje voor morgen.','Voeg een uitje toe aan mijn agenda.','Wat is een uitje?','Schrijf een Python-functie.'])
def test_other_requests_keep_their_normal_presentation(text):
    assert not outing_overview(text)


def test_explicit_read_aloud_override_and_tools_keep_complete_speech():
    async def scenario(message,tool):
        run=SimpleNamespace(message=message,speech_message='',conversational_reply=False,response_data=None,wait_state='WAITING_FOR_APPROVAL' if tool else None,natural_context={'settings':UserSettings().model_dump()})
        async def source():yield {'type':'delta','text':'Voorstel. Belangrijke kosten en toestemming blijven zichtbaar.'}
        return [e async for e in IntelligentResponseManager(None).stream(run,source(),tool)]
    for message,tool in [('Lees de volledige lijst met uitjes voor.',False),('Welke uitjes passen in mijn agenda?',True)]:
        events=asyncio.run(scenario(message,tool))
        speech=''.join(e['text'] for e in events if e['type']=='speech')
        assert 'Belangrijke kosten' in speech and ANNOUNCEMENT not in speech


def test_cancelled_overview_closes_the_upstream_generator():
    closed=[]
    async def scenario():
        run=SimpleNamespace(message='Bedenk uitjes.',speech_message='')
        async def source():
            try:
                yield {'type':'delta','text':'1. Wandeling.'}
                await asyncio.Event().wait()
            finally:closed.append(True)
        stream=IntelligentResponseManager(None).stream(run,source())
        assert (await anext(stream))['type']=='speech'
        assert (await anext(stream))['type']=='delta'
        await stream.aclose()
    asyncio.run(scenario())
    assert closed


def test_announcement_precedes_model_wait_and_full_list_stays_written():
    async def scenario():
        run=SimpleNamespace(message='Bedenk vijf leuke uitjes.',speech_message='',conversational_reply=False,natural_context={'settings':UserSettings().model_dump()})
        gate=asyncio.Event();closed=[]
        async def source():
            try:
                await gate.wait()
                yield {'type':'delta','text':'1. Wandeling — rustig en flexibel.\n'}
                yield {'type':'delta','text':'2. Museum — controleer openingstijden en prijzen.'}
            finally:closed.append(True)
        stream=IntelligentResponseManager(None).stream(run,source())
        first=await asyncio.wait_for(anext(stream),.1)
        assert first=={'type':'speech','text':ANNOUNCEMENT}
        gate.set();events=[event async for event in stream]
        assert all(e['type']=='delta' for e in events)
        assert 'controleer openingstijden' in ''.join(e['text'] for e in events)
        assert run.speech_message==ANNOUNCEMENT and closed
    asyncio.run(scenario())


def test_outing_prompt_asks_for_written_list_and_does_not_invent_current_facts():
    prompt=response_prompt(UserSettings().model_dump(),'Bedenk vijf uitjes voor ons.',True)
    assert 'genummerde lijst' in prompt and 'geen bedragen' in prompt
    assert 'spreek hem niet volledig uit' in prompt
    assert 'Schrijf natuurlijke Nederlandse spreektaal zonder Markdown' not in prompt
