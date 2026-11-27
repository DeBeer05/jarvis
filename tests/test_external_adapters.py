"""Official HTTP shapes with mocked services and keys. No real devices/accounts."""
import json

import httpx
import pytest

from server.automation.external import ExternalAdapters,HomePolicy
from server.automation.models import validate
from tests.test_automation import automation as automation,submit
from tests.test_windows_host import approve
from tests.test_chat_automation import tools_chat as tools_chat,call
from server.natural.public_sources import PublicSources


class Vault:
    def __init__(self,values):self.values=values
    def get(self,key):return self.values.get(key)


def configure(e,handler):
    policy=HomePolicy(enabled=True,endpoint='https://home.example.invalid',entities=['light.desk','climate.study','sensor.temperature'],aliases={'bureaulamp':'light.desk'})
    e.store.set_preference('home_assistant',policy.model_dump(mode='json'))
    e.integrations.vault=Vault({'external:home_assistant':json.dumps({'endpoint':policy.endpoint,'token':'synthetic-home-token'}),'external:openrouteservice':'synthetic-route-token'})
    e.external=ExternalAdapters(e,transport=httpx.MockTransport(handler))
    return policy


def test_home_control_needs_approval_and_verified_matching_state(automation):
    _,c,e=automation;calls=[];state=['off']
    def handler(request):
        calls.append(request.method)
        assert request.headers['authorization']=='Bearer synthetic-home-token'
        if request.method=='POST':
            assert request.url.path=='/api/services/light/turn_on'
            assert json.loads(request.content)=={'entity_id':'light.desk'}
            state[0]='on';return httpx.Response(200,json=[])
        return httpx.Response(200,json={'entity_id':'light.desk','state':state[0],'attributes':{'friendly_name':'Bureaulamp'}})
    configure(e,handler)
    job=submit(c,'HomeControl',{'entity_id':'light.desk','action':'on'}).json()
    assert job['status']=='approval';c.portal.call(e.tick);assert not calls
    approve(c,job);c.portal.call(e.tick);c.portal.call(e.tick)
    assert calls==['POST','GET']
    result=e.store.public(e.store.get(job['id']))
    assert result['status']=='completed' and result['result']['verified'] and result['result']['state']=='on'


def test_home_changed_policy_or_wrong_entity_cannot_send_old_proposal(automation):
    _,c,e=automation;calls=[]
    configure(e,lambda request:calls.append(request) or httpx.Response(500))
    job=submit(c,'HomeControl',{'entity_id':'light.desk','action':'off'}).json();approve(c,job)
    e.store.set_preference('home_assistant',{'enabled':True,'endpoint':'https://changed.example.invalid','entities':['light.desk']})
    c.portal.call(e.tick);assert not calls and e.store.get(job['id'])['status']=='uncertain'
    with pytest.raises(ValueError):c.portal.call(e.external.home_state,'light.unlisted')
    assert not calls
    assert not e.external.capabilities()['home_assistant']['configured']


def test_home_accepted_but_unverified_state_is_uncertain_without_write_retry(automation):
    _,c,e=automation;writes=[]
    def handler(request):
        if request.method=='POST':writes.append(1);return httpx.Response(200,json=[])
        return httpx.Response(200,json={'entity_id':'light.desk','state':'off','attributes':{}})
    configure(e,handler)
    job=submit(c,'HomeControl',{'entity_id':'light.desk','action':'on'}).json();approve(c,job)
    c.portal.call(e.tick);e.store.recover();c.portal.call(e.tick)
    assert writes==[1] and e.store.get(job['id'])['status']=='uncertain'


def test_routes_are_cached_and_do_not_claim_live_traffic_or_prices(automation):
    _,c,e=automation;calls=[]
    def handler(request):
        calls.append(1)
        assert request.url.host=='api.openrouteservice.org' and request.url.path.endswith('/driving-car/json')
        return httpx.Response(200,json={'routes':[{'summary':{'distance':12500,'duration':900}}]})
    configure(e,handler)
    payload=validate('RouteRead',{'coordinates':[[4.8,52.4],[5.1,52.1]]})
    first=c.portal.call(e.external.route,payload);assert first==c.portal.call(e.external.route,payload)
    assert len(calls)==1 and first['distance_km']==12.5 and first['live_traffic'] is False
    cost=c.post('/api/v1/automation/trip-cost',json={'distance_km':'100','liters_per_100km':'6.5','price_per_liter':'2.00'}).json()
    assert cost['estimated_fuel_cost_eur']=='13.00' and not cost['live_prices']
    assert not e.external.capabilities()['creality_hi']['supported']


def test_external_configuration_rejects_http_credentials_and_unsafe_services():
    for endpoint in ('http://host.example.invalid','https://user:pass@host.example.invalid','https://host.example.invalid/?key=secret'):
        with pytest.raises(ValueError):HomePolicy(endpoint=endpoint)
    with pytest.raises(ValueError):HomePolicy(entities=['shell_command.run'])
    with pytest.raises(ValueError):validate('HomeControl',{'entity_id':'climate.study','action':'temperature','temperature':90})
    with pytest.raises(ValueError):validate('RouteRead',{'coordinates':[[400,52],[5,52]]})


def test_natural_home_aliases_use_same_registry_without_model_or_fake_success(tools_chat):
    app,c,router=tools_chat;calls=[]
    configure(app.state.automation,lambda request:calls.append(request) or httpx.Response(500))
    result=call(c,'Kunt u de bureaulamp aanzetten?').json()
    assert result['status']=='completed' and 'voorstel' in result['message']
    jobs=app.state.automation.store.items()
    assert len(jobs)==1 and jobs[0]['tool']=='HomeControl' and jobs[0]['status']=='approval'
    assert not calls and not router.planning_calls and not any(provider.calls for provider in router.providers.values())


def test_city_routes_reuse_public_geocoder_and_missing_key_sends_no_places(automation):
    app,c,e=automation;lookups=[]
    configure(e,lambda request:httpx.Response(200,json={'routes':[{'summary':{'distance':10000,'duration':1000}}]}))
    def geocode(request):
        name=request.url.params['name'];lookups.append(name)
        return httpx.Response(200,json={'results':[{'name':name,'latitude':52.1,'longitude':4.5 if name=='Delft' else 4.6}]})
    app.state.natural.briefings.sources=PublicSources(transport=httpx.MockTransport(geocode))
    response=c.post('/api/v1/automation/route-cities',json={'origin':'Delft','destination':'Leiden'})
    assert response.status_code==200,response.text
    assert response.json()['origin']=='Delft' and not response.json()['live_traffic']
    assert len(lookups)==2
    e.integrations.vault.values.pop('external:openrouteservice')
    assert c.post('/api/v1/automation/route-cities',json={'origin':'Andere plaats','destination':'Leiden'}).status_code==409
    assert len(lookups)==2
