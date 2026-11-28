"""Compensating proposals for verified actions; never silently reverses an effect."""
import json
from urllib.parse import quote


class UndoManager:
    def __init__(self,engine):self.engine=engine

    async def propose(self,principal,identifier):
        e=self.engine;device=principal.device_id
        e.permissions.check(device,'automation:write');e.safety.check(device)
        row=e.store.get(identifier)
        with e.store.db() as db:
            owner=db.execute('SELECT a.user_id=b.user_id FROM auth_devices a,auth_devices b WHERE a.id=? AND b.id=?',(device,row['device_id'])).fetchone()
        if not owner or not owner[0] or row['status']!='completed':raise ValueError('Alleen een bevestigde eigen actie kan worden hersteld')
        payload=json.loads(row['payload']);result=json.loads(row['result'] or '{}')
        if row['tool']=='CalendarCreate':
            e.permissions.check_tool(device,'CalendarRead')
            if 'CalendarRead' in e.store.preference('disabled_tools',[]):raise ValueError('Agendalezen is uitgeschakeld')
            if not result.get('id') or not result.get('etag'):raise ValueError('De aangemaakte afspraak is niet verifieerbaar')
            path='/calendar/v3/calendars/'+quote(payload['calendar_id'],safe='')+'/events/'+quote(result['id'],safe='')
            current=await e.integrations.api('calendar_read',path)
            if current.get('id')!=result['id'] or current.get('etag')!=result['etag']:raise ValueError('De afspraak is inmiddels gewijzigd; maak een nieuw verwijdervoorstel')
            tool='CalendarDelete';value={**payload,'event_id':result['id'],'etag':result['etag']}
        elif row['tool']=='DesktopControl' and payload['action'] in ('shutdown','restart'):
            if e.store.clock()-row['updated']>=60:raise ValueError('De afbreektermijn is verstreken')
            tool='DesktopControl';value={'action':'cancel_shutdown'}
        else:raise ValueError('Voor deze actie is geen veilige herstelactie beschikbaar')
        return e.submit(device,tool,value,'undo:'+identifier)
