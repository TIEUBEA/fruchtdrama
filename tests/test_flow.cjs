const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const context={};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../extension/flow-controls.js'),'utf8'),context);const flow=context.FruchtFlow;
assert.equal(flow.cost('Für die Generierung werden 10 Guthabenpunkte verwendet'),10);
assert.equal(flow.cost('Für die Generierung werden 100 Guthabenpunkte verwendet'),100);
assert.equal(flow.cost('La génération utilisera 10 crédits'),10);
assert.equal(flow.cost('Generation will use 20 credits'),20);
assert.equal(flow.cost('50 Guthabenpunkte verbleibend'),null,'A balance is not a generation cost');
assert.equal(flow.cost('will use 10 credits. costs 20 credits'),null,'Conflicting costs must not be accepted');
assert.equal(flow.count('Video · 720p · 8 Sek. · 1-mal'),1);
assert.equal(flow.count('Video · 720p · 8 Sek. · 2-mal'),2);
assert.equal(flow.count('Video · x1'),1);
console.log('9 contrôles Flow réussis, dont le libellé exact de la capture allemande.');
const frSettings={innerText:'',getAttribute:key=>key==='aria-label'?'Déclencheur des paramètres':null,getClientRects:()=>[{}]};
const selectedOutput=n=>({innerText:'x'+n,getAttribute:()=>null,getClientRects:()=>[{}]});
const frDoc={querySelectorAll:selector=>selector.startsWith('button')?[frSettings]:[selectedOutput(1)]};
assert.equal(flow.settingsButton(frDoc),frSettings);
assert.equal(flow.outputCount(frDoc,frSettings),1);
assert.equal(flow.outputCount({querySelectorAll:()=>[selectedOutput(2)]},frSettings),2);
assert.equal(flow.outputCount({querySelectorAll:()=>[]},frSettings),null);
assert.equal(flow.outputCount({querySelectorAll:()=>[selectedOutput(1),selectedOutput(2)]},frSettings),null);
assert.equal(flow.outputCount(frDoc,{innerText:'Video · 720p · 8 Sek. · 1-mal'}),1);
console.log('6 contrôles des paramètres français : bouton accessible, sortie sélectionnée, x2, valeur absente et ambiguïté.');
async function automaticSettings(){
 for(const language of ['Vidéo','Video','videocam\nVidéo']){
  let opened=false;const picked=[];
  const radio=label=>({innerText:label,getClientRects:()=>[{}],getAttribute:key=>key==='aria-checked'?'false':null,click:()=>picked.push(label)});
  const settings={...frSettings,click:()=>opened=true};
  const radios=[radio(language),radio('9:16'),radio('x1')];
  const doc={body:{innerText:'La génération utilisera 10 crédits'},querySelectorAll:selector=>selector.includes('role="radio"')?(opened?radios:[]):[settings]};
  await flow.configure(doc,async()=>{},10);assert.deepEqual(picked,[language,'9:16','x1']);
 }
 console.log('Configuration automatique vidéo / 9:16 / x1 vérifiée sans clic de génération.');
}
automaticSettings().catch(e=>{console.error(e);process.exitCode=1;});
const editor={getBoundingClientRect:()=>({left:500,right:1200,top:400,bottom:900})};
const arrow={innerText:'arrow_forward',getAttribute:()=>null,getClientRects:()=>[{}],getBoundingClientRect:()=>({left:1190,right:1230,top:920,bottom:960,width:40,height:40})};
let sendButtons=[arrow];const flowDoc={location:{hostname:'flow.google.com'},querySelectorAll:()=>sendButtons};
assert.equal(flow.sendButton(flowDoc,editor),arrow);
arrow.disabled=true;assert.equal(flow.sendButton(flowDoc,editor),null);arrow.disabled=false;
sendButtons=[arrow,{...arrow}];assert.equal(flow.sendButton(flowDoc,editor),null,'Ambiguous arrows must not be clicked');
sendButtons=[arrow];assert.equal(flow.sendButton({...flowDoc,location:{hostname:'chatgpt.com'}},editor),null);
sendButtons=[{...arrow,getBoundingClientRect:()=>({left:100,right:140,top:20,bottom:60,width:40,height:40})}];assert.equal(flow.sendButton(flowDoc,editor),null);
console.log('5 contrôles de flèche Flow réussis : position, disponibilité, ambiguïté et site.');
sendButtons=[{...arrow,innerText:'Generierung starten'},{...arrow,innerText:'Sammlung erstellen'},{...arrow,innerText:'Tool erstellen'}];
assert.equal(flow.sendButton(flowDoc,editor),sendButtons[0],'Only the explicit generation action is allowed');
sendButtons=sendButtons.slice(1);assert.equal(flow.sendButton(flowDoc,editor),null,'Never select collection or tool creation');
const end={innerText:'Ende',getAttribute:()=>null,getClientRects:()=>[{}],getBoundingClientRect:()=>({left:720,top:420})};
const thumbnail={innerText:'',getAttribute:()=>null,getClientRects:()=>[{}],querySelector:()=>({}),getBoundingClientRect:()=>({left:600,right:670,top:420,width:70,height:70})};
let frameButtons=[end,thumbnail];const frameDoc={querySelectorAll:()=>frameButtons};
assert.equal(flow.startThumbnail(frameDoc),thumbnail);
thumbnail.disabled=true;assert.equal(flow.startThumbnail(frameDoc),null);thumbnail.disabled=false;
frameButtons=[end,thumbnail,{...thumbnail}];assert.equal(flow.startThumbnail(frameDoc),null);
frameButtons=[end,{...thumbnail,getBoundingClientRect:()=>({left:100,right:170,top:420,width:70,height:70})}];assert.equal(flow.startThumbnail(frameDoc),null);
console.log('4 contrôles de miniature Start réussis : position, disponibilité et ambiguïté.');
const events=[];
class MouseEventStub{constructor(type){this.type=type;}}
flow.activate({defaultView:{MouseEvent:MouseEventStub,PointerEvent:MouseEventStub}},{getAttribute:()=>null,focus:()=>events.push('focus'),dispatchEvent:event=>events.push(event.type),click:()=>events.push('click')});
assert.deepEqual(events,['focus','pointerdown','mousedown','pointerup','mouseup','click']);
let accountClosed=0,loggedOut=0;
const accountClose={innerText:'Schließen',getAttribute:()=>null,getClientRects:()=>[{}],click:()=>accountClosed++};
const logout={...accountClose,innerText:'Von allen Konten abmelden',click:()=>loggedOut++};
flow.closeAccountPanel({body:{innerText:'30 Google Flow-Guthabenpunkte Abo verwalten Von allen Konten abmelden'},querySelectorAll:()=>[logout,accountClose]});
assert.equal(accountClosed,1);assert.equal(loggedOut,0);
flow.closeAccountPanel({body:{innerText:'Bild für Frame auswählen'},querySelectorAll:()=>[accountClose]});assert.equal(accountClosed,1);
let previewClicks=0;const poster={complete:true,alt:'Miniaturansicht des erstellten Videos',src:'https://example.test/new-poster',getClientRects:()=>[{}],click:()=>previewClicks++};
assert.equal(flow.openNewVideo({images:[poster]},new Set(),new Set()),true);assert.equal(previewClicks,1);
assert.equal(flow.openNewVideo({images:[poster]},new Set([poster.src]),new Set()),false);
assert.equal(flow.openNewVideo({images:[poster]},new Set(),new Set([poster])),false);
assert.equal(flow.openNewVideo({images:[poster,{...poster,src:'https://example.test/other'}]},new Set(),new Set()),false);
async function importTests(){
 let clicked=[];const input={accept:'image/*',disabled:false};let exposed=false;
 const start={innerText:'Start',disabled:false,getClientRects:()=>[{}],getAttribute:()=>null,click:()=>{clicked.push('start');exposed=true;}};
 const doc={querySelectorAll:q=>q==='input[type="file"]'?(exposed?[input]:[]):q==='button,[role="button"],label'?[start]:[]};
 assert.equal(await flow.openImport(doc,async()=>{}),input);assert.deepEqual(clicked,['start']);
 clicked=[];assert.equal(await flow.openImport(doc,async()=>{}),input);assert.deepEqual(clicked,[],'Do not reopen a picker if an input already exists');
 exposed=false;let modal=false;
 start.click=()=>{clicked.push('start');modal=true;};
 const upload={innerText:'Hochladen',disabled:false,getClientRects:()=>[{}],getAttribute:()=>null,click:()=>{clicked.push('upload');exposed=true;}};
 doc.querySelectorAll=q=>q==='input[type="file"]'?(exposed?[input]:[]):q==='button,[role="button"],label'?(modal?[start,upload]:[start]):[];
 assert.equal(await flow.openImport(doc,async()=>{}),input);assert.deepEqual(clicked,['start','upload']);
 for(const label of ['Medien hoch…','Medien hoch...','file_upload\nMedien hochladen',"Importer l'élément multimédia",'Importer l’élément multimédia']){
  exposed=false;clicked=[];modal=true;upload.innerText=label;
  upload.getAttribute=name=>name==='aria-label'?'Autre intitulé':null;
  assert.equal(await flow.openImport(doc,async()=>{}),input);
  assert.deepEqual(clicked,['upload'],'Use the open picker and recognize '+label);
 }
 exposed=false;clicked=[];upload.disabled=true;
 await assert.rejects(()=>flow.openImport(doc,async()=>{}),/champ d’import détecté/);
 assert.ok(!clicked.includes('upload'),'Do not click disabled upload');
 console.log('7 parcours d’import vérifiés, dont le libellé allemand tronqué, les icônes et le sélecteur déjà ouvert.');
}
async function confirmationTests(){
 let present=true,clicks=0,ticks=0;
 const button={innerText:'Zum Prompt hinzufügen',getAttribute:()=>null,getClientRects:()=>[{}],click:()=>{clicks++;present=false;}};
 const doc={querySelectorAll:()=>present?[button]:[]};
 await flow.confirmImport(doc,async()=>{});assert.equal(clicks,1);
 present=true;button.disabled=true;
 await assert.rejects(()=>flow.confirmImport(doc,async()=>{}),/toujours en traitement/);assert.equal(clicks,1);
 button.disabled=false;button.click=()=>{clicks++;};
 await assert.rejects(()=>flow.confirmImport(doc,async()=>{}),/non terminée/);assert.equal(clicks,2,'Do not repeatedly click confirmation');
 present=false;button.click=()=>{clicks++;present=false;};
 await flow.confirmImport(doc,async()=>{if(++ticks===3)present=true;});assert.equal(clicks,3,'Wait for upload completion');
 console.log('4 confirmations vérifiées : ajout, bouton inactif, fenêtre persistante, téléversement différé.');
}
async function reuseTests(){
 let clicked=0,opened=0,ticks=0;
 const name='flow_reference_81edc04c01ddc83d4f75.jpg';
 const option={innerText:name,getClientRects:()=>[{}],getAttribute:()=>null,click:()=>clicked++};
 const start={innerText:'Start',getClientRects:()=>[{}],getAttribute:()=>null,click:()=>opened++};
 let options=[option];
 const doc={querySelectorAll:q=>q==='[role="option"]'?options:q==='button,[role="button"],label'?[start]:[]};
 const result=await flow.openImport(doc,async()=>{},name);assert.equal(result.existingReference,true);assert.equal(clicked,1);assert.equal(opened,0);
 option.innerText='Wird hochgeladen '+name;assert.equal(flow.existingReference(doc,name),null);
 option.innerText='wrong.jpg';assert.equal(flow.existingReference(doc,name),null);
 option.innerText=name;options=[option,{...option}];assert.equal(flow.existingReference(doc,name),null);
 options=[option];option.innerText='image\n'+name;assert.equal(flow.existingReference(doc,name),option,'A material icon must not hide the exact filename');option.innerText=name;
 options=[];const delayed=await flow.openImport(doc,async()=>{if(++ticks===16)options=[option];},name);
 assert.equal(delayed.existingReference,true);assert.equal(opened,1,'Click Start once while waiting for a slow selector');
 console.log('5 contrôles de réutilisation réussis : fichier exact, import en cours, mauvais fichier, ambiguïté et sélecteur lent.');
}
async function exactConfirmationTest(){
 let ticks=0,present=true;const clicked=[];const name='flow_reference_correct.jpg';
 const asset={innerText:name,getClientRects:()=>[{}],getAttribute:()=>null,click:()=>clicked.push('select-correct')};
 const button={innerText:'Zum Prompt hinzufügen',getClientRects:()=>present?[{}]:[],getAttribute:()=>null,click:()=>{clicked.push('confirm');present=false;}};
 const preview={complete:true,naturalWidth:720,getClientRects:()=>[{}],getAttribute:()=>null,get alt(){return 'Vorschau für „'+(ticks>=6?name:'old.jpg')+'“';}};
 const doc={images:[preview],querySelectorAll:q=>q==='[role="option"]'?(ticks>=3?[asset]:[]):[button]};
 await flow.confirmImport(doc,async()=>{ticks++;},()=>{},name);
 assert.deepEqual(clicked,['select-correct','confirm'],'Do not confirm the previously selected image while the new image is uploading');
 assert.ok(ticks>=6,'Wait until the preview belongs to the exact expected file');
}
async function attachedReferenceTest(){
 let clicks=0;
 const name='flow_reference_existing.jpg';
 const image={src:'https://lh3.googleusercontent.com/unique-frame=w1280'};
 const frame={...thumbnail,querySelector:()=>image,click:()=>clicks++};
 const gallery={...thumbnail,innerText:name,querySelector:()=>({src:'https://lh3.googleusercontent.com/unique-frame=w400'}),getBoundingClientRect:()=>({left:100,right:170,top:100,width:70,height:70})};
 const doc={querySelectorAll:q=>q==='input[type="file"]'||q==='[role="option"]'?[]:[end,frame,gallery]};
 assert.equal((await flow.openImport(doc,async()=>{},name)).alreadyAttached,true);assert.equal(clicks,0);
 assert.equal(flow.frameMatches(doc,'https://lh3.googleusercontent.com/other-frame'),false);
}
async function removedFrameTest(){
 let cleared=false,opened=false;const actions=[];const input={accept:'image/jpeg'};
 const old={...thumbnail,innerText:'',querySelector:()=>({src:'old'}),click:()=>{cleared=true;actions.push('clear-old');}};
 const empty={...old,innerText:'Start',querySelector:()=>null,click:()=>{opened=true;actions.push('open-start');}};
 const doc={querySelectorAll:q=>q==='input[type="file"]'?(opened?[input]:[]):q==='[role="option"]'?[]:[end,cleared?empty:old]};
 assert.equal(await flow.openImport(doc,async()=>{},'correct.jpg'),input);assert.deepEqual(actions,['clear-old','open-start']);
 const hidden={...empty,innerText:'Medien hochladen'};
 assert.equal(flow.control({querySelectorAll:()=>[hidden],defaultView:{getComputedStyle:()=>({visibility:'hidden',display:'block'})}},/^Medien hochladen$/),undefined);
}
Promise.all([importTests(),confirmationTests(),reuseTests(),exactConfirmationTest(),attachedReferenceTest(),removedFrameTest()]).catch(e=>{console.error(e);process.exitCode=1;});
