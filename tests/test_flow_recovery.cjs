const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const load=name=>fs.readFileSync(path.join(__dirname,'../extension',name),'utf8');
const store={flowTab:10};let navigated=0,created=0;
const listener={addListener(){}};
const chrome={storage:{local:{get:async key=>({[key]:store[key]}),set:async data=>Object.assign(store,data)}},runtime:{onMessage:listener,onInstalled:listener,onStartup:listener},alarms:{onAlarm:listener},tabs:{query:async()=>[{id:10,url:'https://flow.google.com/u/0/project/original/edit/clip'}],update:async()=>{navigated++;return{id:10};},create:async p=>{created++;return{id:11,...p};}}};
const c=vm.createContext({chrome,URL,Date,setTimeout,FruchtWorkspace:{adopt:async(_,tab)=>tab,createTab:(ch,p)=>ch.tabs.create(p)}});
for(const file of ['flow-controls.js','flow-session.js','background-worker.js'])vm.runInContext(load(file),c);
(async()=>{
 for(const [message,kind] of [['Dieses Video konnte nicht generiert werden.','other'],['Die Generierung ist fehlgeschlagen.','other'],['Der Inhalt verstößt gegen unsere Richtlinien.','refusal'],['Something went wrong. Try again.','other'],['This content violates our policy.','refusal']]){
  const doc={body:{innerText:message}};assert.equal(c.FruchtFlow.generationFailure(doc,new Set()).kind,kind);
  assert.equal(c.FruchtFlow.generationFailure(doc,new Set([message])),null,'Old errors are not this generation');
 }
 const repeated='Impossible de générer la vidéo demandée pour le moment en raison des intérêts des fournisseurs de contenu tiers.';
 const before=c.FruchtFlow.generationSnapshot({body:{innerText:repeated}});
 assert.equal(c.FruchtFlow.generationFailure({body:{innerText:repeated}},before),null);
 const duplicate=c.FruchtFlow.generationFailure({body:{innerText:repeated+'\n'+repeated}},before);
 assert.equal(duplicate.kind,'refusal','The same refusal on a new clip must end the wait');
 assert.equal(duplicate.message,repeated);
 const active={tabId:10,task:{id:'uncertain',job:'job',slot:'clip:3',kind:'flow_video',payload:{}}};
 await c.protectPendingFlow(active,{ok:false,generation_submitted:true});assert.equal(store.flowRecoveryTabs.uncertain.tabId,10);
 // Neither a different account nor another clip in the same project may reuse this tab.
 for(const url of ['https://flow.google.com/u/2/project/next','https://flow.google.com/u/0/project/original']){
  store.flowTab=10;const tab=await c.FruchtFlowSession.tabFor({payload:{flow_route:{url}}},chrome);assert.equal(tab.id,11);
 }
 assert.equal(created,2);assert.equal(navigated,0);
 await c.protectPendingFlow(active,{ok:true});assert.equal(Object.keys(store.flowRecoveryTabs).length,0);
 await c.protectPendingFlow(active,{ok:false,generation_submitted:false});assert.equal(Object.keys(store.flowRecoveryTabs).length,0);
 await c.protectPendingFlow(active,{ok:false,generation_submitted:true,flow_failed:true});assert.equal(Object.keys(store.flowRecoveryTabs).length,0);
 console.log('Flow: German failure detection, technical/refusal distinction, old-error exclusion, uncertain-tab protection and successful recovery cleanup passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
