const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const c={};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../extension/flow-controls.js'),'utf8'),c);const f=c.FruchtFlow;
for(const name of ['Gemini Omni 1.2 Flash','Omni 1.2 Flash','Gemini Omni Flash 1.2'])assert.ok(f.modelPattern('gemini_omni_flash').test(name));
for(const name of ['Gemini Omni Flash','Gemini Omni Flash 1.1','Gemini Omni 1.1 Flash','Omni Flash 1.20'])assert.ok(!f.modelPattern('gemini_omni_flash').test(name));
assert.ok(!f.modelPattern('gemini_omni_flash').test('Veo 3.1 Fast'));
assert.ok(!f.modelPattern('gemini_omni_flash').test('Veo 3.1 Lite'));
for(const text of ['Video · 720p · 8 Sek. · 1-mal','Vidéo · 720p · 8 s · x1','Video · 720p · 8 seconds · x1']){assert.equal(f.resolution(text),'720p');assert.equal(f.seconds(text),8);}
assert.equal(f.resolution('360p 720p'),null);assert.equal(f.seconds('8 s 10 s'),null);
function fixture({missing=false,ambiguous=false,wrongResolution=false,wrongDuration=false,target="Gemini Omni 1.2 Flash",aspect='9:16'}={}){
 let menu=false,current='Veo 3.1 - Lite',resolution=wrongResolution?'360p':'720p',seconds=wrongDuration?10:8,picked=[];
 const element=(text,click,checked=true)=>({innerText:text,getClientRects:()=>[{}],getAttribute:k=>k==='aria-checked'?String(checked):null,click});
 const radios=['Video',aspect,'x1'].map(x=>element(x,()=>picked.push(x)));
 const settings=element('',()=>{});settings.getAttribute=k=>k==='aria-label'?'Settings trigger':null;
 Object.defineProperty(settings,'innerText',{get:()=>`Video · ${resolution} · ${seconds} s · x1`});
 const model=element('',()=>menu=true);Object.defineProperty(model,'innerText',{get:()=>current});
 const option=element(target,()=>{current=target;menu=false;picked.push('omni');});
 const res=element('720p',()=>{resolution='720p';picked.push('720p');});
 const dur=element('8 s',()=>{seconds=8;picked.push('8s');});
 const doc={body:{innerText:'Generation will use 12 credits'},querySelectorAll:q=>{
  if(q==='[role="radio"]')return radios;
  if(q==='[role="combobox"]')return [model];
  if(q==='[role="option"],[role="menuitem"]')return menu&&!missing?(ambiguous?[option,{...option}]:[option]):[];
  if(q==='[role="radio"],[role="option"],[role="menuitem"],button')return [...radios,res,dur];
  if(q==='[aria-checked="true"],[aria-selected="true"]')return radios;
  return [settings,model];
 }};
 return {doc,picked,model};
}
(async()=>{
 // New Flow controls use a labelled button rather than a value-only combobox.
 for(const label of ['Videoauflösung','Résolution','Video resolution']){
  let open=false,value='720p',picked=0;
  const el=(text,attrs,click)=>({innerText:text,getAttribute:k=>attrs[k]||null,click,getClientRects:()=>[{}]});
  const header=el('',{'aria-label':'Settings trigger'},()=>{});
  Object.defineProperty(header,'innerText',{get:()=>`Video · ${value} · 8 s · x1`});
  const trigger=el('720p',{'aria-label':label,'aria-haspopup':'menu'},()=>open=true);
  const option=el('1080p',{'role':'option'},()=>{value='1080p';picked++;open=false;});
  const doc={querySelectorAll:q=>q==='[aria-checked="true"],[aria-selected="true"]'?[]:q==='[role="radio"],[role="option"],[role="menuitem"],button'?(open?[option]:[header,trigger]):[header,trigger,...(open?[option]:[])]};
  await f.chooseSetting(doc,async()=>{},'1080p','resolution');assert.equal(picked,1);assert.equal(value,'1080p');
 }
 // Real Flow label (03/11/2026): "Avertissement de crédits insuffisants" must stop before any send.
 {const el=t=>({innerText:'',getAttribute:k=>k==='aria-label'?t:null,getClientRects:()=>[{}]});const d=labels=>({querySelectorAll:()=>labels.map(el)});
  f.visible=()=>true;assert.ok(f.creditBlocked(d(['Avertissement de crédits insuffisants'])));assert.ok(f.creditBlocked(d(['Warnung: Nicht genügend Guthaben'])));assert.ok(!f.creditBlocked(d(['Ingrédient image','Effacer le prompt'])));}
 // Horizontal 16:9 version: the 16:9 radio is chosen and verified; a vertical-only page refuses.
 {const h=fixture({aspect:'16:9'});await f.configure(h.doc,async()=>{},12,'gemini_omni_flash','720p',8,'16:9');f.verifyModel(h.doc,'gemini_omni_flash','720p',8,'16:9');
  assert.throws(()=>f.verifyModel(h.doc,'gemini_omni_flash','720p',8),/format vertical non confirmé/);
  await assert.rejects(()=>f.configure(fixture().doc,async()=>{},12,'gemini_omni_flash','720p',8,'16:9'),/non reconnu/);}
 for(const [model,label,cost] of [['veo_3_1_fast','Veo 3.1 - Fast',20],['veo_3_1_quality','Veo 3.1 - Quality',100],['veo_3_1_quality','Veo 3.1 - Qualität',100]]){
  const x=fixture({target:label});await f.configure(x.doc,async()=>{},cost,model,'720p',8);f.verifyModel(x.doc,model,'720p',8);assert.throws(()=>f.verifyModel(x.doc,'veo_3_1_lite','720p',8),/modèle demandé/);
 }
 for(const language of ['Generation will use 12 credits','La génération utilisera 12 crédits','Für die Generierung werden 12 Guthabenpunkte verwendet']){
  const x=fixture({wrongResolution:true,wrongDuration:true});x.doc.body.innerText=language;
  await f.configure(x.doc,async()=>{},12,'gemini_omni_flash','720p',8);
  assert.deepEqual(x.picked,['omni','720p','8s']);assert.equal(f.cost(language),12);
  f.verifyModel(x.doc,'gemini_omni_flash','720p',8);
  assert.throws(()=>f.verifyModel(x.doc,'veo_3_1_lite','720p',8),/modèle demandé/);
 }
 for(const mode of [{missing:true},{ambiguous:true}])await assert.rejects(()=>f.configure(fixture(mode).doc,async()=>{},12,'gemini_omni_flash','720p',8),/indisponible ou ambigu/);
 const x=fixture();await f.configure(x.doc,async()=>{},12,'gemini_omni_flash','720p',8);const n=x.picked.length;
 await f.configure(x.doc,async()=>{},12,'gemini_omni_flash','720p',8);assert.equal(x.picked.length,n,'No repeated model selection when already correct');
 console.log('Omni: model selection, no Fast/Lite confusion, 720p, 8s, cost FR/DE/EN, idempotence and missing/ambiguous model guarded. No generation submitted.');
})().catch(e=>{console.error(e);process.exitCode=1;});
