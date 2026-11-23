"""Conflict analysis uses actual provider occurrences, no invented travel times."""
from datetime import datetime, timedelta, UTC
from urllib.parse import quote


class SmartRescheduleEngine:
    def __init__(self, integrations, store): self.integrations,self.store=integrations,store
    async def analyze(self,p):
        if not p.get("event_id") or not p.get("start") or not p.get("end"): raise ValueError("Kies één concrete afspraak en nieuwe tijden")
        path="/calendar/v3/calendars/"+quote(p["calendar_id"],safe="")+"/events/"+quote(p["event_id"],safe="")
        event=await self.integrations.api("calendar_read",path)
        if event.get("locked") or event.get("status")=="cancelled" or event.get("organizer",{}).get("self") is False: raise ValueError("Deze afspraak kan niet veilig worden gewijzigd")
        start=datetime.fromisoformat(p["start"]); end=datetime.fromisoformat(p["end"])
        if end<=start: raise ValueError("Ongeldige tijden")
        data=await self.integrations.events({"calendar_id":p["calendar_id"],"start":(start-timedelta(days=1)).isoformat(),"end":(end+timedelta(days=1)).isoformat(),"query":""})
        if data.get("nextPageToken"): raise ValueError("Te veel afspraken voor volledige conflictcontrole; kies een kleiner bereik")
        buffer=self.store.preference("calendar_buffer_minutes",15)
        conflicts=[]; neighbours=[];occupied=[]
        for other in data.get("items",[]):
            if other.get("id")==event["id"] or other.get("status")=="cancelled" or other.get("transparency")=="transparent": continue
            def date(value):
                if "dateTime" in value: return datetime.fromisoformat(value["dateTime"])
                from zoneinfo import ZoneInfo
                return datetime.fromisoformat(value["date"]).replace(tzinfo=ZoneInfo(p["timezone"]))
            a=date(other["start"]); b=date(other["end"])
            occupied.append((a,b))
            gap=min(abs((start-b).total_seconds()),abs((a-end).total_seconds()))/60
            brief={"id":other["id"],"summary":other.get("summary","Afspraak"),"gap_minutes":gap}
            if a<end and b>start: conflicts.append(brief)
            elif gap<buffer: neighbours.append(brief)
        proposal={**p,"summary":event.get("summary","Afspraak"),"etag":event["etag"],"attendees":[x["email"] for x in event.get("attendees",[]) if "email" in x],"location":event.get("location","")}
        alternatives=[];candidate=end;duration=end-start
        for _ in range(32):
            proposed_end=candidate+duration
            if 8<=candidate.hour and proposed_end.hour<=19 and not any(a<proposed_end+timedelta(minutes=buffer) and b>candidate-timedelta(minutes=buffer) for a,b in occupied):
                alternatives.append({"start":candidate.isoformat(),"end":proposed_end.isoformat()})
                if len(alternatives)==3:break
            candidate+=timedelta(minutes=30)
        return {"proposal":{"tool":"CalendarUpdate","input":proposal},"conflicts":conflicts,"neighbours":neighbours,"buffer_minutes":buffer,"travel_time_available":False,"warning":"Reistijd onbekend; controleer locaties en naburige afspraken.","recurring":bool(event.get("recurrence") or event.get("recurringEventId")),"requires_approval":True,"alternatives":alternatives}
