const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
function harness(mode){
 const active={task:{id:'task1',job:'job1',slot:'script',kind:'chat_text',payload:{provider:'chatgpt',scene_count:4}},tabId:8,client:'client1',startedAt:Date.now(),expectedJob:'job1'};
 if(['scenario-prep','scenario-intent','scenario-live'].includes(mode)){active.submissionIntent=mode==='scenario-intent';active.expectedTask='task1';active.task.payload.prompt='Original script prompt';active.recoveryAttempts=16;}
 if(mode==='research-lost'){active.task.kind='tiktok_search';active.task.slot='research';active.task.payload={query:'KI Früchte Geschichten deutsch'};}
 if(mode==='image'){active.task.kind='chat_image';active.task.slot='image:0';active.task.payload.prompt='Exact original scene image prompt for automatic collection';}
 if(mode==='flow-prep'||mode==='flow-uncertain'){active.task.kind='flow_video';active.task.slot='clip:2';active.task.payload={attachments:[]};active.submissionIntent=mode==='flow-uncertain';}
 const store={lastResearchReadingRecovery:Date.now(),token:'local',client:'client1',enabled:true,activeTask:active,scenarioTabs:{job1:{...active,pending:true}}};
 if(mode==='restart')active.pendingResult={ok:true,text:'{"production_id":"job1"}'};const calls={submitted:[],results:0,created:0};let failOnce=mode==='network';
 const chrome={storage:{local:{get:async key=>{if(key===null)return structuredClone(store);if(Array.isArray(key))return Object.fromEntries(key.map(k=>[k,structuredClone(store[k])]));return {[key]:structuredClone(store[key])};},set:async data=>Object.assign(store,structuredClone(data)),remove:async key=>{delete store[key];}}},tabs:{get:async()=>({id:8,url:mode==='wrong-site'?'https://unrelated.example/':mode==='research-lost'?'https://www.tiktok.com/search?q=fruit':'https://chatgpt.com/c/bound'}),create:async()=>{calls.created++;return{id:9}},sendMessage:async(id,m)=>{if(m.type==='frucht-run'){calls.submitted.push(m.task);return{accepted:true};}if(mode==='scenario-live'&&m.type==='frucht-status')return{task:'task1',state:'running'};if(mode==='research-lost'||mode==='lost'||mode==='wrong-site'||mode==='scenario-prep'||mode==='scenario-intent')throw Error('Receiving end does not exist');return {task:'task1',state:'completed',result:{ok:true,text:'{"production_id":"job1"}'}};}},scripting:{executeScript:async()=>[]},alarms:{create:()=>{},onAlarm:{addListener:()=>{}}},runtime:{onInstalled:{addListener:()=>{}},onStartup:{addListener:()=>{}},onMessage:{addListener:()=>{}}}};
 const fetch=async url=>{if(url.includes('/bridge/status'))return {ok:true,json:async()=>({task_status:mode==='restart'?'failed':'claimed',job_stage:'script',job_status:'running'})};if(url.endsWith('/bridge/recover'))return {ok:true,json:async()=>({...active.task,id:'recovered-task',kind:'chat_collect'})};if(url.endsWith('/bridge/result')){calls.results++;if(failOnce){failOnce=false;throw Error('Failed to fetch');}return {ok:true,json:async()=>({ok:true,task_status:'done'})};}throw Error('Unexpected request '+url);};
 if(mode==='image'){
  const originalMessage=chrome.tabs.sendMessage;
  chrome.tabs.sendMessage=async(id,m)=>m.type==='frucht-media-probe'?{ok:true,matched:true,base64:'aW1hZ2U=',mime:'image/png'}:originalMessage(id,m);
 }
 const wrappedFetch=async(url,options)=>url.includes('/bridge/upload?')?{ok:true,json:async()=>({file:'scene.png'})}:fetch(url,options);
 if(['scenario-prep','scenario-intent','scenario-live'].includes(mode)){chrome.tabs.update=async()=>({});chrome.scripting.executeScript=async()=>[{result:true}];}
 if(mode==='flow-prep'||mode==='flow-uncertain'){
  chrome.tabs.update=async()=>({});chrome.tabs.get=async()=>({id:8,status:'complete',url:'https://flow.google.com/project/bound'});
  chrome.scripting.executeScript=async()=>[{result:true}];
  const originalMessage=chrome.tabs.sendMessage;
  chrome.tabs.sendMessage=async(id,m)=>{if(m.type==='frucht-status')throw Error('Receiving end does not exist');if(m.type==='frucht-video-probe')return{ok:false,matched:false};return originalMessage(id,m);};
 }
 const context=vm.createContext({chrome,fetch:wrappedFetch,URL,Date,structuredClone,console,setTimeout,Uint8Array,atob});
 for(const f of ['recovery.js','background-worker.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension',f),'utf8'),context);
 return {store,calls,poll:()=>vm.runInContext('poll()',context)};
}
(async()=>{
 const completed=harness('done');await completed.poll();assert.equal(completed.calls.results,1);assert.equal(completed.store.activeTask,undefined);assert.equal(completed.calls.created,0);
 const lost=harness('lost');await lost.poll();assert.equal(lost.calls.submitted.length,1);assert.equal(lost.calls.submitted[0].kind,'chat_collect');assert.equal(lost.calls.created,0);assert.equal(lost.store.activeTask.recoveryAttempts,1);
 const offline=harness('network');await offline.poll();assert.equal(offline.store.activeTask.pendingResult.ok,true);await offline.poll();assert.equal(offline.calls.results,2);assert.equal(offline.store.activeTask,undefined);assert.equal(offline.calls.created,0);
 const wrong=harness('wrong-site');await wrong.poll();assert.equal(wrong.calls.submitted.length,0);assert.equal(wrong.store.activeTask,undefined);
 const restart=harness('restart');await restart.poll();assert.equal(restart.calls.results,1);assert.equal(restart.store.activeTask,undefined);assert.equal(restart.calls.created,0);
 const image=harness('image');await image.poll();assert.equal(image.calls.results,1);assert.equal(image.store.activeTask,undefined);assert.equal(image.calls.created,0);assert.equal(image.calls.submitted.length,0,'Collect the existing image without another generation');
 const preparation=harness('flow-prep');await preparation.poll();assert.equal(preparation.calls.created,0);assert.equal(preparation.calls.submitted.length,1);assert.equal(preparation.calls.submitted[0].id,'task1','Resume the same pre-submission lease');assert.equal(preparation.store.activeTask.recoveryAttempts,1);
 const uncertain=harness('flow-uncertain');await uncertain.poll();assert.equal(uncertain.calls.submitted.length,0);assert.equal(uncertain.calls.results,1,'Do not resend after submission intent was recorded');
 const research=harness('research-lost');await research.poll();assert.equal(research.calls.submitted.length,1);assert.equal(research.calls.submitted[0].kind,'tiktok_search');assert.equal(research.calls.submitted[0].id,'task1');assert.equal(research.calls.created,0);
 console.log('9 scénarios du worker réussis, dont collecte existante, reconnexion avant envoi et absence de réenvoi après intention de génération.');
})().catch(e=>{console.error(e);process.exitCode=1;});
