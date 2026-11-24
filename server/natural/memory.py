"""Small SQLite/FTS5 memory; source-aware forgetting and no background vector service."""
import hashlib
import re
import uuid

from server.natural.models import MemoryInput
from server.natural.store import Conflict

SENSITIVE=re.compile(r"\b(?:wachtwoord|password|api.?key|token|bankrekening|iban|bsn|diagnose|medisch|medicatie|seksueel|huisadres|adres is|ik woon op|creditcard)\b",re.I)
SECRET=re.compile(r"(?:-----BEGIN .*PRIVATE KEY|\b(?:sk-|gsk_)[A-Za-z0-9]{16,}|\bAIza[A-Za-z0-9_-]{20,})")


class MemoryManager:
    def __init__(self,store):self.store=store

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
            old=db.execute("SELECT * FROM natural_memories WHERE id=? AND user_id=?",(identifier,user)).fetchone()
            if revision is not None and (not old or old["revision"]!=revision):raise Conflict("Herinnering gewijzigd; ververs eerst")
            if old is None and revision is not None:raise ValueError("Herinnering niet gevonden")
            if db.execute("SELECT count(*) FROM natural_memories WHERE user_id=?",(user,)).fetchone()[0]>=10000 and not old:raise ValueError("Geheugenlimiet bereikt")
            if value.key and value.status=="active":
                previous=db.execute("SELECT * FROM natural_memories WHERE user_id=? AND memory_key=? AND id!=? AND status='active'",(user,value.key,identifier)).fetchall()
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
            db.execute("DELETE FROM natural_memory_fts WHERE id=?",(identifier,))
            db.execute("INSERT INTO natural_memory_fts VALUES (?,?,?,?)",(identifier,user,content,value.category))
            self.store.audit(db,user,principal.device_id,"memory_updated" if old else "memory_created",identifier)
            result=db.execute("SELECT * FROM natural_memories WHERE id=? AND user_id=?",(identifier,user)).fetchone()
        return self.public(result)

    @staticmethod
    def invalidate_summaries(db,user,identifier):
        # Conservative invalidation includes summaries containing an earlier source
        # utterance, even if that memory was created after the summary itself.
        db.execute("DELETE FROM natural_summaries WHERE user_id=?",(user,))

    def forget_source(self,db,user,row):
        if row["source_turn"]:
            db.execute("INSERT OR IGNORE INTO natural_forgotten VALUES (?,?,?,?)",(user,row["source_turn"],hashlib.sha256(row["content"].encode()).hexdigest(),self.store.clock()))
        # Also exclude turns that consumed this memory; their answers may quote it.
        dependents=db.execute("SELECT DISTINCT p.id FROM natural_pending p,json_each(p.payload) j WHERE p.user_id=? AND p.kind='memory_context' AND j.value=?",(user,row["id"])).fetchall()
        for item in dependents:
            db.execute("INSERT OR IGNORE INTO natural_forgotten VALUES (?,?,?,?)",(user,item["id"],hashlib.sha256(row["content"].encode()).hexdigest(),self.store.clock()))

    def list(self,principal,*,query="",category=None,status=None,limit=50,offset=0,include_sensitive=True):
        limit=max(1,min(100,int(limit)));offset=max(0,min(10000,int(offset)))
        with self.store.transaction(principal) as (db,user):
            clauses=["m.user_id=?"];params=[user]
            if category:clauses.append("m.category=?");params.append(category)
            if status:clauses.append("m.status=?");params.append(status)
            if not include_sensitive:clauses.append("m.sensitivity='normal'")
            terms=re.findall(r"[\wÀ-ÿ]{2,40}",query)[:12]
            if query and not terms:return {"items":[],"has_more":False}
            if terms:
                clauses.append("m.id IN (SELECT id FROM natural_memory_fts WHERE natural_memory_fts MATCH ? AND user_id=?)")
                params += [" OR ".join('"'+word.replace('"','')+'"' for word in terms),user]
            rows=db.execute("SELECT m.* FROM natural_memories m WHERE "+" AND ".join(clauses)+" ORDER BY m.updated DESC LIMIT ? OFFSET ?",(*params,limit+1,offset)).fetchall()
        return {"items":[self.public(row) for row in rows[:limit]],"has_more":len(rows)>limit}

    def retrieve(self,principal,query,*,limit=8,include_sensitive=False):
        now=self.store.clock()
        stops={"de","het","een","en","of","van","voor","naar","met","dat","dit","die","over","wat","wie","hoe","waar","wanneer","welke","ik","je","jij","mijn","me","mij","we","ons","is","zijn","ben","heb","heeft","kan","kun","wil","zou","maar","ook","nog","dan","er","te","in","op","aan","bij","om","als","vertel","graag"}
        words=set(re.findall(r"[\wÀ-ÿ]{2,40}",query.casefold()))-stops
        terms=[]
        for word in sorted(words)[:12]:terms.append('"afspr"*' if word in ("afspraak","afspraken") else '"'+word+'"')
        if not terms:return []
        with self.store.transaction(principal) as (db,user):
            rows=db.execute("SELECT m.*,bm25(natural_memory_fts) AS relevance FROM natural_memory_fts JOIN natural_memories m ON m.id=natural_memory_fts.id WHERE natural_memory_fts MATCH ? AND natural_memory_fts.user_id=? AND m.user_id=? AND m.status='active' AND (m.expires IS NULL OR m.expires>?) AND (? OR m.sensitivity='normal') ORDER BY relevance,m.updated DESC LIMIT 100",(" OR ".join(terms),user,user,now,include_sensitive)).fetchall()
            candidates=[dict(row) for row in rows]
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
            row=db.execute("SELECT * FROM natural_memories WHERE id=? AND user_id=?",(identifier,user)).fetchone()
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
            for row in db.execute("SELECT * FROM natural_memories WHERE user_id=?",(user,)).fetchall():self.forget_source(db,user,row)
            db.execute("DELETE FROM natural_memory_fts WHERE user_id=?",(user,))
            db.execute("DELETE FROM natural_memories WHERE user_id=?",(user,))
            db.execute("DELETE FROM natural_summaries WHERE user_id=?",(user,))
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
