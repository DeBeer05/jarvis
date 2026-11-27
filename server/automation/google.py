"""Official Google REST/OAuth endpoints only. No arbitrary URLs or redirects."""
import asyncio
import base64
import hashlib
import json
from contextvars import ContextVar
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import quote, urlencode

import httpx

from server.automation.store import encode, fingerprint
from server.automation.vault import SecretVault
from server.security.types import digest, pkce, token

SCOPES = {
    "calendar_read": "https://www.googleapis.com/auth/calendar.readonly",
    "calendar_write": "https://www.googleapis.com/auth/calendar.events",
    "gmail_read": "https://www.googleapis.com/auth/gmail.readonly",
    "gmail_compose": "https://www.googleapis.com/auth/gmail.compose",
}
WRITE_GUARD=ContextVar("automation_write_guard",default=None)
REQUEST_GUARD=ContextVar("automation_request_guard",default=None)


class IntegrationManager:
    def __init__(self, store, security, port=8765, *, vault=None, transport=None, client_config=None):
        self.store, self.security, self.port = store, security, port
        self.vault = vault or SecretVault(store,key_file=security.settings.vault_key_file)
        self.http = httpx.AsyncClient(timeout=20, follow_redirects=False, trust_env=False, transport=transport)
        self.lock = asyncio.Lock()
        self.client_config = client_config

    def config(self):
        if self.client_config is not None: return self.client_config
        path = self.security.settings.google_client_file
        if not path: raise ValueError("Stel JARVIS_GOOGLE_CLIENT_FILE in met je Desktop OAuth-clientbestand")
        try:
            document=json.loads(Path(path).read_text(encoding='utf-8'))
            kind='web' if 'web' in document else 'installed';data=document[kind]
            if not data["client_id"].endswith(".apps.googleusercontent.com"): raise ValueError()
            return {"client_id": data["client_id"], "client_secret": data.get("client_secret", ""),'kind':kind,'redirect_uris':data.get('redirect_uris',[])}
        except (OSError, KeyError, ValueError): raise ValueError("Ongeldig Desktop OAuth-clientbestand") from None

    @property
    def redirect(self): return (self.security.settings.public_origin or f"http://127.0.0.1:{self.port}")+"/oauth/google/callback"

    def begin(self, principal, features):
        config = self.config()
        if self.security.settings.public_origin and (config.get('kind')!='web' or self.redirect not in config.get('redirect_uris',[])):raise ValueError('Een nieuwe cloudkoppeling vereist een Web OAuth-client met de exacte HTTPS-callback')
        if not features or not set(features) <= SCOPES.keys(): raise ValueError("Invalid OAuth features")
        verifier, state = token(), token()
        payload = self.vault.crypt(encode({"verifier": verifier, "features": features}).encode())
        with self.store.db(True) as db:
            db.execute("DELETE FROM integration_oauth WHERE expires<?", (self.store.clock(),))
            db.execute("INSERT INTO integration_oauth VALUES (?,?,?,?,?)", (digest(state), payload, self.store.clock()+300, principal.session_id, principal.device_id))
        return {"authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
            "client_id": config["client_id"], "redirect_uri": self.redirect, "response_type": "code",
            "scope": " ".join(SCOPES[x] for x in features), "state": state, "code_challenge": pkce(verifier),
            "code_challenge_method": "S256", "access_type": "offline", "prompt": "consent",
        })}

    async def callback(self, state, code):
        with self.store.db(True) as db:
            row = db.execute("SELECT * FROM integration_oauth WHERE state_hash=? AND expires>?", (digest(state), self.store.clock())).fetchone()
            if not row: raise ValueError("OAuth-verzoek verlopen of ongeldig")
            db.execute("DELETE FROM integration_oauth WHERE state_hash=?", (digest(state),))
            live = db.execute("SELECT 1 FROM auth_sessions s JOIN auth_devices d ON d.id=s.device_id JOIN auth_permissions p ON p.device_id=d.id WHERE s.id=? AND s.device_id=? AND s.expires_at>? AND s.revoked_at IS NULL AND d.revoked_at IS NULL AND p.permission='integrations:manage'", (row["session_id"], row["device_id"], self.store.clock())).fetchone()
            if not live: raise ValueError("OAuth-sessie ingetrokken")
        data = json.loads(self.vault.crypt(row["ciphertext"], True))
        credentials = await self._token({**self.config(), "code": code, "code_verifier": data["verifier"], "redirect_uri": self.redirect, "grant_type": "authorization_code"})
        if not credentials.get("refresh_token"): raise ValueError("Geen refresh-token ontvangen; koppel opnieuw met toestemming")
        granted = set(credentials.get("scope", "").split())
        if not {SCOPES[x] for x in data["features"]} <= granted: raise ValueError("Niet alle aangevraagde rechten verleend")
        credentials["features"] = data["features"]
        credentials["deadline"] = self.store.clock()+int(credentials.get("expires_in", 3600))-60
        with self.store.db() as db:
            live=db.execute("SELECT 1 FROM auth_sessions s JOIN auth_devices d ON d.id=s.device_id JOIN auth_permissions p ON p.device_id=d.id WHERE s.id=? AND s.revoked_at IS NULL AND s.expires_at>? AND d.revoked_at IS NULL AND p.permission='integrations:manage'",(row["session_id"],self.store.clock())).fetchone()
        if not live: raise ValueError("OAuth-sessie ingetrokken tijdens koppeling")
        self.vault.put("google", encode(credentials))
        with self.store.db(True) as db: self.store.event(db, "google_connected", device=row["device_id"])

    async def _token(self, form):
        response = await self.http.post("https://oauth2.googleapis.com/token", data=form)
        if response.status_code != 200 or len(response.content) > 32000: raise ValueError("Google-tokenvernieuwing mislukt; koppel zo nodig opnieuw")
        data = response.json()
        if not isinstance(data.get("access_token"), str): raise ValueError("Ongeldig tokenantwoord")
        return data

    async def access(self, feature):
        async with self.lock:
            raw = self.vault.get("google")
            if not raw: raise ValueError("Google-account nog niet gekoppeld")
            data = json.loads(raw)
            if feature not in data["features"]: raise ValueError("Deze Google-toegang is niet verleend")
            if data["deadline"] <= self.store.clock():
                refreshed = await self._token({**self.config(), "refresh_token": data["refresh_token"], "grant_type": "refresh_token"})
                data.update(refreshed)
                data["deadline"] = self.store.clock()+int(refreshed.get("expires_in", 3600))-60
                self.vault.put("google", encode(data))
            return data["access_token"]

    def status(self):
        data = self.vault.get("google")
        return {"connected": bool(data), "features": json.loads(data)["features"] if data else []}

    async def disconnect(self):
        async with self.lock:
            raw = self.vault.get("google")
            if raw:
                response = await self.http.post("https://oauth2.googleapis.com/revoke", data={"token": json.loads(raw)["refresh_token"]})
                if response.status_code != 200: raise ValueError("Google kon intrekking niet bevestigen; probeer opnieuw of trek toegang in bij Google")
                self.vault.delete("google")
        return {"disconnected": True}

    async def api(self, feature, path, method="GET", *, params=None, body=None, etag=None):
        access = await self.access(feature)
        request_guard=REQUEST_GUARD.get()
        if request_guard is not None:request_guard()
        if method!="GET":
            guard=WRITE_GUARD.get()
            if guard is None: raise ValueError("Externe actie mist uitvoeringsautorisatie")
            guard()
        headers = {"Authorization": "Bearer "+access}
        if etag: headers["If-Match"] = etag
        response = await self.http.request(method, "https://www.googleapis.com"+path, params=params, json=body, headers=headers)
        if not 200 <= response.status_code < 300: raise ValueError("Google-verzoek niet bevestigd (controleer verbinding, rechten of gewijzigde afspraak)")
        if len(response.content) > 2_000_000: raise ValueError("Google-antwoord te groot")
        return response.json() if response.content else {}

    async def calendar_list(self):
        return await self.api("calendar_read", "/calendar/v3/users/me/calendarList", params={"maxResults":100})

    async def events(self, p):
        return await self.api("calendar_read", "/calendar/v3/calendars/"+quote(p["calendar_id"], safe="")+"/events", params={"timeMin":p["start"], "timeMax":p["end"], "q":p["query"], "singleEvents":"true", "orderBy":"startTime", "maxResults":100})

    async def change(self, tool, p, key):
        await self.access("calendar_read")
        await self.access("calendar_write")
        path = "/calendar/v3/calendars/"+quote(p["calendar_id"],safe="")+"/events"
        if tool != "CalendarCreate": path += "/"+quote(p["event_id"],safe="")
        body = {"summary":p["summary"], "start":{"dateTime":p["start"],"timeZone":p["timezone"]}, "end":{"dateTime":p["end"],"timeZone":p["timezone"]}, "location":p["location"], "attendees":[{"email":x} for x in p["attendees"]]}
        if p["recurrence"]: body["recurrence"] = p["recurrence"]
        if p.get('description') is not None:body['description']=p['description']
        if p.get("reminder_minutes") is not None:
            body["reminders"]={"useDefault":False,"overrides":[{"method":"popup","minutes":p["reminder_minutes"]}]}
        if tool == "CalendarCreate": body["id"] = "j"+hashlib.sha256(key.encode()).hexdigest()[:40]
        if tool == "CalendarUpdate":
            current = await self.api("calendar_read", path)
            if current.get("etag") != p["etag"]: raise ValueError("Afspraak gewijzigd; maak een nieuw voorstel")
            # PATCH preserves untouched fields (including attachments/conference
            # metadata), rather than rebuilding a partial event for PUT.
        method = {"CalendarCreate":"POST", "CalendarUpdate":"PATCH", "CalendarDelete":"DELETE"}[tool]
        result = await self.api("calendar_write", path, method, body=None if method=="DELETE" else body, etag=p["etag"] or None, params={"sendUpdates":"all"})
        if method == "DELETE":
            # A successful conditional DELETE is the provider's confirmation.
            return {"deleted":True, "event_id":p["event_id"]}
        verified = await self.api("calendar_read", "/calendar/v3/calendars/"+quote(p["calendar_id"],safe="")+"/events/"+quote(result["id"],safe=""))
        if verified.get("start",{}).get("dateTime") != result.get("start",{}).get("dateTime"): raise ValueError("Wijziging niet verifieerbaar")
        return verified

    async def mail_search(self, query):
        return await self.api("gmail_read", "/gmail/v1/users/me/messages", params={"q":query, "maxResults":30})

    async def mail_read(self, identifier, body=False):
        return await self.api("gmail_read", "/gmail/v1/users/me/messages/"+quote(identifier,safe=""), params={"format":"full" if body else "metadata", "metadataHeaders":["Subject","From","Date","List-Unsubscribe"]} if not body else {"format":"full"})

    async def draft(self, p):
        mail = EmailMessage(); mail["To"]=p["to"]; mail["Subject"]=p["subject"]; mail.set_content(p["text"])
        message = {"raw":base64.urlsafe_b64encode(mail.as_bytes()).decode()}
        if p["thread_id"]: message["threadId"]=p["thread_id"]
        result = await self.api("gmail_compose", "/gmail/v1/users/me/drafts", "POST", body={"message":message})
        snapshot = await self.api("gmail_compose", "/gmail/v1/users/me/drafts/"+quote(result["id"],safe=""), params={"format":"raw"})
        return {"draft_id":result["id"], "message_hash":fingerprint(snapshot["message"]),"preview":self.preview(snapshot["message"])}

    @staticmethod
    def preview(message):
        from email import policy
        from email.parser import BytesParser
        raw=message.get("raw","")
        parsed=BytesParser(policy=policy.default).parsebytes(base64.urlsafe_b64decode(raw+"="*((-len(raw))%4)))
        body=parsed.get_body(preferencelist=("plain",)) if parsed.is_multipart() else parsed
        if body is None or body.get_content_type()!="text/plain": raise ValueError("Alleen controleerbare tekstconcepten kunnen worden verzonden")
        if any(parsed.get_all(header,[]) for header in ("Bcc","Cc")): raise ValueError("Concept met Cc/Bcc vereist handmatige verzending")
        return "Aan: "+str(parsed.get("To",""))+"\nOnderwerp: "+str(parsed.get("Subject",""))+"\n\n"+body.get_content()

    async def send(self, p):
        await self.access("gmail_read")
        draft = await self.api("gmail_compose", "/gmail/v1/users/me/drafts/"+quote(p["draft_id"],safe=""), params={"format":"raw"})
        if fingerprint(draft["message"]) != p["message_hash"]: raise ValueError("Concept gewijzigd; nieuwe toestemming nodig")
        if self.preview(draft["message"]) != p["preview"]: raise ValueError("Conceptvoorbeeld komt niet overeen; nieuwe toestemming nodig")
        # Send the immutable reviewed bytes. A draft edited between GET and POST
        # must never substitute unreviewed recipients/content in the sent message.
        message={"raw":draft["message"]["raw"]}
        if draft["message"].get("threadId"): message["threadId"]=draft["message"]["threadId"]
        result = await self.api("gmail_compose", "/gmail/v1/users/me/messages/send", "POST", body=message)
        # Verify returned message through the read API, not an optimistic local flag.
        verified = await self.mail_read(result["id"])
        return {"id":verified["id"], "threadId":verified.get("threadId"), "verified":True,"draft_retained":True}
