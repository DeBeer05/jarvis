"""Bound request bodies before JSON decoding; reject cross-origin browser writes."""
from urllib.parse import urlsplit

from starlette.responses import JSONResponse


class RequestGuard:
    def __init__(self, app, port: int):
        self.app, self.port = app, port

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        writing = scope["method"] in ("POST", "PUT", "PATCH", "DELETE")
        if writing and b"origin" in headers:
            try:
                origin = urlsplit(headers[b"origin"].decode("ascii"))
                allowed = origin.scheme == "http" and origin.hostname in ("127.0.0.1", "localhost") and (origin.port or 80) == self.port and not origin.username and not origin.path and not origin.query and not origin.fragment
            except (ValueError, UnicodeError):
                allowed = False
            if not allowed:
                return await JSONResponse({"error": {"code": "origin_forbidden", "message": "Alleen dezelfde lokale webchat mag dit verzoek doen."}}, status_code=403)(scope, receive, send)
        if writing:
            content = bytearray()
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                content.extend(message.get("body", b""))
                if len(content) > 65536:
                    return await JSONResponse({"error": {"code": "body_too_large", "message": "Het verzoek is te groot."}}, status_code=413)(scope, receive, send)
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
