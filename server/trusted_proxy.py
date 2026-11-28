"""Opt-in one-hop HTTPS proxy; Uvicorn proxy_headers must remain disabled."""
import ipaddress
from urllib.parse import urlsplit
from starlette.responses import JSONResponse


class TrustedHTTPSProxy:
    def __init__(self,app,origin):self.app=app;self.origin=urlsplit(origin)
    async def __call__(self,scope,receive,send):
        if scope['type'] not in ('http','websocket'):return await self.app(scope,receive,send)
        raw_headers=scope.get('headers',[])
        headers=dict(raw_headers)
        if b'x-forwarded-proto' not in headers:return await self.app(scope,receive,send)
        try:
            for name in (b'host',b'x-forwarded-proto',b'x-forwarded-for'):
                if sum(key==name for key,value in raw_headers)!=1:raise ValueError()
            if not ipaddress.ip_address(scope['client'][0]).is_loopback:raise ValueError()
            if headers[b'x-forwarded-proto']!=b'https' or headers.get(b'host',b'').decode('ascii').lower()!=self.origin.netloc:raise ValueError()
            address=str(ipaddress.ip_address(headers[b'x-forwarded-for'].decode('ascii')))
            if scope['path']=='/internal' or scope['path'].startswith('/internal/'):raise ValueError()
        except (ValueError,KeyError,UnicodeError,TypeError):
            if scope['type']=='websocket':return await send({'type':'websocket.close','code':4403})
            return await JSONResponse({'error':{'code':'untrusted_proxy','message':'Gebruik de beveiligde JARVIS-hostnaam.'}},status_code=403)(scope,receive,send)
        scope={**scope,'scheme':'wss' if scope['type']=='websocket' else 'https','client':(address,0),'jarvis.trusted_https':True}
        return await self.app(scope,receive,send)
