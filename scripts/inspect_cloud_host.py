"""Read-only host inspection, suitable for piping to python3 over trusted SSH."""
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import urllib.request


def command(args):
    try:
        result=subprocess.run(args,capture_output=True,text=True,timeout=8,check=False)
        return {'returncode':result.returncode,'output':result.stdout[:14000],'error_type':'command_failed' if result.returncode else None}
    except (OSError,subprocess.TimeoutExpired) as error:return {'error_type':type(error).__name__}


def main():
    info={'architecture':platform.machine(),'kernel':platform.release(),'cpu_count':os.cpu_count(),
          'os':Path('/etc/os-release').read_text(),'python':platform.python_version(),
          'memory':{},'root_disk':dict(zip(('total','used','free'),shutil.disk_usage('/'))),
          'software':{name:bool(shutil.which(name)) for name in ('python3','git','docker','ollama','caddy','nginx','openssl','systemctl')},
          'ports':command(['ss','-lntup']),'swap':command(['swapon','--show']),
          'firewall':command(['sudo','-n','ufw','status','verbose']),
          'iptables':command(['sudo','-n','iptables','-S']),
          'available_updates':command(['apt','list','--upgradable'])}
    for line in Path('/proc/meminfo').read_text().splitlines():
        name,value=line.split(':',1)
        if name in ('MemTotal','MemAvailable','SwapTotal','SwapFree'):info['memory'][name]=value.strip()
    ssh=command(['sudo','-n','sshd','-T'])
    info['ssh']={'returncode':ssh.get('returncode'),'selected_settings':[line for line in ssh.get('output','').splitlines() if line.split(' ',1)[0] in ('passwordauthentication','permitrootlogin','pubkeyauthentication','kbdinteractiveauthentication','x11forwarding')]}
    try:
        request=urllib.request.Request('http://169.254.169.254/opc/v2/instance/',headers={'Authorization':'Bearer Oracle'})
        with urllib.request.urlopen(request,timeout=3) as response:metadata=json.load(response)
        info['oci']={key:metadata.get(key) for key in ('shape','shapeConfig','canonicalRegionName','region')}
    except Exception as error:info['oci']={'error_type':type(error).__name__}
    print(json.dumps(info,indent=2))


if __name__=='__main__':main()
