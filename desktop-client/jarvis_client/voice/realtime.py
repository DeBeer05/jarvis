"""Persistent authenticated STT transport; transcripts never submit a chat turn."""
import asyncio
import json


class RealtimeSpeech:
    def __init__(self,api):self.api=api;self.socket=None

    async def close(self):
        socket,self.socket=self.socket,None
        if socket:await socket.close()

    async def transcribe(self,audio):
        from websockets.asyncio.client import connect
        try:
            if self.socket is None:
                headers=await asyncio.to_thread(self.api.headers)
                origin=self.api.origin
                url=('wss'+origin[5:] if origin.startswith('https:') else 'ws'+origin[4:])+'/api/v1/realtime'
                self.socket=await connect(url,additional_headers=headers,proxy=None,compression=None,max_size=65536,max_queue=4,open_timeout=4,close_timeout=2,ping_interval=20,ping_timeout=20)
                if json.loads(await self.socket.recv()).get('type')!='ready':raise ValueError('Realtimeverbinding geweigerd')
            await self.socket.send(json.dumps({'type':'audio.start'}))
            if json.loads(await self.socket.recv()).get('type')!='audio.ready':raise ValueError('Opname niet gereed')
            for offset in range(0,len(audio),32768):await self.socket.send(audio[offset:offset+32768])
            await self.socket.send(json.dumps({'type':'audio.commit'}))
            result=json.loads(await self.socket.recv())
            if result.get('type')!='transcript' or not result.get('final'):raise ValueError('Geen definitief transcript')
            return json.dumps(result).encode()
        except BaseException:
            await self.close();raise
