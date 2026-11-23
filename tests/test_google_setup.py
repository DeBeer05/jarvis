import json
from pathlib import Path
import re
import os
import subprocess
import shutil

import pytest

from scripts.configure_google import configure
from tests.test_security import make_app, client_for


def client_file(tmp_path, name="download.json", client="example"):
    path=tmp_path/name
    path.write_text(json.dumps({"installed":{"client_id":client+".apps.googleusercontent.com","client_secret":"example-client-secret"}}),encoding="utf-8")
    return path


def test_google_setup_preserves_other_env_and_existing_client(tmp_path):
    root=tmp_path/"project";root.mkdir()
    (root/".env").write_bytes(b'# Keep comment\r\nOTHER_SETTING=keep_me\r\nJARVIS_ENABLE_AUTOMATIONS=false\r\n')
    one=configure(root,client_file(tmp_path))
    original=one.read_bytes()
    assert one==root/"secrets/google-desktop.json"
    text=(root/".env").read_text()
    assert "OTHER_SETTING=keep_me" in text and "# Keep comment" in text
    assert "JARVIS_GOOGLE_CLIENT_FILE=secrets/google-desktop.json" in text
    assert "JARVIS_ENABLE_AUTOMATIONS=true" in text
    two=configure(root,client_file(tmp_path,"another.json","different-example"))
    assert two!=one and one.read_bytes()==original
    assert configure(root,tmp_path/"another.json")==two


def test_invalid_web_client_changes_nothing(tmp_path):
    source=tmp_path/"wrong.json";source.write_text('{"web":{}}')
    root=tmp_path/"project";root.mkdir()
    with pytest.raises(ValueError):configure(root,source)
    assert not (root/"secrets").exists() and not (root/".env").exists()


def test_check_only_has_no_side_effects_and_bad_env_is_preserved(tmp_path):
    root=tmp_path/"project";root.mkdir();source=client_file(tmp_path)
    assert configure(root,source,check_only=True) is None
    assert not list(root.iterdir())
    broken='KEY="unclosed\n';(root/".env").write_text(broken)
    with pytest.raises(ValueError):configure(root,source)
    assert (root/".env").read_text()==broken and not (root/"secrets").exists()


def test_every_automation_page_script_is_served_as_javascript(settings):
    app=make_app(settings)
    with client_for(app) as client:
        html=client.get("/automations").text
        scripts=re.findall(r'<script[^>]+src="([^"]+)"',html)
        assert "/chat/assets/automations.js" in scripts
        for path in scripts:
            response=client.get(path)
            assert response.status_code==200
            assert "javascript" in response.headers["content-type"]
            assert response.headers["x-content-type-options"]=="nosniff"
        assert client.get("/chat/assets/unknown.js").status_code==401
        assert client.get("/api/v1/automation").status_code==401


@pytest.mark.skipif(os.name!="nt",reason="Windows PowerShell helper")
def test_powershell_check_only_accepts_a_path_with_spaces(tmp_path):
    source=client_file(tmp_path,"download with spaces.json")
    script=Path(__file__).resolve().parents[1]/"scripts/Connect-Google.ps1"
    result=subprocess.run(["powershell.exe","-NoProfile","-File",str(script),"-ClientFile",str(source),"-CheckOnly"],capture_output=True,text=True,timeout=15)
    assert result.returncode==0
    assert "example-client-secret" not in result.stdout+result.stderr


@pytest.mark.skipif(not shutil.which("node"),reason="Optional JavaScript runtime")
def test_google_selection_and_login_return_allowlist():
    root=Path(__file__).resolve().parents[1]
    code=r'''
const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const scripts=process.argv[1];
for(const destination of ['/automations?google=all#oauth','https://other.example/','//other.example/','javascript:alert(1)']) {
 const context={sessionStorage:{getItem:key=>key==='jarvis_after_login'?destination:null,removeItem:()=>{}},document:{getElementById:()=>({addEventListener:()=>{}})},fetch:()=>new Promise(()=>{}),JarvisAuth:{csrf:()=>''}};
 vm.createContext(context);vm.runInContext(fs.readFileSync(scripts+'/login.js','utf8'),context);
 assert.equal(vm.runInContext('loginDestination()',context),destination==='/automations?google=all#oauth'?destination:'/chat');
}
const checks=['calendar_read','calendar_write','gmail_read','gmail_compose'].map(name=>({name,checked:false}));
const elements={},fields={};const context={URLSearchParams,Intl,location:{search:'?google=all'},document:{getElementById:id=>elements[id]??(elements[id]={addEventListener:()=>{},querySelectorAll:()=>checks,elements:{namedItem:name=>fields[name]??(fields[name]={value:''})}})},JarvisAuth:{initialize:()=>new Promise(()=>{})}};
vm.createContext(context);vm.runInContext(fs.readFileSync(scripts+'/automations.js','utf8'),context);
assert(checks.every(item=>item.checked));
'''
    result=subprocess.run([shutil.which("node"),"-e",code,str(root/"server/static")],capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr


@pytest.mark.skipif(not shutil.which("node"),reason="Optional JavaScript runtime")
def test_calendar_results_stay_in_calendar_panel():
    root=Path(__file__).resolve().parents[1]
    result=subprocess.run([shutil.which("node"),str(root/"tests/js/calendar_view.cjs"),str(root/"server/static/automations.js")],capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr
