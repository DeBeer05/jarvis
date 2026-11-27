"""Interactive hidden input; no API request, subscription or credit purchase."""
import getpass
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from server.voice_secrets import default_secret_path,save_secret


def main():
    if not sys.stdin.isatty():raise SystemExit('Open dit script in uw eigen terminal voor verborgen sleutelinvoer.')
    secret=getpass.getpass('ElevenLabs API-key (onzichtbaar, niet in chat plakken): ')
    destination=default_secret_path();save_secret(destination,secret)
    source=ROOT/'.env';content=source.read_text(encoding='utf-8') if source.exists() else ''
    if any(line.strip().startswith('ELEVENLABS_API_KEY=') for line in content.splitlines()):
        raise SystemExit('Er staat al ELEVENLABS_API_KEY in .env. De beveiligde sleutel is opgeslagen; verwijder de oude variabele zelf om het sleutelbestand te gebruiken.')
    lines=[line for line in content.splitlines() if not line.strip().startswith('ELEVENLABS_API_KEY_FILE=')]
    lines.append('ELEVENLABS_API_KEY_FILE='+json.dumps(str(destination).replace('\\','/')))
    source.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Sleutel beveiligd opgeslagen buiten het project. Herstart de backend om hem te laden. Geen credits verbruikt.')


if __name__=='__main__':main()
