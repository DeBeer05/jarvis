const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
class Element{
 constructor(){this.value='';this.children=[];this.listeners={};this.checked=false;this.fields={};}
 append(...items){this.children.push(...items);}
 replaceChildren(...items){this.children=[...items];this.value='';}
 addEventListener(event,fn){this.listeners[event]=fn;}
 querySelectorAll(){return [];}
 querySelector(selector){const name=selector.match(/name="([^"]+)"/)[1];return this.fields[name]??(this.fields[name]=new Element());}
 scrollIntoView(){}
 set innerHTML(_){throw Error('Device names must remain text');}
}
const nodes={},element=id=>nodes[id]??(nodes[id]=new Element()),fields={};
element('calendar').elements={namedItem:name=>fields[name]??(fields[name]=new Element())};
fields.calendar_id=element('calendar-choice');
const windows='11111111-1111-4111-8111-111111111111',android='22222222-2222-4222-8222-222222222222';
const devices=[{id:windows,name:'Windows <script>',type:'windows',trusted:1,permissions:[]},{id:android,name:'Mijn telefoon',type:'android',trusted:1,permissions:['automation:read']},{id:'owner',name:'Owner',type:'browser',trusted:1,permissions:[]},{id:'revoked',trusted:1,revoked_at:1,permissions:[]}];
const calls=[];
const context={URLSearchParams,Intl,location:{search:'',hash:'#device='+windows},confirm:()=>true,
 document:{getElementById:element,createElement:()=>new Element()},
 FormData:class{get(){return element('grant-device').value;}*keys(){yield 'device_id';for(const [name,field] of Object.entries(element('grant').fields))if(field.checked)yield name;}},
 JarvisAuth:{initialize:()=>new Promise(()=>{}),api:async(path,options={})=>{calls.push([path,options]);if(path==='/api/v1/devices')return {items:devices};if(path.endsWith('/grants')){const data=JSON.parse(options.body);devices.find(d=>d.id===data.device_id).permissions=data.scopes;return {updated:true};}return {};}}};
vm.createContext(context);vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),context);
(async()=>{
 vm.runInContext('grantPrincipal={device_id:"owner",permissions:["admin:devices"]}',context);
 await vm.runInContext('loadGrantDevices()',context);vm.runInContext('prepareDeviceGrant()',context);
 assert.equal(element('grant-device').children.length,3);
 assert.equal(element('grant-device').children[1].textContent,'Windows <script> · windows');
 assert.equal(element('grant-device').value,windows);
 assert(element('grant').fields['automation:write'].checked);
 assert.equal(calls.filter(([,o])=>o.method==='POST').length,0,'No grant just by opening a link');
 element('grant-device').value=android;element('grant-device').listeners.change();
 assert(element('grant').fields['automation:read'].checked);
 assert(!element('grant').fields['automation:write'].checked);
 element('grant').fields['automation:write'].checked=true;
 await element('grant').listeners.submit({preventDefault(){},target:element('grant')});
 const writes=calls.filter(([,o])=>o.method==='POST');assert.equal(writes.length,1);
 assert.equal(JSON.parse(writes[0][1].body).device_id,android);
 assert.deepEqual(JSON.parse(writes[0][1].body).scopes,['automation:read','automation:write']);
 assert(element('grant-status').textContent.includes('opgeslagen'));
 console.log('Windows / Android owner grants passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
