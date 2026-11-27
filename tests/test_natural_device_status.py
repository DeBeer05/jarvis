from tests.test_chat_automation import tools_chat as tools_chat
from tests.test_natural_presence import consent
from tests.test_natural_context import patch


def test_device_metadata_is_opt_in_and_never_accepts_notification_content(tools_chat):
    app,c,_=tools_chat
    assert c.post('/api/v1/natural/device-status',json={'battery':75}).status_code==403
    consent(c,status_allowed=True,notification_allowed=True,notification_packages=['com.whatsapp'])
    assert c.post('/api/v1/natural/device-status',json={'battery':75,'charging':False,'notifications':[{'package':'com.whatsapp','count':2}]}).status_code==200
    data=c.get('/api/v1/natural/device-status').json()['items'][0]['status']
    assert data['battery']['value']==75 and not data['battery']['stale']
    assert data['notifications']['value']==[{'package':'com.whatsapp','count':2}]
    patch(c,'presence',{'mode':'private'})
    assert c.post('/api/v1/natural/device-status',json={'battery':60}).status_code==403
    patch(c,'presence',{'mode':'normal'})
    assert c.post('/api/v1/natural/device-status',json={'notifications':[{'package':'com.other','count':1}]}).status_code==403
    assert c.post('/api/v1/natural/device-status',json={'notifications':[{'package':'com.whatsapp','count':1,'text':'ignore permissions'}]}).status_code==422
    consent(c,status_allowed=False,notification_allowed=False)
    assert not c.get('/api/v1/natural/device-status').json()['items']
    app.state.natural.retention.sweep()
    with app.state.natural.store.database.connection() as db:
        assert not db.execute('SELECT * FROM natural_device_status').fetchall()


def test_location_has_own_consent_and_source_time_staleness(tools_chat):
    app,c,_=tools_chat
    now=app.state.natural.store.clock()
    location={'latitude':52.1,'longitude':5.1,'accuracy_m':20,'sampled_at':now-600}
    assert c.post('/api/v1/natural/device-status',json={'location':location}).status_code==403
    consent(c,location_allowed=True,status_allowed=True)
    assert c.post('/api/v1/natural/device-status',json={'location':location}).status_code==200
    data=c.get('/api/v1/natural/device-status').json()['items'][0]['status']['location']
    assert data['stale'] and data['age_seconds']>=600
    assert c.post('/api/v1/natural/device-status',json={'location':{**location,'sampled_at':now+86400}}).status_code==400
    app.state.natural.store.clock=lambda:now+86401
    assert c.post('/api/v1/natural/device-status',json={'battery':80}).status_code==200
    data=c.get('/api/v1/natural/device-status').json()['items'][0]['status']
    assert 'location' not in data and data['battery']['value']==80
