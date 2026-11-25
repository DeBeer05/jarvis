"""Latest content must be retrieved before summarizing, never ask users for IDs."""
import base64,json
import pytest
from tests.test_chat_automation import tools_chat as tools_chat,call
from server.natural.mail_digest import latest_count,brief_digest


@pytest.mark.parametrize('message',['Toon mijn laatste mails van Noah','Vat mijn laatste tien mails over het project samen','Toon de onderwerpen van mijn laatste mails','Toon mijn laatste mails uit spam'])
def test_specific_filters_are_not_replaced_with_unfiltered_inbox(message):
    assert latest_count(message) is None


def test_screenshot_last_ten_mail_fetches_bodies_and_summarizes_without_id_question(tools_chat):
    app,c,router=tools_chat;reads=[]
    async def search(query):assert query=='in:inbox';return {'messages':[{'id':f'mail{i}'} for i in range(12)]}
    async def read(identifier,body=False):
        reads.append((identifier,body))
        return {'id':identifier,'payload':{'headers':[{'name':'Subject','value':'Synthetisch onderwerp '+identifier}],'mimeType':'text/plain','body':{'data':base64.urlsafe_b64encode(b'Een uitnodiging. Reactie uiterlijk vrijdag.').decode()}}}
    app.state.automation.integrations.mail_search=search;app.state.automation.integrations.mail_read=read
    router.plans=[{'groups':[{'indices':list(range(1,11)),'purpose':'met uitnodigingen'}],'notes':['Reactie uiterlijk vrijdag.']}]
    response=call(c,'Nee, ik wil gewoon weten wat in mijn laatste 10 mails staat.').json()
    assert response['status']=='completed' and 'uitnodigingen' in response['message'] and 'vrijdag' in response['message']
    assert len(reads)==10 and all(body for _,body in reads)
    prompt=json.loads(router.planning_calls[0][0][1]['content'])
    assert prompt['actual_read_count']==10 and len(prompt['messages'])==10
    assert 'Reactie uiterlijk vrijdag' in prompt['messages'][0]['content']
    assert not app.state.automation.store.items()
    follow=call(c,'Lees de 10e mail',response['conversation_id']).json()
    assert 'vrijdag' in follow['message'] and reads[-1]==('mail9',True)


def test_plain_latest_mail_also_reads_content_not_only_subjects(tools_chat):
    app,c,router=tools_chat
    async def search(_):return {'messages':[{'id':'first'}]}
    async def read(identifier,body=False):
        assert body
        return {'id':identifier,'snippet':'Synthetische korte inhoud.','payload':{'headers':[]}}
    app.state.automation.integrations.mail_search=search;app.state.automation.integrations.mail_read=read
    router.plans=[{'groups':[{'indices':[1],'purpose':'met een korte mededeling'}]}]
    result=call(c,'Wat zijn mijn laatste mails?').json()
    assert result['status']=='completed'
    assert 'mededeling' in result['message']
    assert 'bericht-IDs' not in result['message']


@pytest.mark.parametrize('message',['Vat mijn laatste 21 mails samen','Wat staat in mijn laatste 999 emails?'])
def test_limit_never_reads_or_creates_jobs(tools_chat,message):
    app,c,router=tools_chat
    async def forbidden(*args):pytest.fail('No Google call allowed')
    app.state.automation.integrations.mail_search=forbidden
    result=call(c,message).json()
    assert 'maximaal twintig' in result['message'] and not router.planning_calls
    assert not app.state.automation.store.items()


def test_disabled_read_prevents_even_search(tools_chat):
    app,c,router=tools_chat
    app.state.automation.store.set_preference('disabled_tools',['EmailRead'])
    async def forbidden(*args):pytest.fail('Disabled read must prevent search')
    app.state.automation.integrations.mail_search=forbidden
    result=call(c,'Vat mijn laatste tien mails samen').json()
    assert 'veilige' in result['message'] and not router.planning_calls


