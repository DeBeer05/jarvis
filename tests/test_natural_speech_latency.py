"""Ready speech chunks arrive early while written answers and approvals stay complete."""
import asyncio
from types import SimpleNamespace

from server.natural.models import UserSettings
from server.natural.responses import IntelligentResponseManager


def run_events(chunks,*,tool=False,waiting=None):
    run=SimpleNamespace(natural_context={'settings':UserSettings().model_dump()},message='Een vraag',
        speech_message='',conversational_reply=False,response_data=None,wait_state=waiting)
    async def source():
        for chunk in chunks:yield {'type':'delta','text':chunk}
    async def scenario():return [event async for event in IntelligentResponseManager(None).stream(run,source(),tool)]
    return asyncio.run(scenario())


def test_first_long_clause_can_be_spoken_before_sentence_completion():
    first='Na een lange werkdag helpt een rustige wandeling om wat afstand te nemen, '
    events=run_events([first,'terwijl u ondertussen nadenkt over wat u morgen anders wilt aanpakken.'])
    speech_index=next(i for i,e in enumerate(events) if e['type']=='speech')
    second_delta=next(i for i,e in enumerate(events) if e['type']=='delta' and e['text'].startswith('terwijl'))
    assert speech_index<second_delta
    assert ''.join(e['text'] for e in events if e['type']=='delta')==first+'terwijl u ondertussen nadenkt over wat u morgen anders wilt aanpakken.'
    assert 'morgen anders' in ''.join(e['text'] for e in events if e['type']=='speech')


def test_short_clause_and_decimal_do_not_split_unnaturally():
    events=run_events(['Goedemorgen, meneer, ','het bedrag is 3,14 euro.'])
    speech_index=next(i for i,e in enumerate(events) if e['type']=='speech')
    assert speech_index>1
    assert len([e for e in events if e['type']=='speech'])==1


def test_tool_approval_keeps_whole_preview_before_any_speech():
    text='Voorstel: '+('Dit is noodzakelijke voorstelinhoud. '*50)+'Deadline vrijdag.'
    events=run_events([text[:100],text[100:]],tool=True,waiting='WAITING_FOR_APPROVAL')
    speech=[e['text'] for e in events if e['type']=='speech']
    assert max(i for i,e in enumerate(events) if e['type']=='delta')<min(i for i,e in enumerate(events) if e['type']=='speech')
    assert all(len(part)<=700 for part in speech)
    assert ''.join(e['text'] for e in events if e['type']=='delta')==text
    assert 'Deadline vrijdag' in ' '.join(speech)


def test_cancelling_after_first_clause_closes_source():
    closed=[]
    async def source():
        try:
            yield {'type':'delta','text':'Na een lange werkdag helpt een rustige wandeling om wat afstand te nemen, '}
            await asyncio.Event().wait()
        finally:closed.append(True)
    async def scenario():
        run=SimpleNamespace(natural_context={'settings':UserSettings().model_dump()},speech_message='',conversational_reply=False)
        stream=IntelligentResponseManager(None).stream(run,source())
        assert (await anext(stream))['type']=='delta'
        event=await asyncio.wait_for(anext(stream),.2)
        assert event['type']=='speech'
        await stream.aclose()
    asyncio.run(scenario())
    assert closed
