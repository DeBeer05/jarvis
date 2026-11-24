"""Date, clock, duration and reminder slots come from the user's own words."""
from datetime import datetime,timedelta

import pytest

from server.natural.calendar import create_parameters,update_parameters
from server.natural.temporal import AmbiguousTime,resolve


def test_single_sentence_overrides_model_dates_and_keeps_full_duration_and_reminder():
    result=create_parameters({"summary":"Bioscoop met Noah","start":"1999-01-01T00:00:00Z","end":"1999-01-01T01:00:00Z"},
        "Maak volgende week vrijdag om half vier een afspraak van twee uur met Noah en herinner me er een dag van tevoren aan")
    expected=resolve("volgende week vrijdag om half vier").start
    assert datetime.fromisoformat(result["start"])==expected
    assert datetime.fromisoformat(result["end"])==expected+timedelta(hours=2)
    assert result["reminder_minutes"]==1440 and result["summary"]=="Bioscoop met Noah"


def test_explicit_end_and_midnight_and_user_configured_defaults():
    result=create_parameters({"summary":"Test"},"Maak 1 januari 2030 van 23:00 tot 00:00 een afspraak")
    assert result["start"]=="2030-01-01T23:00:00+01:00" and result["end"]=="2030-01-02T00:00:00+01:00"
    configured=create_parameters({"summary":"Test"},"Maak morgen om half vier een afspraak",{"calendar":{"duration_minutes":45,"reminder_minutes":10,"default_calendar":"selected"}})
    assert configured["calendar_id"]=="selected" and configured["reminder_minutes"]==10
    assert datetime.fromisoformat(configured["end"])-datetime.fromisoformat(configured["start"])==timedelta(minutes=45)


def test_followup_corrects_only_day_and_duration_without_losing_known_clock():
    result=create_parameters({"summary":"Noah"},"Maak vrijdag om drie uur een afspraak met Noah\nAanvullende gegevens van dezelfde gebruiker: Twee uur, maar doe toch maar zaterdag")
    assert datetime.fromisoformat(result["start"]).weekday()==5
    assert datetime.fromisoformat(result["start"]).hour==15
    assert datetime.fromisoformat(result["end"]).hour==17


@pytest.mark.parametrize("instruction",["Maak een afspraak", "Maak morgen een afspraak", "Maak een afspraak morgen om zeven", "Maak 31 februari 2030 om 12:00 een afspraak", "Maak 1 januari 2030 van 11 tot 12 een afspraak van twee uur"])
def test_ambiguous_or_missing_slots_cannot_use_model_guesses(instruction):
    with pytest.raises(AmbiguousTime):
        create_parameters({"summary":"Test","start":"2030-01-01T11:00:00+01:00","end":"2030-01-01T12:00:00+01:00"},instruction)


def test_duration_is_requested_when_defaults_are_disabled():
    with pytest.raises(AmbiguousTime,match="Hoe lang"):
        create_parameters({"summary":"Test"},"Maak morgen om 15:00 een afspraak",{"calendar":{"use_defaults":False}})


def test_explicit_dates_and_dst_are_not_guessed():
    assert resolve("op 1 januari 2030 om 11:00").date=="2030-01-01"
    assert resolve("op 2030-01-01 om 11:00").date=="2030-01-01"
    with pytest.raises(AmbiguousTime,match="zomertijd"):
        create_parameters({"summary":"Test"},"Maak 28 maart 2027 om 02:30 een afspraak van twee uur")


def test_personal_appointment_never_invents_external_invite_addresses():
    payload={"summary":"Noah","attendees":["invented@example.invalid"]}
    assert create_parameters(payload,"Maak morgen om 15:00 een afspraak met Noah")["attendees"]==[]
    with pytest.raises(AmbiguousTime,match="e-mailadres"):
        create_parameters(payload,"Maak morgen om 15:00 een afspraak en nodig Noah uit")
    assert create_parameters({"summary":"Test","attendees":["test@example.invalid"]},"Maak morgen om 15:00 een afspraak en nodig test@example.invalid uit")["attendees"]==["test@example.invalid"]


def test_time_correction_preserves_explicit_original_duration():
    result=create_parameters({"summary":"Test"},"Maak morgen van 15:00 tot 17:00 een afspraak\nAanvullende gegevens van dezelfde gebruiker: Nee, toch vrijdag om vier uur")
    assert datetime.fromisoformat(result["start"]).hour==16 and datetime.fromisoformat(result["end"]).hour==18


def test_rescheduling_uses_actual_event_and_preserves_its_duration_and_guests():
    event={"start":{"dateTime":"2030-01-01T11:00:00+01:00"},"end":{"dateTime":"2030-01-01T13:00:00+01:00"}}
    payload={"summary":"Test","start":"1999-01-01T00:00:00Z","end":"1999-01-01T01:00:00Z","attendees":["actual@example.invalid"]}
    result=update_parameters(payload,"Verzet mijn afspraak een uur later",event)
    assert result["start"]=="2030-01-01T12:00:00+01:00" and result["end"]=="2030-01-01T14:00:00+01:00"
    assert result["attendees"]==payload["attendees"] and result["reminder_minutes"] is None
