const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
class Element {
 constructor(){this.value='';this.checked=false;this.textContent='';this.fields={};this.elements={namedItem:name=>this.fields[name]??(this.fields[name]=new Element())};this.fieldset={disabled:true};}
 addEventListener(){} querySelectorAll(){return [];} append(){} replaceChildren(){}
 querySelector(selector){assert.equal(selector,'fieldset');return this.fieldset;}
 set innerHTML(_){throw Error('No user text as HTML');}
}
const nodes={},element=id=>nodes[id]??(nodes[id]=new Element()),calls=[];
const policy={enabled:false,programs:{},roots:[],watch_downloads:false,media_allowed:false,programs_allowed:false,notify_device:''};let rejectResume=false;
const context={URLSearchParams,Intl,location:{search:''},document:{getElementById:element,createElement:()=>new Element()},
 JarvisAuth:{initialize:()=>new Promise(()=>{}),api:async(path,options={})=>{
  calls.push([path,options]);if(path.endsWith('/windows/policy'))return structuredClone(policy);
  if(path.endsWith('/safety') && JSON.parse(options.body).active===false && rejectResume)throw Error('Eigenaarrecht ontbreekt');return {};
 }}};
vm.createContext(context);vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),context);
(async()=>{
 assert.equal(calls.length,0,'Loading does not grant or execute anything');
 await element('host-load').onclick();const form=element('host-policy');assert.equal(form.fieldset.disabled,false);
 assert.equal(form.elements.namedItem('media_allowed').checked,false);
 form.elements.namedItem('programs').value='Kladblok = C:\\Windows\\System32\\notepad.exe';form.elements.namedItem('roots').value='C:\\Synthetic\\Documents';
 form.elements.namedItem('enabled').checked=true;form.onsubmit({preventDefault(){}});await new Promise(setImmediate);
 const data=JSON.parse(calls.find(([path])=>path.endsWith('/windows'))[1].body);
 assert.deepEqual(data.programs,{Kladblok:'C:\\Windows\\System32\\notepad.exe'});assert.equal(data.media_allowed,false);assert.equal(data.programs_allowed,false);
 await element('butler-stop').onclick();assert.match(element('butler-status').textContent,/Noodstop actief/);
 rejectResume=true;await element('butler-resume').onclick();assert.equal(element('butler-status').textContent,'Eigenaarrecht ontbreekt');
 console.log('Butler controls: explicit host edits, safe defaults and rejected resume passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
