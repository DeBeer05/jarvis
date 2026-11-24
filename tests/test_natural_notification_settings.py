from datetime import datetime,UTC

from tests.test_automation import automation as automation
from tests.test_natural_context import patch


def test_global_notification_preferences_apply_to_jobs_and_preserve_explicit_reminders(automation):
    app,c,engine=automation
    principal=app.state.security.store.authenticate(c.cookies.get("jarvis_access"))
    patch(c,"notifications",{"enabled":False})
    assert engine.notifications.send("important","Synthetic","disabled",device=principal.device_id)=={"suppressed":True}
    patch(c,"notifications",{"enabled":True,"proactivity":"off","quiet_start":0,"quiet_end":0})
    assert engine.notifications.send("important","Synthetic","proactive",device=principal.device_id,proactive=True)=={"suppressed":True}
    assert "notification_id" in engine.notifications.send("important","Explicit reminder","explicit",device=principal.device_id)
    patch(c,"notifications",{"proactivity":"normal","suggestions_per_hour":0})
    assert engine.notifications.send("important","Synthetic","zero",device=principal.device_id,proactive=True)=={"suppressed":True}


def test_user_quiet_hours_and_timezone_are_used_for_delivery(automation):
    app,c,engine=automation
    principal=app.state.security.store.authenticate(c.cookies.get("jarvis_access"))
    stamp=datetime(2030,1,1,22,0,tzinfo=UTC).timestamp();engine.store.clock=lambda:stamp
    patch(c,"general",{"timezone":"Europe/Amsterdam"})
    patch(c,"notifications",{"quiet_start":22,"quiet_end":7})
    result=engine.notifications.send("important","Synthetic","quiet-local",device=principal.device_id)
    with engine.store.db() as db:row=db.execute("SELECT at FROM automation_notifications WHERE id=?",(result["notification_id"],)).fetchone()
    assert row["at"]==datetime(2030,1,2,6,0,tzinfo=UTC).timestamp()
