"""Synchronous network core; called only on workers, never the GUI thread."""
import base64
import hashlib
import json
import re
import secrets
import threading
import time
from uuid import uuid4

import httpx

from jarvis_client.settings import endpoint


class ClientError(Exception):
    def __init__(self, code, message, status=0):
        super().__init__(message)
        self.code, self.status = code, status


def challenge(verifier):
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")


class ApiClient:
    def __init__(self, origin, vault, *, transport=None, clock=time.monotonic):
        self.origin, self.vault, self.clock = endpoint(origin), vault, clock
        self.http = httpx.Client(base_url=self.origin, verify=True, trust_env=False, follow_redirects=False,
                                 transport=transport, timeout=httpx.Timeout(15, connect=4), headers={"Accept": "application/json"})
        self.lock = threading.RLock()
        self.access = None
        self.deadline = 0
        self.principal = None
        self.pairing = None
        self.cancelled = threading.Event()
        self.closed = False

    def _network(self, method, path, **kwargs):
        try:
            response = self.http.request(method, path, **kwargs)
        except (httpx.ConnectError, httpx.ConnectTimeout):
            raise ClientError("network_before_send", "Server niet bereikbaar of TLS-certificaat ongeldig. Je opgeslagen sessie blijft behouden.") from None
        except httpx.TransportError:
            raise ClientError("network", "Server niet bereikbaar of TLS-certificaat ongeldig. Controleer het serveradres.") from None
        return self._decode(response)

    @staticmethod
    def _decode(response):
        if response.is_redirect:
            raise ClientError("redirect", "De server verwijst naar een ander adres. Controleer het profiel.")
        if len(response.content) > 2_000_000:
            raise ClientError("invalid_response", "Het serverantwoord is te groot.")
        try:
            body = response.json()
        except ValueError:
            raise ClientError("invalid_response", "De server stuurde geen geldig JARVIS-antwoord.") from None
        if not response.is_success:
            code = body.get("error", {}).get("code", "request_failed") if isinstance(body, dict) else "request_failed"
            expired_message = "De koppelcode is verlopen. Start opnieuw."
            messages = {"authorization_pending": "Wacht op jouw goedkeuring in de browser.", "slow_down": "Even wachten voor de volgende koppelcontrole.",
                        "expired_token": expired_message, "access_denied": "Deze koppeling is geweigerd.",
                        "invalid_grant": "De koppeling is ongeldig of al gebruikt.", "permission_denied": "Dit apparaat heeft hiervoor geen toestemming.",
                        "rate_limited": "Te veel verzoeken. Probeer later opnieuw.", "authentication_required": "Je sessie is verlopen of ingetrokken. Log opnieuw in."}
            messages["invalid_credentials"] = "Inloggen mislukt. Controleer je gebruikersnaam en wachtwoord."
            raise ClientError(code, messages.get(code, "Het verzoek is niet gelukt. Controleer je verbinding en rechten."), response.status_code)
        if not isinstance(body, dict):
            raise ClientError("invalid_response", "Onverwacht serverantwoord.")
        return body

    def probe(self):
        body = self._network("GET", "/health")
        if body.get("service") != "jarvis-server" or body.get("status") != "ok":
            raise ClientError("identity", "Dit endpoint identificeert zich niet als JARVIS.")
        return body

    def _install(self, credentials):
        if self.closed:
            raise ClientError("closed", "De verbinding is afgesloten.")
        access, refresh = credentials.get("access_token"), credentials.get("refresh_token")
        if credentials.get("token_type") != "Bearer" or not isinstance(access, str) or not 32 <= len(access) <= 128 or not isinstance(refresh, str) or not 32 <= len(refresh) <= 128:
            raise ClientError("invalid_response", "Ongeldige sessie ontvangen.")
        self.vault.save(self.origin, refresh)
        self.access = access
        self.deadline = self.clock() + min(max(int(credentials.get("expires_in", 0)), 0), 900)

    def headers(self):
        with self.lock:
            if self.closed:
                raise ClientError("closed", "De verbinding is afgesloten.")
            if not self.access or self.deadline - self.clock() < 40:
                refresh = self.vault.load(self.origin)
                if not refresh:
                    raise ClientError("authentication_required", "Log in met je gebruikersnaam en wachtwoord.", 401)
                # Remove the old durable token before rotation. A crash/ambiguous failure
                # must cause re-pairing, never replay of a possibly consumed token.
                self.vault.delete(self.origin)
                self.access, self.principal = None, None
                try:
                    self._install(self._network("POST", "/api/v1/auth/token", json={"refresh_token": refresh}))
                except ClientError as error:
                    if error.code == "network_before_send":
                        # No request reached the server: the old token was not consumed.
                        self.vault.save(self.origin, refresh)
                        raise
                    raise ClientError("authentication_required", "Sessievernieuwing niet bevestigd. Log opnieuw in.", 401) from None
                except Exception:
                    raise ClientError("authentication_required", "Sessievernieuwing niet bevestigd. Log opnieuw in.", 401) from None
            return {"Authorization": "Bearer " + self.access}

    def request(self, method, path, body=None):
        mail_body = re.fullmatch(r"/api/v1/automation/email/[A-Za-z0-9_-]+\?include_body=true", path)
        if not path.startswith("/api/v1/") or "?" in path and not (path.startswith("/api/v1/chat/conversations?") or mail_body):
            raise ValueError("Invalid API path")
        try:
            return self._network(method, path, headers=self.headers(), **({"json": body} if body is not None else {}))
        except ClientError as error:
            if error.status == 401:
                self.forget()
            raise

    def session(self):
        self.principal = self.request("GET", "/api/v1/auth/session")
        return self.principal

    def login(self, username, password, name, device_id):
        with self.lock:
            if self.closed:
                raise ClientError("closed", "De verbinding is afgesloten.")
            credentials = self._network("POST", "/api/v1/auth/desktop-login", json={
                "username": username, "password": password, "device_name": name, "device_id": device_id,
            })
            self._install(credentials)
            return self.session()

    def begin_pair(self, name, delete=False):
        with self.lock:
            if self.access or self.vault.load(self.origin):
                raise ClientError("already_paired", "Log eerst uit voordat je opnieuw koppelt.")
            verifier = secrets.token_urlsafe(32)
            scopes = ["chat:read", "chat:write", "status:read"] + (["chat:delete"] if delete else [])
            result = self._network("POST", "/api/v1/pairing/requests", json={"device_name": name, "device_type": "windows", "scopes": scopes,
                                    "code_challenge": challenge(verifier), "code_challenge_method": "S256"})
            self.pairing = {"secret": result["device_code"], "verifier": verifier, "deadline": self.clock() + result["expires_in"], "interval": result["interval"], "next": self.clock() + result["interval"]}
            return {"user_code": result["user_code"], "expires_in": result["expires_in"], "verification_uri": self.origin + "/security"}

    def poll_pair(self):
        with self.lock:
            item = self.pairing
            if not item or self.clock() >= item["deadline"]:
                self.pairing = None
                raise ClientError("expired_token", "De koppelcode is verlopen. Start opnieuw.")
            if self.clock() < item["next"]:
                return {"pending": True}
            item["next"] = self.clock() + item["interval"]
            try:
                result = self._network("POST", "/api/v1/pairing/token", json={"grant_type": "urn:ietf:params:oauth:grant-type:device_code", "device_code": item["secret"], "code_verifier": item["verifier"]})
            except ClientError as error:
                if error.code in ("slow_down", "authorization_pending"):
                    if error.code == "slow_down":
                        item["interval"] = min(30, item["interval"] + 5)
                        item["next"] = self.clock() + item["interval"]
                    return {"pending": True}
                if error.code != "network":
                    self.pairing = None
                raise
            self.pairing = None
            self._install(result)
            return self.session()

    def forget(self):
        with self.lock:
            self.access, self.principal, self.pairing = None, None, None
            self.vault.delete(self.origin)

    def logout(self, revoke_device=False):
        try:
            return self.request("POST", "/api/v1/auth/disconnect" if revoke_device else "/api/v1/auth/logout")
        finally:
            self.forget()

    def stream(self, message, conversation, provider, emit, request_id=None, *,channel="text",session_epoch=None):
        self.cancelled.clear()
        body = {"message": message, "provider": provider, "request_id": request_id or str(uuid4())}
        if channel!="text":body["channel"]=channel
        if session_epoch is not None:body["session_epoch"]=session_epoch
        if conversation:
            body["conversation_id"] = conversation
        headers = self.headers()
        final, size = False, 0
        try:
            with self.http.stream("POST", "/api/v1/chat/stream", headers=headers, json=body, timeout=httpx.Timeout(75, connect=4)) as response:
                if not response.is_success:
                    response.read()
                    self._decode(response)
                for line in response.iter_lines():
                    if self.cancelled.is_set():
                        raise ClientError("cancelled", "Antwoord gestopt; herlaad het gesprek voor de opgeslagen status.")
                    size += len(line)
                    if size > 1_000_000 or len(line) > 200_000:
                        raise ClientError("invalid_response", "De stream is te groot.")
                    if line.startswith("data: "):
                        event = json.loads(line[6:])
                        if not isinstance(event, dict) or "type" not in event:
                            raise ValueError
                        emit(event)
                        if event["type"] == "done":
                            final = True
                            if (event.get("error") or {}).get("code") == "authentication_expired":
                                raise ClientError("authentication_required", "Je sessie is ingetrokken. Log opnieuw in.", 401)
                if not final:
                    raise ClientError("incomplete", "De verbinding stopte vóór het antwoord compleet was. Herlaad de historie; het bericht is niet opnieuw verstuurd.")
        except httpx.TransportError:
            raise ClientError("network", "Verbinding tijdens antwoord verloren. Herlaad de historie; het bericht is niet opnieuw verstuurd.") from None
        except (ValueError, TypeError):
            raise ClientError("invalid_response", "Ongeldig streamantwoord.") from None
        except ClientError as error:
            if error.status == 401:
                self.forget()
            raise
        return {"completed": final}

    def close(self):
        self.closed = True
        self.pairing = None
        self.access = None
        self.cancelled.set()
        self.http.close()
