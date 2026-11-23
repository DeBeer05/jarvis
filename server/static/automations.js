"use strict";
const base="/api/v1/automation";
const el=id=>document.getElementById(id);
const api=(path="",method="GET",body)=>JarvisAuth.api(base+path,{method,...(body===undefined?{}:{headers:{"Content-Type":"application/json"},body:JSON.stringify(body)})});
const zone=Intl.DateTimeFormat().resolvedOptions().timeZone;
const show=data=>{el("result").textContent=JSON.stringify(data,null,2);};
const run=fn=>async event=>{event?.preventDefault();try{await fn(event);el("status").textContent="Bijgewerkt.";}catch(error){el("status").textContent=error.message;}};
const bind=(id,fn)=>el(id).addEventListener("submit",run(event=>fn(new FormData(event.target))));
async function refresh(){
 const data=await api();el("jobs").replaceChildren();
 for(const job of data.items){
  const section=document.createElement("section"),title=document.createElement("h3"),detail=document.createElement("pre");title.textContent=job.tool+" · "+job.status;detail.textContent=JSON.stringify(job.payload,null,2);section.append(title,detail);
  const action=(text,fn)=>{const b=document.createElement("button");b.textContent=text;b.onclick=run(async()=>{await fn();await refresh();});section.append(b);};
  if(job.status==="approval")for(const approve of [true,false])action(approve?"Gevolgen goedkeuren":"Weigeren",async()=>{if(!confirm((approve?"Deze exacte actie goedkeuren?\n":"Deze actie weigeren?\n")+detail.textContent))return;const challenge=await api(`/jobs/${job.id}/challenge`,"POST");await api(`/jobs/${job.id}/decision`,"POST",{token:challenge.token,approve});});
  if(["queued","waiting","approval","paused","blocked"].includes(job.status))action("Annuleren",()=>api(`/jobs/${job.id}/control`,"POST",{status:"cancelled"}));
  if(job.status==="queued")action("Pauzeren",()=>api(`/jobs/${job.id}/control`,"POST",{status:"paused"}));
  if(job.status==="paused")action("Hervatten",()=>api(`/jobs/${job.id}/control`,"POST",{status:"queued"}));
  el("jobs").append(section);
 }
 el("history").textContent=JSON.stringify(data.history,null,2);
 el("notifications").replaceChildren(...data.notifications.map(n=>{const p=document.createElement("p");p.textContent=n.category+": "+n.text;return p;}));
 if(!el("tool-name").options.length)for(const name of data.tools){const option=document.createElement("option");option.textContent=name;el("tool-name").append(option);}
}
const submit=(tool,input,extra={})=>api("/jobs","POST",{tool,input,idempotency_key:crypto.randomUUID(),...extra});
bind("reminder",async f=>{await submit("ReminderCreate",{text:f.get("text"),at:new Date(f.get("at")).toISOString(),repeat:f.get("repeat"),timezone:zone});await refresh();});
bind("calendar",async f=>show(await api("/calendar/search","POST",{calendar_id:f.get("calendar_id"),start:new Date(f.get("start")).toISOString(),end:new Date(f.get("end")).toISOString(),query:f.get("query")})));
bind("mail",async f=>show(await api("/email/search","POST",{query:f.get("query")})));
bind("message",async f=>show(await api("/email/"+encodeURIComponent(f.get("id"))+"?include_body="+f.has("body"))));
bind("plan",async f=>{const p=await api("/plan","POST",{instruction:f.get("instruction")});show(p);if(p.tool){el("tool-name").value=p.tool;el("tool-input").value=JSON.stringify(p.input,null,2);}});
bind("tool",async f=>{const input=JSON.parse(f.get("input"));if(!confirm("Deze actie indienen?\n"+f.get("tool")+"\n"+JSON.stringify(input,null,2)))return;show(await submit(f.get("tool"),input,{repeat:f.get("repeat"),timezone:zone,...(f.get("due")?{due:new Date(f.get("due")).toISOString()}:{})}));await refresh();});
bind("policy",async f=>{await api("/notifications","PUT",{quiet_start:Number(f.get("quiet_start")),quiet_end:Number(f.get("quiet_end")),max_hour:Number(f.get("max_hour")),timezone:zone,categories:["urgent","appointments","important","news"]});await refresh();});
bind("oauth",async f=>{const result=await api("/integrations/google","POST",{features:[...f.keys()]});const url=new URL(result.authorization_url);if(url.origin!=="https://accounts.google.com")throw Error("Ongeldige autorisatielink");el("oauth-link").href=url.href;el("oauth-link").hidden=false;});
bind("grant",async f=>{if(confirm("Deze rechten aan dit apparaat verlenen?"))await api("/grants","POST",{device_id:f.get("device_id"),scopes:[...f.keys()].filter(x=>x!=="device_id")});});
el("refresh").onclick=run(refresh);
el("calendars").onclick=run(async()=>show(await api("/calendar/calendars")));
el("disconnect").onclick=run(async()=>{if(confirm("Google-toegang intrekken?"))show(await api("/integrations/google","DELETE"));});
JarvisAuth.initialize().then(refresh).catch(error=>{el("status").textContent=error.message;});
