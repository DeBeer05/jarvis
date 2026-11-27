"""Explicit local desktop requests; no planner/model round or generated code."""
import asyncio
import re

from server.natural.presence import address
from server.security.types import AuthError


class DesktopCommands:
    def __init__(self,natural):self.natural=natural

    def monitor(self):
        n=self.natural;e=n.automation;policy=e.windows.policy()
        if not policy.enabled or not policy.watch_downloads:return
        source=e.store.preference('windows_watch_owner','')
        try:
            e.permissions.check(source,'automation:read');e.permissions.check_tool(source,'DesktopRead')
            if 'DesktopRead' in e.store.preference('disabled_tools',[]):return
            changes=e.windows.changed_downloads()
        except (ValueError,OSError,AuthError):return
        if not changes:return
        target=policy.notify_device or source
        with e.store.db(True) as db:
            owner=db.execute('SELECT user_id FROM auth_devices WHERE id=? AND revoked_at IS NULL',(source,)).fetchone()
            if not owner:return
            device=db.execute('SELECT id FROM auth_devices WHERE id=? AND user_id=? AND trusted=1 AND revoked_at IS NULL',(target,owner['user_id'])).fetchone()
            if not device:return
            for item in changes:
                n.events.publish(db,owner['user_id'],target,'task.changed',{'text':'Downloadbestand nieuw of bijgewerkt: '+item['name'],'source':'windows_downloads'},'download:'+item['key'],lifetime=3600)

    def parse(self,message):
        text=message.strip().rstrip('.!?')
        text=re.sub(r'^(?:jarvis[, ]+)?(?:(?:kunt?|wilt?) (?:u|je) (?:voor mij )?)?','',text,flags=re.I)
        for pattern,action in ((r'vergrendel (?:mijn |de )?(?:pc|computer|windows)','lock'),(r'herstart (?:mijn |de )?(?:pc|computer)','restart'),(r'sluit (?:mijn |de )?(?:pc|computer) af','shutdown'),(r'zet (?:mijn |de )?(?:pc|computer) in (?:de )?slaapstand','sleep'),(r'annuleer (?:het )?afsluiten','cancel_shutdown'),(r'zet (?:het )?(?:volume|geluid) (?:hoger|harder)','volume_up'),(r'zet (?:het )?(?:volume|geluid) (?:lager|zachter)','volume_down'),(r'demp (?:het )?(?:volume|geluid)','mute'),(r'pauzeer (?:de )?(?:muziek|media)','pause'),(r'(?:speel|hervat) (?:de )?(?:muziek|media)','play'),(r'(?:speel )?(?:het )?volgende (?:nummer|liedje)','next'),(r'(?:speel )?(?:het )?vorige (?:nummer|liedje)','previous')):
            if re.fullmatch(pattern,text,re.I):return 'DesktopControl',{'action':action}
        if re.fullmatch(r'(?:toon|geef) (?:mijn |de )?(?:systeemstatus|systeeminformatie|cpu-?gebruik|ram-?gebruik)',text,re.I):return 'DesktopRead',{'kind':'status'}
        match=re.fullmatch(r'zoek (?:naar )?(?:het |een )?bestand (.+)',text,re.I)
        if match:return 'DesktopRead',{'kind':'files','query':match[1].strip('"“”')}
        match=re.fullmatch(r'open (?:het )?bestand (.+)',text,re.I)
        if match:return 'DesktopControl',{'action':'open_file','path':match[1].strip('"“”')}
        match=re.fullmatch(r'(open|start|sluit) (?:het programma |de app |programma )?(.+)',text,re.I)
        if match:
            names={name.casefold():name for name in self.natural.automation.windows.policy().programs}
            name=names.get(match[2].casefold())
            if name:return 'DesktopControl',{'action':'close_program' if match[1].casefold()=='sluit' else 'open_program','program':name}
        return None

    async def answer(self,run,request):
        n=self.natural;e=n.automation;tool,payload=request
        def guard():
            n.settings.get(run.principal)
            e.permissions.check(run.principal.device_id,'automation:read')
            e.permissions.check_tool(run.principal.device_id,tool)
            if tool in e.store.preference('disabled_tools',[]):raise ValueError('Actie uitgeschakeld')
        try:
            guard()
            e.windows.check()
            if tool=='DesktopControl':
                job=e.submit(run.principal.device_id,tool,payload,run.request_id)
                # Desktop approval remains in the existing exact-payload UI; no
                # model may infer approval or rebind an earlier calendar 'ja'.
                n.chat.automation_chat.remember(run,'pending',[])
                if job['status']=='approval':text='Ik heb het Windows-voorstel klaargezet. Controleer het bij Taken → Goedkeuringen.'
                else:text='Dit Windows-voorstel bestaat al. De actuele status staat bij Taken.'
            else:
                data=await asyncio.to_thread(e.windows.read,payload,guard);guard()
                if payload['kind']=='status':
                    available=data['ram_available']/1024**3;total=data['ram_total']/1024**3
                    cpu=str(data['cpu_percent'])+'%' if data['cpu_percent'] is not None else 'niet beschikbaar'
                    text=f'De Windows-server gebruikt {cpu} CPU. Er is {available:.1f} van {total:.1f} GB RAM beschikbaar.'
                    if data.get('gpu'):
                        text+=' GPU: '+', '.join(str(item['utilization'])+'%' if item['utilization'] is not None else 'niet beschikbaar' for item in data['gpu'][:2])+'.'
                        if data.get('temperature') is not None:text+=f" GPU-temperatuur: {data['temperature']} °C."
                else:
                    items=data['items'];text=('Gevonden bestanden:\n'+'\n'.join(item['path'] for item in items[:10])) if items else 'Ik vind geen passend document in de toegestane mappen.'
                    if data['truncated']:text+='\nDe zoekopdracht is begrensd; geef een specifiekere bestandsnaam.'
        except AuthError:text='Dit apparaat mist de vereiste Windows- of automatiseringsrechten.'
        except (ValueError,OSError):text='Windows-bediening is niet beschikbaar voor deze opdracht. Controleer de toegestane programma’s en documentmappen; ik heb geen uitvoering bevestigd.'
        return address(text,run.natural_context['settings'])
