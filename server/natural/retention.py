"""One bounded maintenance task for existing SQLite data; no inference or account I/O."""
import asyncio
import json
import logging
from datetime import datetime,UTC

from server.natural.models import UserSettings

logger=logging.getLogger("jarvis.server")
OPEN_JOBS=frozenset({"approval","queued","running","waiting","paused","blocked","uncertain"})


class RetentionManager:
    def __init__(self,natural):self.natural=natural;self.task=None

    def start(self):
        if self.task is None or self.task.done():self.task=asyncio.create_task(self.run())

    async def close(self):
        if self.task:
            self.task.cancel();await asyncio.gather(self.task,return_exceptions=True);self.task=None

    async def run(self):
        while True:
            work=asyncio.create_task(asyncio.to_thread(self.sweep))
            try:await asyncio.shield(work)
            except asyncio.CancelledError:
                await asyncio.gather(work,return_exceptions=True)
                raise
            except Exception:logger.warning("retention_unavailable")
            await asyncio.sleep(60)

    def sweep(self):
        natural=self.natural;store=natural.store;now=store.clock()
        busy={run.conversation_id for run in list(natural.chat.active.values()) if run.conversation_id}
        with store.database.connection() as db:
            import sqlite3
            db.row_factory=sqlite3.Row;db.execute("BEGIN IMMEDIATE")
            users=db.execute("SELECT id FROM auth_users").fetchall()
            for user_row in users:
                user=user_row["id"]
                if getattr(natural,'device_status',None):natural.device_status.prune(db,user,now)
                db.execute("UPDATE automation_jobs SET status='uncertain',result=?,updated=? WHERE tool='MobileHandoff' AND status='waiting' AND EXISTS(SELECT 1 FROM natural_events e WHERE e.user_id=? AND e.kind='device.handoff' AND json_extract(e.payload,'$.job_id')=automation_jobs.id AND e.expires<=?)",(json.dumps({'handoff':'expired_unconfirmed','called':False,'sent':False}),now,user,now))
                saved=db.execute("SELECT payload FROM natural_settings WHERE user_id=? AND scope='user' AND device_id=''",(user,)).fetchone()
                config=UserSettings.model_validate_json(saved["payload"]).model_dump(mode="json") if saved else UserSettings().model_dump(mode="json")
                if config["memory"]["prune_expired"]:
                    expired=db.execute("SELECT * FROM natural_memories WHERE user_id=? AND expires IS NOT NULL AND expires<=? LIMIT 100",(user,now)).fetchall()
                    for memory in expired:
                        natural.memory.forget_source(db,user,memory);natural.memory.invalidate_summaries(db,user,memory["id"])
                        db.execute("DELETE FROM natural_memory_fts WHERE id=? AND user_id=?",(memory["id"],user))
                        db.execute("DELETE FROM natural_memories WHERE id=? AND user_id=?",(memory["id"],user))
                    if expired:store.audit(db,user,"system","memory_expired")
                cutoff=datetime.fromtimestamp(now-config["privacy"]["history_days"]*86400,UTC).isoformat()
                rows=db.execute("SELECT t.id,t.conversation_id FROM chat_turns t JOIN natural_conversation_owners o ON o.conversation_id=t.conversation_id WHERE o.user_id=? AND t.created_at<? AND t.status!='running' AND (t.user_text!='' OR t.assistant_text!='') AND NOT EXISTS(SELECT 1 FROM natural_sessions s WHERE s.conversation_id=t.conversation_id AND s.lease_until>?) LIMIT 200",(user,cutoff,now)).fetchall()
                changed=False
                for row in rows:
                    if row["conversation_id"] in busy:continue
                    db.execute("UPDATE chat_turns SET user_text='',assistant_text='' WHERE id=?",(row["id"],))
                    db.execute("DELETE FROM natural_summaries WHERE user_id=? AND conversation_id=?",(user,row["conversation_id"]))
                    db.execute("UPDATE chat_conversations SET title='Gesprek (oude inhoud verwijderd)' WHERE id=? AND NOT EXISTS(SELECT 1 FROM chat_turns WHERE conversation_id=? AND user_text!='')",(row["conversation_id"],row["conversation_id"]))
                    changed=True
                if changed:store.audit(db,user,"system","history_expired")
                db.execute("DELETE FROM natural_diagnostics WHERE user_id=? AND at<?",(user,now-config["privacy"]["diagnostic_days"]*86400))
                for plan in db.execute("SELECT id,conversation_id FROM natural_pending WHERE user_id=? AND kind='activity_plan' AND updated<? LIMIT 100",(user,now-config['privacy']['history_days']*86400)).fetchall():
                    if plan['conversation_id'] not in busy:db.execute('DELETE FROM natural_pending WHERE id=? AND user_id=?',(plan['id'],user))
                for row in db.execute("SELECT id,payload,conversation_id FROM natural_pending WHERE user_id=? AND kind='automation_context' AND updated<? LIMIT 50",(user,now-config["privacy"]["history_days"]*86400)).fetchall():
                    if row["conversation_id"] in busy:continue
                    payload=json.loads(row["payload"])
                    if payload.get("write_question") or payload.get("read_question"):continue
                    jobs=[db.execute("SELECT status FROM automation_jobs WHERE id=?",(job["id"],)).fetchone() for job in payload.get("jobs",[])]
                    if any(job and job["status"] in OPEN_JOBS for job in jobs):continue
                    db.execute("DELETE FROM natural_pending WHERE id=? AND user_id=?",(row["id"],user))
