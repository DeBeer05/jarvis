from tests.test_automation import automation as automation
from tests.test_natural_context import patch
from datetime import datetime, timedelta, UTC


def test_reschedule_uses_saved_hours_days_buffers_and_optional_suggestions(automation):
    app,c,engine=automation
    event={"id":"actual","etag":"v1","summary":"Test","start":{"dateTime":"2030-01-07T10:00:00+01:00"},"end":{"dateTime":"2030-01-07T11:00:00+01:00"}}
    nearby={"id":"nearby","summary":"Buur","start":{"dateTime":"2030-01-07T11:05:00+01:00"},"end":{"dateTime":"2030-01-07T11:30:00+01:00"}}
    async def fetch(*args,**kwargs):return event
    async def events(_):return {"items":[event,nearby]}
    engine.integrations.api=fetch;engine.integrations.events=events
    payload={"event_id":"actual","etag":"v1","summary":"Test","start":"2030-01-07T10:00:00+01:00","end":"2030-01-07T11:00:00+01:00"}
    patch(c,"calendar",{"buffer_minutes":10,"workdays":[0],"work_start":"12:00","work_end":"13:00"})
    result=c.post("/api/v1/automation/reschedule",json=payload)
    assert result.status_code==200
    data=result.json();assert data["buffer_minutes"]==10 and len(data["neighbours"])==1
    assert data["alternatives"]==[{"start":"2030-01-07T12:00:00+01:00","end":"2030-01-07T13:00:00+01:00"}]
    patch(c,"calendar",{"alternatives":False,"neighboring":False})
    data=c.post("/api/v1/automation/reschedule",json=payload).json()
    assert not data["alternatives"] and not data["neighbours"]
    assert data["requires_approval"] is True


def test_alternatives_and_buffers_stay_inside_verified_range(automation):
    app,c,engine=automation
    event={"id":"actual","etag":"v1","summary":"Test"}
    checked={}
    async def fetch(*args,**kwargs):return event
    async def events(query):
        checked.update(query)
        return {"items":[]}
    engine.integrations.api=fetch;engine.integrations.events=events
    patch(c,"calendar",{"buffer_minutes":240,"workdays":[0,1,2,3,4,5,6],"work_start":"00:00","work_end":"23:59"})
    # A 21-hour candidate at the end of the search window would previously be
    # advertised as free even though its four-hour buffer was never fetched.
    payload={"event_id":"actual","etag":"v1","summary":"Test","start":"2030-01-07T00:00:00+01:00","end":"2030-01-07T21:00:00+01:00"}
    response=c.post("/api/v1/automation/reschedule",json=payload)
    assert response.status_code==200
    assert response.json()["alternatives"]==[]
    assert datetime.fromisoformat(checked["end"])==datetime.fromisoformat(payload["end"]).astimezone(UTC)+timedelta(days=1)
