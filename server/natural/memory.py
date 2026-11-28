"""Small SQLite/FTS5 memory; source-aware forgetting and no background vector service."""
import hashlib
import json
import re
import uuid

from server.natural.models import MemoryInput
from server.natural.store import Conflict
from server.natural.search_terms import expand

SENSITIVE=re.compile(r"\b(?:wachtwoord|password|api.?key|token|bankrekening|iban|bsn|diagnose|medisch|medicatie|seksueel|huisadres|adres is|ik woon op|creditcard|financieel overzicht)\b",re.I)
SECRET=re.compile(r"(?:-----BEGIN .*PRIVATE KEY|\b(?:sk-|gsk_)[A-Za-z0-9]{16,}|\bAIza[A-Za-z0-9_-]{20,})")


class MemoryManager:
    def __init__(self,store):self.store=store

    @staticmethod
    def scope(db,user,principal):
        row=db.execute("SELECT payload FROM natural_settings WHERE user_id=? AND scope='user' AND device_id=''",(user,)).fetchone()
        if row and not json.loads(row["payload"])["memory"]["synchronize"]:
            return " AND m.id IN (SELECT memory_id FROM natural_memory_origins WHERE device_id=?)",[principal.device_id]
        return "",[]

    @staticmethod
    def public(row):
        result=dict(row);result["explicit"]=bool(result["explicit"])
        return result

    def save(self,principal,data,*,identifier=None,revision=None,source="explicit",source_turn=None,explicit=True):
        value=MemoryInput.model_validate(data);content=self.store.safe_content(value.content)
        if SECRET.search(content) or re.search(r"\b(?:wachtwoord|password|api.?key|token)\s*(?:is|:|=)",content,re.I):raise ValueError("Sla geen geheimen op")
        sensitive=value.sensitivity=="sensitive" or bool(SENSITIVE.search(content))
        if sensitive and (not explicit or not value.consent_sensitive):raise ValueError("Gevoelig geheugen vereist expliciete toestemming")
        now=self.store.clock()
        if value.expires_at is not None and value.expires_at<=now:raise ValueError("Vervaldatum ligt in het verleden")
        identifier=identifier or str(uuid.uuid4())
        with self.store.transaction(principal,write=True) as (db,user):
            scope,args=self.scope(db,user,principal)
            old=db.execute("SELECT * FROM natural_memories WHERE id=? AND user_id=?",(identifier,user)).fetchone()
            origin_row=db.execute("SELECT device_id FROM natural_memory_origins WHERE memory_id=?",(identifier,)).fetchone()
            original_origin=origin_row[0] if origin_row else None
            if old and not db.execute("SELECT m.id FROM natural_memories m WHERE m.id=? AND m.user_id=?"+scope,(identifier,user,*args)).fetchone():raise ValueError("Herinnering niet gevonden")
            if revision is not None and (not old or old["revision"]!=revision):raise Conflict("Herinnering gewijzigd; ververs eerst")
            if old is None and revision is not None:raise ValueError("Herinnering niet gevonden")
            if db.execute("SELECT count(*) FROM natural_memories WHERE user_id=?",(user,)).fetchone()[0]>=10000 and not old:raise ValueError("Geheugenlimiet bereikt")
            if value.key and value.status=="active":
                previous=db.execute("SELECT m.* FROM natural_memories m WHERE m.user_id=? AND m.memory_key=? AND m.id!=? AND m.status='active'"+scope,(user,value.key,identifier,*args)).fetchall()
                for entry in previous:
                    self.invalidate_summaries(db,user,entry["id"])
                    self.forget_source(db,user,entry)
                    db.execute("UPDATE natural_memories SET status='outdated',revision=revision+1 WHERE id=?",(entry["id"],))
            if old:
                self.invalidate_summaries(db,user,identifier);self.forget_source(db,user,old)
            settings=db.execute("SELECT payload FROM natural_settings WHERE user_id=? AND scope='user' AND device_id=''",(user,)).fetchone()
            import json
            days=json.loads(settings["payload"])["memory"]["retention_days"] if settings else 365
            expires=value.expires_at if value.expires_at is not None else now+days*86400
            fields=(identifier,user,value.category,content,value.key,value.kind,source,source_turn or (old["source_turn"] if old else None),old["created"] if old else now,now,None,value.confidence,"sensitive" if sensitive else "normal",expires,value.status,int(explicit),old["revision"]+1 if old else 1)
            db.execute("INSERT OR REPLACE INTO natural_memories VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",fields)
            # REPLACE cascades foreign keys; restore the original device binding.
            if old is None:origin=principal.device_id
            else:origin=original_origin
            if origin:db.execute("INSERT INTO natural_memory_origins VALUES (?,?)",(identifier,origin))
            db.execute("DELETE FROM natural_memory_fts WHERE id=?",(identifier,))
            db.execute("INSERT INTO natural_memory_fts VALUES (?,?,?,?)",(identifier,user,content,value.category))
            self.store.audit(db,user,principal.device_id,"memory_updated" if old else "memory_created",identifier)
            result=db.execute("SELECT * FROM natural_memories WHERE id=? AND user_id=?",(identifier,user)).fetchone()
        return self.public(result)

    @staticmethod
    def invalidate_summaries(db,user,identifier):
        # Follow provenance, including memories created after a summary. Preserve
        # unrelated conversations and manually edited notes belonging to the user.
        db.execute("""DELETE FROM natural_summaries WHERE user_id=? AND (
            id IN (SELECT summary_id FROM natural_summary_sources WHERE memory_id=?)
            OR EXISTS (SELECT 1 FROM natural_memories m WHERE m.id=? AND m.user_id=?
                AND instr(lower(natural_summaries.content),lower(m.content))>0)
            OR EXISTS (SELECT 1 FROM chat_turns t WHERE
                t.conversation_id=natural_summaries.conversation_id
                AND t.sequence<=natural_summaries.through_sequence AND (
                    t.id IN (SELECT source_turn FROM natural_memories WHERE id=? AND user_id=?)
                    OR t.id IN (SELECT p.id FROM natural_pending p,json_each(p.payload) j
                        WHERE p.user_id=? AND p.kind='memory_context' AND j.value=?))))""",
            (user,identifier,identifier,user,identifier,user,user,identifier))

    def forget_source(self,db,user,row):
        if row["source_turn"]:
            db.execute("INSERT OR IGNORE INTO natural_forgotten VALUES (?,?,?,?)",(user,row["source_turn"],hashlib.sha256(row["content"].encode()).hexdigest(),self.store.clock()))
        # Also exclude turns that consumed this memory; their answers may quote it.
        dependents=db.execute("SELECT DISTINCT p.id FROM natural_pending p,json_each(p.payload) j WHERE p.user_id=? AND p.kind='memory_context' AND j.value=?",(user,row["id"])).fetchall()
        for item in dependents:
            db.execute("INSERT OR IGNORE INTO natural_forgotten VALUES (?,?,?,?)",(user,item["id"],hashlib.sha256(row["content"].encode()).hexdigest(),self.store.clock()))
        # Forget every later turn that consumed an episode derived from this
        # fact, including transitive retrieval across conversations.
        db.execute("""INSERT OR IGNORE INTO natural_forgotten
            WITH RECURSIVE affected(id) AS (
                SELECT source_turn FROM natural_forgotten WHERE user_id=?
                UNION SELECT e.turn_id FROM natural_episode_sources e JOIN affected a ON e.source_turn=a.id
                JOIN chat_turns t ON t.id=e.turn_id
                JOIN natural_conversation_owners o ON o.conversation_id=t.conversation_id AND o.user_id=?)
            SELECT ?,id,?,? FROM affected a WHERE NOT EXISTS (
                SELECT 1 FROM natural_forgotten f WHERE f.user_id=? AND f.source_turn=a.id)""",
            (user,user,user,hashlib.sha256(row['content'].encode()).hexdigest(),self.store.clock(),user))
        db.execute("""DELETE FROM natural_summaries WHERE user_id=? AND EXISTS (
            SELECT 1 FROM chat_turns t JOIN natural_episode_sources e ON e.turn_id=t.id
            JOIN natural_forgotten f ON f.source_turn=e.source_turn AND f.user_id=?
            WHERE t.conversation_id=natural_summaries.conversation_id
            AND t.sequence<=natural_summaries.through_sequence)""",(user,user))

    def list(self,principal,*,query="",category=None,status=None,limit=50,offset=0,include_sensitive=True):
        limit=max(1,min(100,int(limit)));offset=max(0,min(10000,int(offset)))
        with self.store.transaction(principal) as (db,user):
            scope,scope_args=self.scope(db,user,principal)
            clauses=["m.user_id=?"];params=[user]
            if category:clauses.append("m.category=?");params.append(category)
            if status:clauses.append("m.status=?");params.append(status)
            if not include_sensitive:clauses.append("m.sensitivity='normal'")
            terms=re.findall(r"[\wÀ-ÿ]{2,40}",query)[:12]
            if query and not terms:return {"items":[],"has_more":False}
            if terms:
                clauses.append("m.id IN (SELECT id FROM natural_memory_fts WHERE natural_memory_fts MATCH ? AND user_id=?)")
                params += [" OR ".join('"'+word.replace('"','')+'"' for word in terms),user]
            rows=db.execute("SELECT m.* FROM natural_memories m WHERE "+" AND ".join(clauses)+scope+" ORDER BY m.updated DESC LIMIT ? OFFSET ?",(*params,*scope_args,limit+1,offset)).fetchall()
        return {"items":[self.public(row) for row in rows[:limit]],"has_more":len(rows)>limit}

    def retrieve(self,principal,query,*,limit=8,include_sensitive=False):
        now=self.store.clock()
        stops={"de","het","een","en","of","van","voor","naar","met","dat","dit","die","over","wat","wie","hoe","waar","wanneer","welke","ik","je","jij","mijn","me","mij","we","ons","is","zijn","ben","heb","heeft","kan","kun","wil","zou","maar","ook","nog","dan","er","te","in","op","aan","bij","om","als","vertel","graag"}
        words=set(re.findall(r"[\wÀ-ÿ]{2,40}",query.casefold()))-stops
        terms=[]
        for word in sorted(words)[:12]:terms.append('"afspr"*' if word in ("afspraak","afspraken") else '"'+word+'"')
        if not terms:return []
        with self.store.transaction(principal) as (db,user):
            scope,args=self.scope(db,user,principal)
            saved=db.execute("SELECT payload FROM natural_settings WHERE user_id=? AND scope='user' AND device_id=''",(user,)).fetchone()
            if saved and json.loads(saved["payload"])["memory"]["semantic_search"]:
                terms=['"afspr"*' if word in ("afspraak","afspraken") else '"'+word+'"' for word in expand(words)]
            rows=db.execute("SELECT m.*,bm25(natural_memory_fts) AS relevance FROM natural_memory_fts JOIN natural_memories m ON m.id=natural_memory_fts.id WHERE natural_memory_fts MATCH ? AND natural_memory_fts.user_id=? AND m.user_id=? AND m.status='active' AND (m.expires IS NULL OR m.expires>?) AND (? OR m.sensitivity='normal')"+scope+" ORDER BY relevance,m.updated DESC LIMIT 100",(" OR ".join(terms),user,user,now,include_sensitive,*args)).fetchall()
            candidates=[dict(row) for row in rows]
            latest={}
            for item in candidates:
                key=item["memory_key"]
                if key and key not in latest:
                    row=db.execute("SELECT m.id FROM natural_memories m WHERE m.user_id=? AND m.memory_key=? AND m.status='active' AND (m.expires IS NULL OR m.expires>?)"+scope+" ORDER BY m.updated DESC,m.id DESC LIMIT 1",(user,key,now,*args)).fetchone()
                    latest[key]=row[0] if row else None
            candidates=[item for item in candidates if not item["memory_key"] or latest[item["memory_key"]]==item["id"]]
        def score(item):
            overlap=len(words & set(re.findall(r"\w{2,}",item["content"].casefold())))
            age=max(0,(now-item["updated"])/86400)
            return overlap*3+min(10,-item["relevance"]*2)+item["confidence"]*2+(1 if item["explicit"] else 0)+1/(1+age/30)
        candidates=[item for item in candidates if item["expires"] is None or item["expires"]>now]
        selected=sorted(candidates,key=score,reverse=True)[:max(0,min(20,limit))]
        if selected:
            with self.store.transaction(principal,write=True) as (db,user):
                for item in selected:db.execute("UPDATE natural_memories SET last_used=? WHERE id=? AND user_id=?",(now,item["id"],user))
        return [self.public({key:value for key,value in item.items() if key!="relevance"}) for item in selected]

    def delete(self,principal,identifier,revision=None):
        with self.store.transaction(principal,write=True) as (db,user):
            scope,args=self.scope(db,user,principal)
            row=db.execute("SELECT m.* FROM natural_memories m WHERE m.id=? AND m.user_id=?"+scope,(identifier,user,*args)).fetchone()
            if not row:raise ValueError("Herinnering niet gevonden")
            if revision is not None and row["revision"]!=revision:raise Conflict("Herinnering gewijzigd; ververs eerst")
            self.forget_source(db,user,row)
            self.invalidate_summaries(db,user,identifier)
            db.execute("DELETE FROM natural_memory_fts WHERE id=? AND user_id=?",(identifier,user))
            db.execute("DELETE FROM natural_memories WHERE id=? AND user_id=?",(identifier,user))
            self.store.audit(db,user,principal.device_id,"memory_deleted",identifier)
        return {"deleted":True,"original_conversations_retained":True}

    def clear(self,principal):
        with self.store.transaction(principal,write=True) as (db,user):
            scope,args=self.scope(db,user,principal)
            for row in db.execute("SELECT m.* FROM natural_memories m WHERE m.user_id=?"+scope,(user,*args)).fetchall():
                self.forget_source(db,user,row);self.invalidate_summaries(db,user,row["id"])
                db.execute("DELETE FROM natural_memory_fts WHERE id=? AND user_id=?",(row["id"],user))
                db.execute("DELETE FROM natural_memories WHERE id=? AND user_id=?",(row["id"],user))
            if not scope:db.execute("DELETE FROM natural_summaries WHERE user_id=?",(user,))
            self.store.audit(db,user,principal.device_id,"memory_cleared")
        return {"deleted":True,"original_conversations_retained":True}

    def prune(self,principal):
        now=self.store.clock()
        with self.store.transaction(principal,write=True) as (db,user):
            expired=db.execute("SELECT * FROM natural_memories WHERE user_id=? AND expires IS NOT NULL AND expires<=?",(user,now)).fetchall()
            for row in expired:
                self.forget_source(db,user,row);self.invalidate_summaries(db,user,row["id"])
                db.execute("DELETE FROM natural_memory_fts WHERE id=? AND user_id=?",(row["id"],user))
                db.execute("DELETE FROM natural_memories WHERE id=? AND user_id=?",(row["id"],user))
            if expired:self.store.audit(db,user,principal.device_id,"memory_expired")
