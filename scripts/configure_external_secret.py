"""Hidden local input into the existing encrypted backend vault; no API calls."""
import argparse
import getpass
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from server.config import load_settings
from server.database import Database
from server.automation.store import Store
from server.automation.vault import SecretVault


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('service',choices=['home-assistant','openrouteservice'])
    args=parser.parse_args()
    if not sys.stdin.isatty():raise SystemExit('Gebruik uw eigen interactieve terminal voor verborgen invoer; plak geen sleutel in de chat.')
    settings=load_settings(root=ROOT);database=Database(settings.database_path)
    if not database.path.is_file():raise SystemExit('Start eerst uw geconfigureerde JARVIS-backend; dit script maakt geen nieuw account aan.')
    store=Store(database);vault=SecretVault(store,key_file=settings.vault_key_file)
    # No migration/installation or account operation from this configuration tool.
    if args.service=='home-assistant':
        from server.automation.external import HomePolicy
        policy=HomePolicy.model_validate(store.preference('home_assistant',{}))
        if not policy.endpoint:raise SystemExit('Stel eerst de HTTPS-basis-URL in de eigenaarinstellingen in.')
    secret=getpass.getpass('Toegangssleutel (onzichtbaar): ')
    if not 8<=len(secret)<=4096 or any(not 0x21<=ord(ch)<=0x7e for ch in secret):raise SystemExit('Ongeldige sleutel; niets opgeslagen.')
    if args.service=='home-assistant':
        vault.put('external:home_assistant',json.dumps({'endpoint':policy.endpoint,'token':secret}))
    else:vault.put('external:openrouteservice',secret)
    print('Sleutel versleuteld opgeslagen in de bestaande backend-vault. Geen netwerkverzoek, accountupgrade of proefactie uitgevoerd.')


if __name__=='__main__':main()
