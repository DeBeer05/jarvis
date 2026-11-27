"""Atomic conservative credit reservations; no text, voice recordings or secrets."""
from datetime import datetime
import uuid
from zoneinfo import ZoneInfo

from server.security.types import AuthError


class VoiceUsage:
    def __init__(self,store):self.store=store

    def periods(self,config):
        now=datetime.fromtimestamp(self.store.clock(),ZoneInfo(config['general']['timezone']))
        day=now.replace(hour=0,minute=0,second=0,microsecond=0)
        return day.timestamp(),day.replace(day=1).timestamp()

    @staticmethod
    def totals(db,user,day,month):
        row=db.execute("SELECT coalesce(sum(CASE WHEN created>=? THEN credits ELSE 0 END),0),coalesce(sum(credits),0),coalesce(sum(characters),0) FROM voice_usage WHERE user_id=? AND created>=? AND status!='released'",(day,user,month)).fetchone()
        return {'daily_reserved_credits':row[0],'monthly_reserved_credits':row[1],'monthly_requested_characters':row[2]}

    def usage(self,principal,config):
        day,month=self.periods(config);voice=config['voice']
        with self.store.transaction(principal) as (db,user):result=self.totals(db,user,day,month)
        ratios=[result['daily_reserved_credits']/voice['elevenlabs_daily_limit'] if voice['elevenlabs_daily_limit'] else 1,result['monthly_reserved_credits']/voice['elevenlabs_monthly_limit'] if voice['elevenlabs_monthly_limit'] else 1]
        return {**result,'daily_limit':voice['elevenlabs_daily_limit'],'monthly_limit':voice['elevenlabs_monthly_limit'],'warning':max(ratios)*100>=voice['elevenlabs_warning_percent'],
                'conservative_estimate':True,'cancelled_requests_may_cost_credits':True}

    def reserve(self,principal,config,characters,credits):
        day,month=self.periods(config);voice=config['voice'];identifier=str(uuid.uuid4())
        if not 0<characters<=700 or not 0<credits<=100000:raise ValueError('Ongeldige spraakomvang')
        with self.store.transaction(principal,write=True) as (db,user):
            counts=self.totals(db,user,day,month)
            if counts['daily_reserved_credits']+credits>voice['elevenlabs_daily_limit'] or counts['monthly_reserved_credits']+credits>voice['elevenlabs_monthly_limit']:
                raise AuthError('tts_budget','De ingestelde ElevenLabs-limiet is bereikt.',429)
            db.execute('INSERT INTO voice_usage VALUES (?,?,?,?,?,?)',(identifier,user,self.store.clock(),characters,credits,'reserved'))
            db.execute('DELETE FROM voice_usage WHERE user_id=? AND created<?',(user,month-180*86400))
        return identifier

    def finish(self,identifier,status):
        if status not in ('attempted','completed','cancelled','failed','released'):raise ValueError('Ongeldige verbruiksstatus')
        # Settlement must still run after the originating session is revoked.
        with self.store.database.connection() as db:
            db.execute('UPDATE voice_usage SET status=? WHERE id=?',(status,identifier))
