// Claude model and effort selection in claude.ai (simulated DOM, not a test of a real claude.ai account).
const assert=require('node:assert/strict');
const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
const context={};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../extension/claude-model.js'),'utf8'),context);
const helper=context.FruchtClaudeModel;
const sleep=()=>Promise.resolve();

// A small claude.ai page: a model button opening a menu; clicking a menu entry closes the menu.
function page({current='Sonnet 4.5',models=['Opus 5.5','Sonnet 5.5','Fable 5.1'],efforts=null,more=null,testid=true,effortEntry=false}){
 const state={current,open:false,sub:false,effortOpen:false,effort:'medium',clicks:[]};
 const el=(attrs,text,onclick,visibleWhen=()=>true)=>({hidden:false,disabled:false,get innerText(){return typeof text==='function'?text():text;},
  getAttribute(k){return attrs[k]??null;},getBoundingClientRect:()=>visibleWhen()?{width:80,height:24}:{width:0,height:0},getClientRects:()=>visibleWhen()?[{}]:[],
  click(){state.clicks.push(typeof text==='function'?text():text);onclick&&onclick();}});
 const trigger=el(testid?{'data-testid':'model-selector-dropdown','aria-haspopup':'menu'}:{'aria-haspopup':'menu'},()=>state.current,()=>{state.open=!state.open;});
 const send=el({'aria-label':'Send message'},'');
 const items=models.map(m=>el({role:'menuitem'},m+'\nDescription',()=>{state.current=m;state.open=false;},()=>state.open));
 const hidden=(more||[]).map(m=>el({role:'menuitem'},m,()=>{state.current=m;state.open=false;state.sub=false;},()=>state.open&&state.sub));
 const moreItem=more?[el({role:'menuitem','aria-haspopup':'menu'},'More models',()=>{state.sub=true;},()=>state.open)]:[];
 const effortItems=(efforts||[]).map(([key,label])=>el({role:'menuitemradio',get 'aria-checked'(){return String(state.effort===key);}},label,()=>{state.effort=key;state.open=false;state.effortOpen=false;},()=>effortEntry?state.effortOpen:state.open));
 const entry=effortEntry?[el({role:'menuitem','aria-haspopup':'menu'},'Effort\nHow long Claude thinks',()=>{state.effortOpen=true;},()=>state.open)]:[];
 const upgrade=el({role:'menuitem'},'Opus 5.5 Upgrade to Max',()=>{throw Error('upgrade clicked');},()=>state.open);
 const all=[trigger,send,upgrade,...items,...moreItem,...hidden,...entry,...effortItems];
 return {state,doc:{body:{dispatchEvent(){state.open=false;state.effortOpen=false;}},activeElement:null,defaultView:{KeyboardEvent:class{constructor(t,o){this.type=t;Object.assign(this,o);}}},querySelectorAll:()=>all}};
}
const EFFORTS=[['high','High'],['extra','Extra high'],['medium','Medium']];

(async()=>{
 // 1. Model and effort picked by their visible text; the upgrade entry is never clicked.
 let p=page({efforts:EFFORTS});
 let r=await helper.select(p.doc,sleep,'opus-5.5','high');
 assert.equal(p.state.current,'Opus 5.5');assert.equal(r.model,'selected');
 assert.equal(p.state.effort,'high','"Extra high" not taken for "High"');assert.equal(r.effort,'selected');
 assert.deepEqual([...r.notes],[]);assert.ok(!p.state.clicks.some(c=>/Upgrade/.test(c)));
 p=page({efforts:EFFORTS});r=await helper.select(p.doc,sleep,'fable-5.1','extra');
 assert.equal(p.state.current,'Fable 5.1');assert.equal(p.state.effort,'extra');
 p=page({current:'Opus 4.1',efforts:EFFORTS});r=await helper.select(p.doc,sleep,'sonnet-5.5','medium');
 assert.equal(p.state.current,'Sonnet 5.5');assert.equal(r.effort,'already','effort already checked: no click');
 console.log('Modèle et effort Claude choisis par leur texte visible ; « Extra high » distinct de « High » ; jamais d’entrée payante.');

 // 2. Already the right model: no click on the menu.
 p=page({current:'Opus 5.5'});r=await helper.select(p.doc,sleep,'opus-5.5',null);
 assert.equal(r.model,'already');assert.deepEqual([...p.state.clicks],[]);

 // 3. Without the known test id, under « More models », and a newer version of the same family.
 p=page({testid:false,models:['Sonnet 5.5'],more:['Opus 5.5','Fable 5.1']});r=await helper.select(p.doc,sleep,'fable-5.1',null);
 assert.equal(p.state.current,'Fable 5.1');assert.equal(r.model,'selected');
 p=page({models:['Opus 5.6','Sonnet 5.5']});r=await helper.select(p.doc,sleep,'opus-5.5',null);
 assert.equal(p.state.current,'Opus 5.6','same family kept when the exact version is gone');
 console.log('Sans identifiant connu, sous « More models », et version plus récente de la même famille.');

 // 4. Effort behind an « Effort » entry.
 p=page({efforts:EFFORTS,effortEntry:true});r=await helper.select(p.doc,sleep,'opus-5.5','extra');
 assert.equal(p.state.effort,'extra');assert.equal(r.effort,'selected');

 // 5. Nothing found: never blocks, tab model kept, clear note for the studio.
 p=page({models:[]});p.state.current='Claude';
 const empty={body:{dispatchEvent(){}},querySelectorAll:()=>[]};
 r=await helper.select(empty,sleep,'opus-5.5','high');
 assert.equal(r.model,'missing');assert.equal(r.effort,'missing');
 assert.match(r.notes[0],/^Modèle Claude non sélectionnable automatiquement : modèle de l’onglet conservé/);
 assert.match(r.notes[1],/^Effort Claude non sélectionnable automatiquement/);
 p=page({models:['Sonnet 5.5']});r=await helper.select(p.doc,sleep,'fable-5.1','high');
 assert.equal(p.state.current,'Sonnet 4.5','tab model kept');assert.equal(r.model,'missing');assert.equal(p.state.open,false,'menu closed again');
 const broken={body:{dispatchEvent(){}},querySelectorAll:()=>{throw Error('DOM changed');}};
 r=await helper.select(broken,sleep,'opus-5.5','high');assert.equal(r.model,'missing');assert.match(r.error,/DOM changed/);
 console.log('Menu introuvable ou page cassée : rien de bloqué, modèle de l’onglet conservé, note renvoyée.');

 // 6. The runner selects before filling the prompt, on claude.ai only, and reports the note as progress.
 const runner=fs.readFileSync(path.join(__dirname,'../extension/runner.js'),'utf8');
 assert.ok(runner.indexOf('FruchtClaudeModel.select(')<runner.indexOf('fill(editor,prompt)'));
 assert.match(runner,/location\.hostname==='claude\.ai'/);assert.match(runner,/fruchtRunState\.progress=choice\.notes/);
 const worker=fs.readFileSync(path.join(__dirname,'../extension/background-worker.js'),'utf8');
 assert.ok(/'claude-model\.js','runner\.js'/.test(worker),'helper injected before the runner');
 console.log('Runner : choix fait avant de coller le prompt, seulement sur claude.ai, note relayée au studio.');
})().catch(e=>{console.error(e);process.exitCode=1;});
