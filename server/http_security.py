"""Bound request bodies before JSON decoding; reject cross-origin browser writes."""
from urllib.parse import urlsplit

from starlette.responses import JSONResponse
from starlette.datastructures import MutableHeaders


class SecurityHeaders:
    """Keep receive/disconnect intact; response headers need no BaseHTTP bridge."""
    def __init__(self,app):self.app=app

    async def __call__(self,scope,receive,send):
        if scope["type"]!="http":return await self.app(scope,receive,send)
        async def guarded_send(message):
            if message["type"]=="http.response.start":
                headers=MutableHeaders(scope=message)
                headers["X-Content-Type-Options"]="nosniff"
                headers["Referrer-Policy"]="no-referrer"
                headers["Content-Security-Policy"]="default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
                headers["Cache-Control"]="no-store"
            await send(message)
        await self.app(scope,receive,guarded_send)


class RequestGuard:
    def __init__(self, app, port: int, allowed_origins=None):
        self.app, self.port = app, port
        self.allowed_origins = tuple(allowed_origins or (f"http://127.0.0.1:{port}", f"http://localhost:{port}"))

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        writing = scope["method"] in ("POST", "PUT", "PATCH", "DELETE")
        oauth_callback = scope["path"] == "/oauth/google/callback" and scope["method"] == "GET"
        if headers.get(b"sec-fetch-site") == b"cross-site" and not oauth_callback:
            return await JSONResponse({"error": {"code": "origin_forbidden", "message": "Gebruik de eigen lokale JARVIS-pagina."}}, status_code=403)(scope, receive, send)
        if (writing or scope["path"] == "/api/v1/auth/csrf") and b"origin" in headers:
            try:
                origin = urlsplit(headers[b"origin"].decode("ascii"))
                allowed = headers[b"origin"].decode("ascii") in self.allowed_origins and not origin.username and not origin.path and not origin.query and not origin.fragment
            except (ValueError, UnicodeError):
                allowed = False
            if not allowed:
                return await JSONResponse({"error": {"code": "origin_forbidden", "message": "Alleen dezelfde lokale webchat mag dit verzoek doen."}}, status_code=403)(scope, receive, send)
        if writing:
            audio = scope["path"] == "/api/v1/mobile/speech/transcribe" and scope["method"] == "POST"
            image = scope['path']=='/api/v1/natural/vision' and scope['method']=='POST'
            accepted = (b"audio/wav",) if audio else (b"application/json", b"")
            if scope["path"].startswith("/api/") and scope["method"] != "DELETE" and headers.get(b"content-type", b"").split(b";")[0].strip().lower() not in accepted:
                return await JSONResponse({"error": {"code": "invalid_content_type", "message": "Gebruik JSON voor dit verzoek."}}, status_code=415)(scope, receive, send)
            content = bytearray()
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                piece = message.get("body", b"")
                if len(content) + len(piece) > (2_000_000 if audio else 2_450_000 if image else 65536):
                    return await JSONResponse({"error": {"code": "body_too_large", "message": "Het verzoek is te groot."}}, status_code=413)(scope, receive, send)
                content.extend(piece)
                if not message.get("more_body", False):
                    break
            replayed = False

            async def replay():
                nonlocal replayed
                if not replayed:
                    replayed = True
                    return {"type": "http.request", "body": bytes(content), "more_body": False}
                return await receive()

            return await self.app(scope, replay, send)
        return await self.app(scope, receive, send)
