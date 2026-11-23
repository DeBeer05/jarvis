const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
class Element {
 constructor(){this.children=[];this.listeners={};this.value='';this.textContent='';}
 append(...items){this.children.push(...items);if(this.children.length===1 && !this.value)this.value=items[0].value;}
 replaceChildren(...items){this.children=[...items];this.value='';}
 addEventListener(event,fn){this.listeners[event]=fn;}
 querySelectorAll(){return [];}
 set innerHTML(_){throw Error('Untrusted calendar data must not become HTML');}
}
const nodes={},fields={};
const element=id=>nodes[id]??(nodes[id]=new Element());
element('calendar').elements={namedItem:name=>fields[name]??(fields[name]=new Element())};
fields.calendar_id=element('calendar-choice');fields.calendar_id.value='primary';
element('result').textContent='Existing action proposal';
let answer={items:[]},failure=null,calls=[];
const context={URLSearchParams,Intl,location:{search:''},FormData:class {constructor(form){this.form=form;}get(key){return this.form.elements.namedItem(key).value;}},
 document:{getElementById:element,createElement:()=>new Element()},
 JarvisAuth:{initialize:()=>new Promise(()=>{}),api:async(path,options)=>{calls.push([path,options]);if(failure)throw Error(failure);return answer;}}};
vm.createContext(context);vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),context);
async function search(){await element('calendar').listeners.submit({preventDefault(){},target:element('calendar')});}
(async()=>{
 assert(fields.start.value && fields.end.value,'Useful default date range');
 answer={items:[{id:'primary-id',summary:'Mijn agenda',primary:true},{id:'other-id',summary:'<script>do not run</script>'}]};
 await element('calendars').onclick();
 assert.equal(element('calendar-choice').children.length,2);
 assert.equal(element('calendar-choice').value,'primary-id');
 assert.equal(element('calendar-choice').children[1].textContent,'<script>do not run</script>');
 assert(element('calendar-status').textContent.includes('2 agenda’s'));
 element('calendar-choice').value='other-id';element('calendar-choice').listeners.change();
 answer={items:[{summary:'<img onerror=bad()>',start:{dateTime:'2026-11-25T10:00:00+01:00'},end:{dateTime:'2026-11-25T11:00:00+01:00'},location:'Testlocatie'},{summary:'Vrij',start:{date:'2026-11-26'},end:{date:'2026-11-27'}}],nextPageToken:'synthetic'};
 await search();
 assert.equal(JSON.parse(calls.at(-1)[1].body).calendar_id,'other-id');
 assert.equal(element('calendar-events').children.length,2);
 assert.equal(element('calendar-events').children[0].children[0].textContent,'<img onerror=bad()>');
 assert(element('calendar-events').children[1].children[1].textContent.includes('Hele dag'));
 assert(element('calendar-status').textContent.includes('meer resultaten'));
 assert.equal(element('result').textContent,'Existing action proposal');
 answer={items:[]};await search();assert(element('calendar-status').textContent.includes('Geen afspraken'));
 failure='Google niet beschikbaar';await element('calendars').onclick();assert.equal(element('calendar-status').textContent,failure);assert.equal(element('status').textContent,failure);failure=null;
 let release;context.JarvisAuth.api=()=>new Promise(resolve=>{release=resolve;});
 const pending=search();element('calendar-choice').listeners.change();
 release({items:[{summary:'Stale result'}]});await pending;
 assert.equal(element('calendar-events').children.length,0,'Old result cannot reappear after calendar change');
 console.log('Calendar UI behavior passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
