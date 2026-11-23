"use strict";
const base="/api/v1/automation";
const el=id=>document.getElementById(id);
const api=(path="",method="GET",body)=>JarvisAuth.api(base+path,{method,...(body===undefined?{}:{headers:{"Content-Type":"application/json"},body:JSON.stringify(body)})});
const zone=Intl.DateTimeFormat().resolvedOptions().timeZone;
const googleOptions=new URLSearchParams(location.search);
for(const checkbox of el("oauth").querySelectorAll('input[type="checkbox"]')) {
 if(googleOptions.get("google")==="all" || googleOptions.get(checkbox.name)==="on") checkbox.checked=true;
}
const show=data=>{el("result").textContent=JSON.stringify(data,null,2);};
let calendarSequence=0;
const calendarField=name=>el("calendar").elements.namedItem(name);
function localDateTime(date) {
 const pad=value=>String(value).padStart(2,"0");
 return `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
function clearCalendarEvents() {calendarSequence++;el("calendar-events").replaceChildren();}
el("calendar-choice").addEventListener("change",()=>{clearCalendarEvents();el("calendar-status").textContent="Agenda geselecteerd. Klik op Afspraken zoeken om de afspraken te bekijken.";});
const calendarToday=new Date();calendarToday.setHours(0,0,0,0);
const calendarWeek=new Date(calendarToday);calendarWeek.setDate(calendarWeek.getDate()+7);
calendarField("start").value=localDateTime(calendarToday);calendarField("end").value=localDateTime(calendarWeek);
async function calendarRequest(loading,request,render) {
 clearCalendarEvents();const sequence=calendarSequence;
 el("calendar-status").textContent=loading;
 try {const data=await request();if(sequence===calendarSequence)render(data);}
 catch(error) {if(sequence===calendarSequence){el("calendar-status").textContent=error.message;throw error;}}
}
function renderCalendars(data) {
 const selected=calendarField("calendar_id").value,items=data.items||[];
 el("calendar-choice").replaceChildren();
 for(const calendar of items) {
  const option=document.createElement("option");option.value=calendar.id;
  option.textContent=(calendar.summaryOverride||calendar.summary||"Naamloze agenda")+(calendar.primary?" (hoofdagenda)":"");
  el("calendar-choice").append(option);
 }
 if(items.some(calendar=>calendar.id===selected))calendarField("calendar_id").value=selected;
 else {const primary=items.find(calendar=>calendar.primary);if(primary)calendarField("calendar_id").value=primary.id;}
 el("calendar-status").textContent=items.length?`${items.length} agenda’s opgehaald. Kies hierboven je agenda en klik op Afspraken zoeken.`:"Geen agenda’s gevonden voor dit Google-account.";
 if(data.nextPageToken)el("calendar-status").textContent+=" Niet alle agenda’s worden getoond.";
}
function eventMoment(value) {
 if(!value)return "Onbekend tijdstip";
 const date=new Date(value.dateTime||`${value.date}T12:00:00`);
 if(Number.isNaN(date.getTime()))return "Onbekend tijdstip";
 return new Intl.DateTimeFormat("nl-NL",value.dateTime?{dateStyle:"medium",timeStyle:"short"}:{dateStyle:"long"}).format(date);
}
function renderCalendarEvents(data) {
 const items=data.items||[];
 for(const event of items) {
  const card=document.createElement("section"),title=document.createElement("h3"),time=document.createElement("p");
  title.textContent=event.summary||"Afspraak zonder titel";
  if(event.start?.date) {
   let range=eventMoment(event.start);
   if(event.end?.date){const last=new Date(`${event.end.date}T12:00:00`);last.setDate(last.getDate()-1);const inclusive=localDateTime(last).split("T")[0];if(inclusive>event.start.date)range+=` – ${eventMoment({date:inclusive})}`;}
   time.textContent=`${range} · Hele dag`;
  } else time.textContent=`${eventMoment(event.start)} – ${eventMoment(event.end)}`;
  card.append(title,time);
  if(event.location){const location=document.createElement("p");location.textContent=event.location;card.append(location);}
  el("calendar-events").append(card);
 }
 el("calendar-status").textContent=items.length?`${items.length} afspraken gevonden. Tijden worden getoond in ${zone}.`:"Geen afspraken gevonden in de gekozen agenda en periode.";
 if(data.nextPageToken)el("calendar-status").textContent+=" Er zijn meer resultaten. Kies een kortere periode of gebruik een zoekterm.";
}
let emailSequence=0;
const messageField=name=>el("message").elements.namedItem(name);
function mailHeaders(message) {
 const headers=Object.create(null);for(const header of message.payload?.headers||[])headers[header.name.toLowerCase()]=header.value;
 return headers;
}
function mailTextPart(part) {
 if(!part)return "";
 if(part.mimeType==="text/plain" && part.body?.data) {
  try {const raw=atob(part.body.data.replace(/-/g,"+").replace(/_/g,"/"));return new TextDecoder().decode(Uint8Array.from(raw,char=>char.charCodeAt(0)));}
  catch{return "Berichttekst kon niet worden gelezen.";}
 }
 const values=(part.parts||[]).map(mailTextPart).filter(Boolean);
 // Prefer the readable plain-text alternative; never execute received markup.
 return part.mimeType==="multipart/alternative"?(values[0]||""):values.join("\n\n");
}
function renderMail(message,includeBody) {
 const headers=mailHeaders(message),panel=el("email-message");panel.replaceChildren();
 const title=document.createElement("h3");title.textContent=headers.subject||"Bericht zonder onderwerp";panel.append(title);
 for(const [label,value] of [["Van",headers.from],["Aan",headers.to],["Datum",headers.date]]) {
  if(value){const text=document.createElement("p");text.textContent=`${label}: ${value}`;panel.append(text);}
 }
 const text=document.createElement("p");
 text.textContent=includeBody?(mailTextPart(message.payload)||("Dit bericht heeft geen gewone tekstversie. "+(message.snippet?"Korte weergave: "+message.snippet+". ":"")+"Open het bericht in Gmail voor de volledige opmaak.")):"Alleen berichtgegevens geladen. Vink Inhoud lezen aan en open het bericht opnieuw om de tekst te bekijken.";
 text.style.whiteSpace="pre-wrap";panel.append(text);
}
async function openMail(id,includeBody) {
 const sequence=++emailSequence;el("email-message").replaceChildren();el("email-status").textContent="Bericht ophalen…";
 messageField("id").value=id;el("email-reopen").disabled=false;
 try {const data=await api("/email/"+encodeURIComponent(id)+"?include_body="+includeBody);if(sequence===emailSequence){renderMail(data,includeBody);el("email-status").textContent="Bericht geopend.";}}
 catch(error){if(sequence===emailSequence){el("email-status").textContent=error.message;throw error;}}
}
async function searchMail(query) {
 const sequence=++emailSequence;el("email-results").replaceChildren();el("email-message").replaceChildren();messageField("id").value="";el("email-reopen").disabled=true;el("email-status").textContent="E-mail zoeken…";
 try {
  const data=await api("/email/search","POST",{query}),items=(data.messages||[]).slice(0,10);
  if(sequence!==emailSequence)return;
  for(let start=0;start<items.length;start+=5) {
   const batch=items.slice(start,start+5);
   const results=await Promise.allSettled(batch.map(item=>api("/email/"+encodeURIComponent(item.id))));
   if(sequence!==emailSequence)return;
   for(let index=0;index<batch.length;index++) {
    const result=results[index],headers=result.status==="fulfilled"?mailHeaders(result.value):{};
    const card=document.createElement("section"),title=document.createElement("h3"),from=document.createElement("p"),button=document.createElement("button");
    title.textContent=headers.subject||(result.status==="fulfilled"?"Bericht zonder onderwerp":"Berichtgegevens niet beschikbaar");from.textContent=headers.from||"Onbekende afzender";
    button.type="button";button.textContent="Bericht openen";button.onclick=run(()=>openMail(batch[index].id,messageField("body").checked));
    card.append(title,from,button);el("email-results").append(card);
   }
  }
  el("email-status").textContent=items.length?`${items.length} berichten getoond. Kies Bericht openen om een bericht te bekijken.`:"Geen berichten gevonden voor deze zoekopdracht.";
  if(data.nextPageToken||(data.messages||[]).length>10)el("email-status").textContent+=" Er zijn meer resultaten. Verfijn je zoekopdracht.";
 }catch(error){if(sequence===emailSequence){el("email-status").textContent=error.message;throw error;}}
}
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
bind("calendar",async f=>calendarRequest("Afspraken ophalen…",()=>api("/calendar/search","POST",{calendar_id:f.get("calendar_id"),start:new Date(f.get("start")).toISOString(),end:new Date(f.get("end")).toISOString(),query:f.get("query")}),renderCalendarEvents));
bind("mail",async f=>searchMail(f.get("query")));
bind("message",async f=>openMail(f.get("id"),f.has("body")));
bind("plan",async f=>{const p=await api("/plan","POST",{instruction:f.get("instruction")});show(p);if(p.tool){el("tool-name").value=p.tool;el("tool-input").value=JSON.stringify(p.input,null,2);}});
bind("tool",async f=>{const input=JSON.parse(f.get("input"));if(!confirm("Deze actie indienen?\n"+f.get("tool")+"\n"+JSON.stringify(input,null,2)))return;show(await submit(f.get("tool"),input,{repeat:f.get("repeat"),timezone:zone,...(f.get("due")?{due:new Date(f.get("due")).toISOString()}:{})}));await refresh();});
bind("policy",async f=>{await api("/notifications","PUT",{quiet_start:Number(f.get("quiet_start")),quiet_end:Number(f.get("quiet_end")),max_hour:Number(f.get("max_hour")),timezone:zone,categories:["urgent","appointments","important","news"]});await refresh();});
bind("oauth",async f=>{const result=await api("/integrations/google","POST",{features:[...f.keys()]});const url=new URL(result.authorization_url);if(url.origin!=="https://accounts.google.com")throw Error("Ongeldige autorisatielink");el("oauth-link").href=url.href;el("oauth-link").hidden=false;});
bind("grant",async f=>{
 const id=f.get("device_id"),device=grantDevices.find(item=>item.id===id);
 if(!device)throw Error("Kies eerst een gekoppeld Windows- of Android-apparaat.");
 const scopes=[...f.keys()].filter(x=>x!=="device_id");
 if(confirm(`Rechten wijzigen voor ${device.name} (${device.type})?\n${scopes.join(", ")||"Alle automatiseringsrechten verwijderen"}`)){
  await api("/grants","POST",{device_id:id,scopes});await loadGrantDevices(id);
  el("grant-status").textContent="Rechten opgeslagen. Kies in de app Rechten vernieuwen of wacht op de sessiecontrole. Op Android kun je Automatiseringen opnieuw openen.";
 }
});
el("refresh").onclick=run(refresh);
el("calendars").onclick=run(async()=>calendarRequest("Agenda’s ophalen…",()=>api("/calendar/calendars"),renderCalendars));
el("disconnect").onclick=run(async()=>{if(confirm("Google-toegang intrekken?"))show(await api("/integrations/google","DELETE"));});
let grantDevices=[],grantPrincipal=null;
const grantScopes=["automation:read","automation:write","automation:approve","integrations:manage"];
function selectedGrantDevice(){
 const device=grantDevices.find(item=>item.id===el("grant-device").value);
 for(const scope of grantScopes)el("grant").querySelector(`[name="${scope}"]`).checked=!!device?.permissions?.includes(scope);
 el("grant-status").textContent=device?`${device.name} · ${device.type} · ${device.id}`:"Kies een gekoppeld apparaat.";
}
async function loadGrantDevices(selected=el("grant-device").value){
 if(!grantPrincipal?.permissions?.includes("admin:devices")){el("grant-status").textContent="Alleen de eigenaar kan apparaatrechten instellen.";return;}
 const data=await JarvisAuth.api("/api/v1/devices");
 grantDevices=(data.items||[]).filter(item=>!item.revoked_at&&item.trusted&&item.id!==grantPrincipal.device_id);
 const choice=el("grant-device");choice.replaceChildren();
 const empty=document.createElement("option");empty.value="";empty.textContent="Kies Windows of Android";choice.append(empty);
 for(const device of grantDevices){const option=document.createElement("option");option.value=device.id;option.textContent=`${device.name} · ${device.type}`;choice.append(option);}
 choice.value=grantDevices.some(item=>item.id===selected)?selected:"";selectedGrantDevice();
 if(!grantDevices.length)el("grant-status").textContent="Nog geen gekoppelde apps gevonden. Log eerst in op Windows of koppel Android via Apparaten.";
}
el("grant-device").addEventListener("change",selectedGrantDevice);
el("grant-refresh").onclick=run(()=>loadGrantDevices());
function prepareDeviceGrant(){
 const parameters=new URLSearchParams((location.hash||"").slice(1)),id=parameters.get("device");
 if(!id||!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id))return;
 if(!grantDevices.some(item=>item.id===id)){el("grant-status").textContent="Dit apparaat is niet gekoppeld of is ingetrokken. Kies een geldig apparaat uit de lijst.";return;}
 const form=el("grant");el("grant-device").value=id;selectedGrantDevice();
 form.querySelector('[name="automation:read"]').checked=true;
 form.querySelector('[name="automation:write"]').checked=true;
 form.scrollIntoView({block:"center"});
 el("grant-status").textContent="Apparaat geselecteerd. Controleer de rechten en klik zelf op Rechten instellen. Er zijn nog geen rechten gewijzigd.";
}
JarvisAuth.initialize().then(async principal=>{grantPrincipal=principal;await refresh();await loadGrantDevices();prepareDeviceGrant();}).catch(error=>{el("status").textContent=error.message;});
