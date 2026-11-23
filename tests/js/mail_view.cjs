const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
class Element {
 constructor(){this.children=[];this.listeners={};this.value='';this.checked=false;this.textContent='';this.style={};}
 append(...items){this.children.push(...items);}
 replaceChildren(...items){this.children=[...items];}
 addEventListener(event,fn){this.listeners[event]=fn;}
 querySelectorAll(){return [];}
 set innerHTML(_){throw Error('Untrusted mail must never become HTML');}
}
const nodes={},fields={},messageFields={};const element=id=>nodes[id]??(nodes[id]=new Element());
element('calendar').elements={namedItem:name=>fields[name]??(fields[name]=new Element())};
element('message').elements={namedItem:name=>messageFields[name]??(messageFields[name]=new Element())};
element('result').textContent='Action proposal stays here';
const headers=[{name:'Subject',value:'<script>subject</script>'},{name:'From',value:'Synthetic sender <example@example.com>'},{name:'Date',value:'Test date'}];
let answer={messages:[{id:'example1'},{id:'example2'}]},calls=[];
const context={URLSearchParams,Intl,TextDecoder,atob,location:{search:''},FormData:class {constructor(form){this.form=form;}get(key){return key==='query'?'in:inbox':this.form.elements.namedItem(key).value;}has(key){return !!this.form.elements.namedItem(key).checked;}},
 document:{getElementById:element,createElement:()=>new Element()},
 JarvisAuth:{initialize:()=>new Promise(()=>{}),api:async(path,options)=>{calls.push([path,options]);return path.endsWith('/search')?answer:{id:'example1',payload:{headers}};}}};
vm.createContext(context);vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),context);
async function search(){await element('mail').listeners.submit({preventDefault(){},target:element('mail')});}
(async()=>{
 await search();assert.equal(element('email-results').children.length,2);
 assert.equal(element('email-results').children[0].children[0].textContent,'<script>subject</script>');
 assert.equal(element('email-results').children[0].children[1].textContent,'Synthetic sender <example@example.com>');
 await element('email-results').children[0].children[2].onclick();
 assert(calls.at(-1)[0].endsWith('?include_body=false'));
 assert(element('email-message').children.at(-1).textContent.includes('Alleen berichtgegevens'));
 assert.equal(element('result').textContent,'Action proposal stays here');
 context.JarvisAuth.api=async()=>({payload:{headers,mimeType:'multipart/alternative',parts:[{mimeType:'text/plain',body:{data:Buffer.from('Hallo café 😊\n<img src=tracking onerror=bad()>').toString('base64url')}},{mimeType:'text/html',body:{data:Buffer.from('<script>bad()</script>').toString('base64url')}}]}});
 messageFields.body.checked=true;await element('message').listeners.submit({preventDefault(){},target:element('message')});
 assert.equal(element('email-message').children.at(-1).textContent,'Hallo café 😊\n<img src=tracking onerror=bad()>');
 context.JarvisAuth.api=async()=>{throw Error('Mail niet beschikbaar');};await search();assert.equal(element('email-status').textContent,'Mail niet beschikbaar');
 context.JarvisAuth.api=async()=>({messages:[]});await search();assert(element('email-status').textContent.includes('Geen berichten'));
 let release;context.JarvisAuth.api=()=>new Promise(resolve=>{release=resolve;});
 const old=search();context.JarvisAuth.api=async()=>({messages:[]});await search();release({messages:[{id:'old'}]});await old;
 assert.equal(element('email-results').children.length,0);
 const lifecycle={};const authContext={window:{},addEventListener:(event,fn)=>{lifecycle[event]=fn;},document:{getElementById:element,querySelectorAll:()=>[]}};
 vm.createContext(authContext);vm.runInContext(fs.readFileSync(require('node:path').join(require('node:path').dirname(process.argv[2]),'auth.js'),'utf8'),authContext);
 for(const id of ['email-message','email-results','calendar-events'])element(id).append(new Element());
 lifecycle.pagehide();
 for(const id of ['email-message','email-results','calendar-events'])assert.equal(element(id).children.length,0,'Private views clear when leaving the page');
 console.log('Email UI behavior passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
