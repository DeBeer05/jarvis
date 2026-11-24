"""Explicit personal address book. Only the requested recipient leaves this store."""
import json
import re
import unicodedata
from uuid import uuid4
from pydantic import Field, field_validator
from server.natural.models import StrictModel
from server.natural.store import Conflict, encode


def normalized(value):
    return " ".join(unicodedata.normalize("NFKC",value).casefold().split())


def mailbox(value):
    if len(value)>254 or not re.fullmatch(r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]+@[A-Za-z0-9.-]+",value):return False
    local,domain=value.rsplit("@",1)
    return (len(local)<=64 and not local.startswith(".") and not local.endswith(".") and ".." not in local
        and "." in domain and all(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?",part) for part in domain.split(".")))


class ContactInput(StrictModel):
    name:str=Field(min_length=1,max_length=80)
    email:str=Field(min_length=3,max_length=254)
    aliases:list[str]=Field(default_factory=list,max_length=8)

    @field_validator("name","email")
    @classmethod
    def clean_text(cls,value):
        if value!=value.strip() or any(unicodedata.category(c).startswith("C") for c in value):raise ValueError("Controleer naam en adres")
        return value

    @field_validator("email")
    @classmethod
    def valid_email(cls,value):
        if not mailbox(value):raise ValueError("Vul één volledig e-mailadres in")
        return value

    @field_validator("aliases")
    @classmethod
    def valid_aliases(cls,values):
        for value in values:
            if not 1<=len(value)<=80:raise ValueError("Alias te lang of leeg")
            cls.clean_text(value)
        return list(dict.fromkeys(values))


class ContactUpdate(ContactInput):
    revision:int=Field(ge=1)


class ContactManager:
    def __init__(self,store):self.store=store

    @staticmethod
    def document(row):
        data=dict(row);data.pop("user_id",None);data["aliases"]=json.loads(data["aliases"]);return data

    def list(self,principal):
        with self.store.transaction(principal) as (db,user):
            return {"items":[self.document(row) for row in db.execute("SELECT * FROM natural_contacts WHERE user_id=? ORDER BY name COLLATE NOCASE,id",(user,))]}

    def save(self,principal,value,identifier=None):
        model=ContactUpdate.model_validate(value) if identifier else ContactInput.model_validate(value)
        self.store.safe_content(encode(model.model_dump()))
        with self.store.transaction(principal,write=True) as (db,user):
            if identifier:
                old=db.execute("SELECT * FROM natural_contacts WHERE id=? AND user_id=?",(identifier,user)).fetchone()
                if not old or old["revision"]!=getattr(model,"revision",None):raise Conflict()
                revision=old["revision"]+1
                db.execute("UPDATE natural_contacts SET name=?,email=?,aliases=?,revision=?,updated=? WHERE id=? AND user_id=?",(model.name,model.email,encode(model.aliases),revision,self.store.clock(),identifier,user))
            else:
                if db.execute("SELECT count(*) FROM natural_contacts WHERE user_id=?",(user,)).fetchone()[0]>=200:raise ValueError("Adresboek vol (200 contacten)")
                identifier=str(uuid4());now=self.store.clock()
                db.execute("INSERT INTO natural_contacts VALUES (?,?,?,?,?,1,?,?)",(identifier,user,model.name,model.email,encode(model.aliases),now,now))
            self.store.audit(db,user,principal.device_id,"contact_updated" if isinstance(model,ContactUpdate) else "contact_created",identifier)
            return self.document(db.execute("SELECT * FROM natural_contacts WHERE id=?",(identifier,)).fetchone())

    def delete(self,principal,identifier,revision):
        with self.store.transaction(principal,write=True) as (db,user):
            changed=db.execute("DELETE FROM natural_contacts WHERE id=? AND user_id=? AND revision=?",(identifier,user,revision)).rowcount
            if not changed:raise Conflict()
            self.store.audit(db,user,principal.device_id,"contact_deleted",identifier)
            return {"deleted":True}

    def lookup(self,principal,name):
        key=normalized(name)
        return [item for item in self.list(principal)["items"] if key in [normalized(item["name"]),*[normalized(alias) for alias in item["aliases"]]]]

    def recipient(self,principal,instruction):
        # Only explicit recipient grammar before the body; never scan received mail.
        parts=instruction.split("\nAanvullende gegevens van dezelfde gebruiker: ")
        header=re.split(r"\b(?:dat|waarin|met onderwerp|met tekst|over)\b|[:,\n]",parts[0],maxsplit=1,flags=re.I)[0]
        match=re.search(r"\b(?:mail|e-mail|email|bericht|concept)\s+(?:aan|naar|voor)\s+(.+)$",header,re.I)
        if not match:match=re.search(r"\b(?:stuur|verstuur|schrijf)\s+(.+?)\s+(?:een\s+)?(?:mail|e-mail|email|bericht)\b",header,re.I)
        if not match:match=re.search(r"\b(?:wil\s+)(.+?)\s+mailen\b",header,re.I)
        if not match:return None,None
        name=match[1].strip().strip('"“”').rstrip('.!?')
        if mailbox(name):return {"email":name},None
        matches=self.lookup(principal,name)
        if len(matches)==1:return matches[0],None
        for supplement in parts[1:]:
            candidate=supplement.strip().rstrip('.!?')
            if mailbox(candidate):return {"email":candidate},None
            resolved=self.lookup(principal,candidate)
            if len(resolved)==1:return resolved[0],None
        return None,("Er zijn meerdere contacten met die naam. Noem de volledige unieke contactnaam of het e-mailadres." if matches else "Ik vind geen uniek contact met die naam. Noem de opgeslagen contactnaam of het volledige e-mailadres.")
