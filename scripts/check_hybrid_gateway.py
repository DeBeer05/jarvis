"""Explicit public gateway probe with a disposable database and synthetic account."""
import argparse,json,os,secrets,subprocess,tempfile,time
from pathlib import Path
import httpx

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-live',action='store_true');parser.add_argument('--origin',required=True);parser.add_argument('--release',required=True,type=Path);parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
    if not args.run_live or not args.origin.startswith('https://'):parser.error('Explicit HTTPS live probe required')
    release=args.release.resolve();python=release/'.venv/Scripts/python.exe';host=httpx.URL(args.origin).host
    with tempfile.TemporaryDirectory(prefix='jarvis-gateway-probe-') as temporary:
        root=Path(temporary);env=os.environ.copy();env.update(JARVIS_PROFILE='mini-pc-production',JARVIS_PORT='18766',JARVIS_PUBLIC_ORIGIN=args.origin,JARVIS_TRUSTED_HOSTS='127.0.0.1,localhost,'+host,JARVIS_ALLOWED_ORIGINS=args.origin,JARVIS_DATABASE_PATH=str(root/'test.sqlite3'),JARVIS_RUNTIME_DIR=str(root/'run'),JARVIS_LOG_PATH=str(root/'server.log'),JARVIS_ENABLE_AUTOMATIONS='false',JARVIS_AI_PREFERRED_PROVIDER='oracle',JARVIS_PROVIDER_TIMEOUT_SECONDS='90',JARVIS_AI_TIMEOUT_SECONDS='120',JARVIS_AI_MAX_OUTPUT_TOKENS='128',JARVIS_TEST_PASSWORD=secrets.token_urlsafe(24))
        initialize="import os; from server.config import load_settings; from server.database import Database; from server.security.service import SecurityService; s=load_settings(); d=Database(s.database_path); d.initialize(); SecurityService(d,s).setup_owner('synthetic',os.environ['JARVIS_TEST_PASSWORD'])"
        subprocess.run([str(python),'-c',initialize],cwd=release,env=env,check=True,capture_output=True)
        process=subprocess.Popen([str(python),'-m','server','--no-console'],cwd=release,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        checks={}
        try:
            with httpx.Client(base_url=args.origin,timeout=130,trust_env=False,headers={'Origin':args.origin}) as client:
                for attempt in range(30):
                    if process.poll() is not None:raise RuntimeError('Disposable server failed to start')
                    try:
                        if client.get('/ready',timeout=3).status_code==200:break
                    except httpx.HTTPError:pass
                    time.sleep(1)
                else:raise RuntimeError('Gateway not connected to disposable server')
                checks['tls_validated']=True;checks['unauthenticated_denied']=client.get('/api/v1/status').status_code==401
                checks['internal_control_hidden']=client.get('/internal/status').status_code==404
                client.get('/api/v1/auth/csrf').raise_for_status()
                response=client.post('/api/v1/auth/login',json={'username':'synthetic','password':env['JARVIS_TEST_PASSWORD']},headers={'X-Jarvis-CSRF':client.cookies.get('jarvis_csrf','')});response.raise_for_status()
                checks['authenticated_login']=True
                checks['secure_cookie']=all(cookie.secure for cookie in client.cookies.jar if cookie.name in ('jarvis_access','jarvis_refresh'))
                client.headers['X-Jarvis-CSRF']=client.cookies.get('jarvis_csrf','')
                started=time.perf_counter();first=None;events=[]
                with client.stream('POST','/api/v1/chat/stream',json={'message':'Zeg alleen een korte Nederlandse begroeting.','provider':'oracle'}) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if line.startswith('data: '):
                            event=json.loads(line[6:]);events.append(event)
                            if event.get('type')=='delta' and first is None:first=time.perf_counter()-started
                done=next(event for event in reversed(events) if event.get('type')=='done')
                checks['oracle_stream_completed']=done['status']=='completed' and bool(done['message'])
                checks['first_answer_seconds']=first;checks['total_seconds']=time.perf_counter()-started
                checks['synthetic_response']=done['message']
                checks['personal_database_used']=False
                if not all(checks[key] for key in ('unauthenticated_denied','internal_control_hidden','authenticated_login','secure_cookie','oracle_stream_completed')):raise RuntimeError('Gateway acceptance failed')
        finally:
            subprocess.run([str(python),'-m','server','stop','--wait','10'],cwd=release,env=env,capture_output=True)
            try:process.communicate(timeout=15)
            except subprocess.TimeoutExpired:process.kill();process.communicate()
        args.output.write_text(json.dumps(checks,indent=2),encoding='utf-8');print(json.dumps(checks))

if __name__=='__main__':main()