def test_sensitive_body_uses_local_ai_without_cloud_call(tools_chat):
    app,c,router=tools_chat
    async def search(_):return {'messages':[{'id':'private'}]}
    async def read(*args):return {'id':'private','snippet':'Medisch bericht: reactie uiterlijk vrijdag.','payload':{'headers':[]}}
    app.state.automation.integrations.mail_search=search;app.state.automation.integrations.mail_read=read
    router.plans=[{'groups':[{'indices':[1],'purpose':'over een medisch bericht'}],'notes':['reactie uiterlijk vrijdag.']}]
    result=call(c,'Vat mijn laatste mail samen',provider='groq').json()
    assert result['status']=='completed' and 'vrijdag' in result['message']
    assert 'Korte inhoud per bericht' not in result['message']
    assert len(router.planning_calls)==1 and router.planning_calls[0][1]=='ollama'
    assert not app.state.automation.store.items()


def test_sensitive_local_failure_explains_reason_without_cloud_retry(tools_chat):
    from server.ai.providers import ProviderError
    app,c,router=tools_chat;providers=[]
    async def search(_):return {'messages':[{'id':'private'}]}
    async def read(*args):return {'id':'private','snippet':'Medisch bericht: reageer vrijdag.','payload':{'headers':[]}}
    async def unavailable(messages,mode=None):providers.append(mode);raise ProviderError('unavailable')
    app.state.automation.integrations.mail_search=search;app.state.automation.integrations.mail_read=read;router.bounded_result=unavailable
    result=call(c,'Vat mijn laatste mail samen',provider='groq').json()
    assert providers==['ollama'] and 'privacyredenen lokaal' in result['message']
    assert 'niet bereikbaar' in result['message'] and 'vrijdag' in result['message']


def test_unicode_content_does_not_artificially_exceed_context_budget(tools_chat):
    app,c,router=tools_chat
    async def search(_):return {'messages':[{'id':str(i)} for i in range(10)]}
    async def read(identifier,*args):return {'id':identifier,'snippet':'é🙂 '*1000,'payload':{'headers':[]}}
    app.state.automation.integrations.mail_search=search;app.state.automation.integrations.mail_read=read
    router.plans=[{'groups':[{'indices':list(range(1,11)),'purpose':'met nieuwsbrieven'}]}]
    result=call(c,'Vat mijn laatste tien mails samen',provider='groq').json()
    assert 'tien mails' in result['message'] and 'nieuwsbrieven' in result['message'] and len(router.planning_calls)==1
    prompt=router.planning_calls[0][0][1]['content']
    assert '🙂' in prompt and len(prompt)+1400<=router.settings.max_context_chars


def test_brief_digest_counts_groups_and_renders_one_sentence():
    sources=[{'from':'PayPal <receipts@example.invalid>','content':'Betaalbewijs.'},
             {'from':'PayPal <receipts@example.invalid>','content':'Betaalbewijs.'},
             {'from':'Google Cloud <cloud@example.invalid>','content':'Voorwaarden gewijzigd.'}]
    raw=json.dumps({'groups':[{'indices':[1,2],'purpose':'met betaalbewijzen'},{'indices':[3],'purpose':'over gewijzigde voorwaarden'}]})
    assert brief_digest(raw,sources)=='Van PayPal heeft u twee mails met betaalbewijzen en van Google Cloud een mail over gewijzigde voorwaarden, meneer.'
    assert brief_digest('```json\n'+raw+'\n```',sources)==brief_digest(raw,sources)
    assert 'Google Cloud' in brief_digest(json.dumps({'groups':[{'indices':[1],'purpose':''}]}),[{'from':'Google Cloud','content':''}])
    for groups in ([{'indices':[1,1,3],'purpose':''}],[{'indices':[1,3],'purpose':''},{'indices':[2],'purpose':''}],[{'indices':[1,2],'purpose':''}]):
        with pytest.raises(ValueError):brief_digest(json.dumps({'groups':groups}),sources)
    value=json.loads(raw);value['groups'][0]['count']=999;value['tool']='EmailSend'
    assert 'Van PayPal heeft u twee mails' in brief_digest(json.dumps(value),sources)
    value['notes']=['Verzonden op vrijdag.']
    with pytest.raises(ValueError):brief_digest(json.dumps(value),sources)
