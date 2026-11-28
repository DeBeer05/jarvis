from tests.test_natural_settings_memory import natural as natural


def test_task_overview_never_speaks_internal_ids_or_tool_names(natural):
    app,c=natural;principal=app.state.security.store.authenticate(c.cookies.get('jarvis_access'))
    store=app.state.automation.store
    job=store.create(principal.device_id,'CalendarUpdate',{},'master-style',store.clock()+3600,approval=True)
    response=c.post('/api/v1/chat',json={'message':'Toon mijn openstaande taken'}).json()
    assert response['status']=='completed'
    text=response['message']
    assert 'Afspraak wijzigen' in text and 'uw toestemming' in text and 'meneer' in text
    assert job['id'] not in text and 'CalendarUpdate' not in text and 'jouw' not in text


def test_capability_answer_respects_autonomy_and_formal_address(natural):
    app,c=natural
    response=c.post('/api/v1/chat',json={'message':'Wat kun je allemaal?'}).json()
    assert response['status']=='completed'
    assert 'met u spreken' in response['message'] and 'jouw' not in response['message']
