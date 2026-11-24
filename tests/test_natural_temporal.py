from datetime import datetime, timedelta, UTC
from zoneinfo import ZoneInfo

import pytest

from server.natural.temporal import resolve, local_time, AmbiguousTime

ZONE=ZoneInfo("Europe/Amsterdam")
NOW=datetime(2026,11,24,11,0,tzinfo=ZONE)


@pytest.mark.parametrize("phrase,day",[("morgen","2026-11-25"),("overmorgen","2026-11-26"),("volgende vrijdag","2026-12-04"),("aanstaande vrijdag","2026-11-27"),("komende maandag","2026-11-30")])
def test_dutch_dates(phrase,day):
    hint=resolve(phrase,now=NOW)
    assert hint.date==day and hint.window_end>hint.start


@pytest.mark.parametrize("phrase,clock",[("half vier","15:30"),("kwart over drie","15:15"),("kwart voor vijf","16:45"),("tien voor half acht 's avonds","19:20"),("om 03:00","03:00"),("om drie","15:00")])
def test_dutch_clocks_use_explicit_daypart_or_unique_configured_hours(phrase,clock):
    hint=resolve("morgen "+phrase,now=NOW)
    assert hint.clock==clock and hint.start.date().isoformat()=="2026-11-25"


@pytest.mark.parametrize("phrase,minutes",[("over anderhalf uur",90),("over twintig minuten",20),("over een half uur",30)])
def test_relative_times(phrase,minutes):
    assert resolve(phrase,now=NOW).start==NOW+timedelta(minutes=minutes)


@pytest.mark.parametrize("phrase",["volgende week","eind van de middag","morgenochtend","vanavond","na mijn werk","een uur later","een halfuur eerder","dezelfde tijd als vorige keer"])
def test_uncertain_times_require_missing_information(phrase):
    assert resolve(phrase,now=NOW).clarification


def test_relative_corrections_keep_anchor_and_duration():
    assert resolve("een uur later",now=NOW,anchor=NOW).start==NOW+timedelta(hours=1)
    assert resolve("een halfuur eerder",now=NOW,anchor=NOW).start==NOW-timedelta(minutes=30)
    hint=resolve("Volgende week vrijdag om half vier een afspraak van twee uur met Noah",now=NOW)
    assert hint.start==datetime(2026,12,4,15,30,tzinfo=ZONE) and hint.duration_minutes==120
    assert resolve("dezelfde tijd als vorige keer",now=NOW,anchor=NOW).clock=="11:00"


def test_dst_gaps_folds_and_actual_elapsed_relative_time():
    with pytest.raises(AmbiguousTime,match="bestaat niet"):
        local_time(datetime(2026,3,29).date(),2,30,ZONE)
    with pytest.raises(AmbiguousTime,match="twee keer"):
        local_time(datetime(2026,10,25).date(),2,30,ZONE)
    before=datetime(2026,3,29,1,30,tzinfo=ZONE)
    after=resolve("over anderhalf uur",now=before).start
    assert after.hour==4 and after.astimezone(UTC)-before.astimezone(UTC)==timedelta(minutes=90)
    day=resolve("morgen",now=datetime(2026,3,28,12,tzinfo=ZONE))
    assert (day.window_end.astimezone(UTC)-day.start.astimezone(UTC)).total_seconds()==23*3600


def test_non_unique_work_time_does_not_guess():
    assert resolve("morgen om zeven",now=NOW,work_start=0,work_end=24).clarification
    assert resolve("morgen om zeven in de ochtend",now=NOW).clock=="07:00"


def test_reminder_uses_shared_temporal_validation():
    from server.automation.chat import AutomationChat
    result=AutomationChat.temporal("ReminderCreate",{"text":"Synthetisch"},"Herinner me over anderhalf uur aan tanken")
    assert result["timezone"]=="Europe/Amsterdam" and datetime.fromisoformat(result["at"]).tzinfo
    with pytest.raises(AmbiguousTime):
        AutomationChat.temporal("ReminderCreate",{},"Herinner me morgenochtend aan tanken")
