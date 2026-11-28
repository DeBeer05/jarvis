"""Explicit Home Assistant commands from owner-defined names, without a classifier."""
import re
import httpx

from server.natural.presence import address
from server.security.types import AuthError


class EnvironmentCommands:
    def __init__(self,natural):self.natural=natural

    def parse(self,message):
        text=message.strip().rstrip('.!?')
        text=re.sub(r'^(?:jarvis[, ]+)?(?:(?:kunt?|wilt?) (?:u|je) (?:voor mij )?)?','',text,flags=re.I)
        match=re.fullmatch(r'(?:(?:zet|doe|schakel) )?(.+?) (aan|uit)(?:\s*(?:zetten|schakelen))?',text,re.I)
        action=None;value=None
        if match:name=match[1];action='on' if match[2].casefold()=='aan' else 'off'
        else:
            match=re.fullmatch(r'stel (.+?) in op (\d+(?:[.,]\d+)?)\s*(?:graden)?',text,re.I)
            if match:name=match[1];action='temperature';value=float(match[2].replace(',','.'))
            else:
                match=re.fullmatch(r'(?:start|activeer) (.+)',text,re.I)
                if match:name=match[1];action='routine'
                else:
                    match=re.fullmatch(r'(?:toon|wat is de status van|hoe staat) (.+)',text,re.I)
                    if not match:return None
                    name=match[1]
        names={name.casefold():entity for name,entity in self.natural.automation.external.home_policy().aliases.items()}
        entity=names.get(name.casefold()) or names.get(re.sub(r'^(?:de|het|mijn)\s+','',name.casefold()))
        if not entity:
            if re.search(r'\b(?:lamp|licht|thermostaat|home assistant)\b',name,re.I):return {'missing':True}
            return None
        if action is None:return {'tool':'HomeRead','input':{'entity_id':entity}}
        if action=='routine':
            if entity.startswith('scene.'):action='scene'
            elif entity.startswith(('light.','switch.')):action='on'
            elif not entity.startswith('automation.'):return {'missing':True}
        payload:dict={'entity_id':entity,'action':action}
        if value is not None:payload['temperature']=value
        return {'tool':'HomeControl','input':payload}

    async def answer(self,run,command):
        n=self.natural;e=n.automation;settings=run.natural_context['settings']
        if command.get('missing'):
            text='Welke ingestelde lamp of thermostaat bedoelt u? Controleer de namen bij Integraties.' if e.external.home_policy().enabled else 'Home Assistant is nog niet gekoppeld. Er is geen wijziging uitgevoerd.'
            return address(text,settings)
        tool=command['tool'];payload=command['input']
        def guard():
            n.settings.get(run.principal);e.permissions.check(run.principal.device_id,'automation:read');e.permissions.check_tool(run.principal.device_id,tool)
            if tool in e.store.preference('disabled_tools',[]):raise ValueError('Actie uitgeschakeld')
        try:
            guard();await e.external.home_headers(e.external.home_policy());guard()
            if tool=='HomeControl':
                job=e.submit(run.principal.device_id,tool,payload,run.request_id)
                n.chat.automation_chat.remember(run,'pending',[])
                text='Het Home Assistant-voorstel staat bij Taken → Goedkeuringen.' if job['status']=='approval' else 'Dit voorstel bestaat al; de actuele status staat bij Taken.'
            else:
                state=await e.external.home_state(payload['entity_id'],guard);guard()
                names=e.external.home_policy().aliases;name=next((name for name,entity in names.items() if entity==payload['entity_id']),payload['entity_id'])
                value={'on':'aan','off':'uit','unavailable':'niet beschikbaar','unknown':'onbekend'}.get(state['state'],state['state'])
                text=f'Home Assistant meldt voor {name}: {value}.'
        except AuthError:text='Dit apparaat heeft geen geldige rechten voor deze functie.'
        except (ValueError,OSError,httpx.HTTPError):text='Home Assistant is nog niet beschikbaar voor deze opdracht. Ik heb geen wijziging bevestigd.'
        return address(text,settings)
