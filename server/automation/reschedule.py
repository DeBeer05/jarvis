"""Conflict analysis uses actual provider occurrences, no invented travel times."""
from datetime import datetime, timedelta, UTC
from urllib.parse import quote
import json
from zoneinfo import ZoneInfo


class SmartRescheduleEngine:
    def __init__(self, integrations, store): self.integrations,self.store=integrations,store
    async def analyze(self,p,device=None):
        preferences=None
        if device:
            with self.store.db() as db:
                saved=db.execute("SELECT s.payload FROM natural_settings s JOIN auth_devices d ON d.user_id=s.user_id WHERE d.id=? AND s.scope='user' AND s.device_id=''",(device,)).fetchone()
            if saved:preferences=json.loads(saved["payload"])["calendar"]
        if not p.get("event_id") or not p.get("start") or not p.get("end"): raise ValueError("Kies één concrete afspraak en nieuwe tijden")
        path="/calendar/v3/calendars/"+quote(p["calendar_id"],safe="")+"/events/"+quote(p["event_id"],safe="")
        event=await self.integrations.api("calendar_read",path)
        if event.get("locked") or event.get("status")=="cancelled" or event.get("organizer",{}).get("self") is False: raise ValueError("Deze afspraak kan niet veilig worden gewijzigd")
        zone=ZoneInfo(p["timezone"])
        start=datetime.fromisoformat(p["start"]).astimezone(zone); end=datetime.fromisoformat(p["end"]).astimezone(zone)
        start_utc,end_utc=start.astimezone(UTC),end.astimezone(UTC)
        if end_utc<=start_utc: raise ValueError("Ongeldige tijden")
        data=await self.integrations.events({"calendar_id":p["calendar_id"],"start":(start-timedelta(days=1)).isoformat(),"end":(end+timedelta(days=1)).isoformat(),"query":""})
        if data.get("nextPageToken"): raise ValueError("Te veel afspraken voor volledige conflictcontrole; kies een kleiner bereik")
        buffer=preferences["buffer_minutes"] if preferences else self.store.preference("calendar_buffer_minutes",15)
        conflicts=[]; neighbours=[];occupied=[]
        for other in data.get("items",[]):
            if other.get("id")==event["id"] or other.get("status")=="cancelled" or other.get("transparency")=="transparent": continue
            def date(value):
                if "dateTime" in value: return datetime.fromisoformat(value["dateTime"])
                return datetime.fromisoformat(value["date"]).replace(tzinfo=ZoneInfo(p["timezone"]))
            a=date(other["start"]).astimezone(UTC); b=date(other["end"]).astimezone(UTC)
            occupied.append((a,b))
            gap=min(abs((start_utc-b).total_seconds()),abs((a-end_utc).total_seconds()))/60
            brief={"id":other["id"],"summary":other.get("summary","Afspraak"),"gap_minutes":gap}
            if a<end_utc and b>start_utc: conflicts.append(brief)
            elif gap<buffer and (not preferences or preferences["neighboring"]): neighbours.append(brief)
        proposal={**p,"summary":event.get("summary","Afspraak"),"etag":event["etag"],"attendees":[x["email"] for x in event.get("attendees",[]) if "email" in x],"location":event.get("location","")}
        alternatives=[];candidate=end;duration=end.astimezone(UTC)-start.astimezone(UTC)
        for _ in range(32):
            if preferences and not preferences["alternatives"]:break
            proposed_end=(candidate.astimezone(UTC)+duration).astimezone(zone)
            work_start=preferences["work_start"] if preferences else "08:00"
            work_end=preferences["work_end"] if preferences else "19:00"
            allowed_day=not preferences or candidate.weekday() in preferences["workdays"]
            if allowed_day and candidate.date()==proposed_end.date() and work_start<=candidate.strftime("%H:%M") and proposed_end.strftime("%H:%M")<=work_end and not any(a<proposed_end.astimezone(UTC)+timedelta(minutes=buffer) and b>candidate.astimezone(UTC)-timedelta(minutes=buffer) for a,b in occupied):
                alternatives.append({"start":candidate.isoformat(),"end":proposed_end.isoformat()})
                if len(alternatives)==3:break
            candidate=(candidate.astimezone(UTC)+timedelta(minutes=30)).astimezone(zone)
        return {"proposal":{"tool":"CalendarUpdate","input":proposal},"conflicts":conflicts,"neighbours":neighbours,"buffer_minutes":buffer,"travel_time_available":False,"warning":"Reistijd onbekend; controleer locaties en naburige afspraken.","recurring":bool(event.get("recurrence") or event.get("recurringEventId")),"requires_approval":True,"alternatives":alternatives}
