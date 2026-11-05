const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
function harness(mode){
 const calls={imports:0,results:[],resumed:0,generated:0};
 const requestedAt=new Date(Date.now()-(mode==='late-complete'||mode==='late-waiting'?330000:1000)).toISOString();
 const active={task:{id:'task',job:'job',kind:'flow_collect',slot:'clip:1',payload:{}},client:'client',tabId:1,download:{requestedAt}};
 const store={token:'local',client:'client',activeTask:active};const listener={addListener:()=>{}};
 const base={id:7,startTime:requestedAt,url:'blob:https://flow.google.com/clip',filename:'C:/Users/test/Downloads/clip.mp4',mime:'video/mp4',state:'complete',exists:true,danger:'safe',fileSize:3200};
 let item={...base,...(mode==='late-complete'?{startTime:new Date(Date.parse(requestedAt)+124000).toISOString()}:{}),...(mode==='late-waiting'?{state:'in_progress'}:{}),...(mode==='unsafe'?{danger:'content'}:{}),...(mode==='interrupted'?{state:'interrupted',error:'NETWORK_FAILED',canResume:true}:{}),...(mode==='unrelated'?{url:'https://unrelated.example/clip'}:{})};
 const chrome={storage:{local:{get:async key=>key===null?structuredClone(store):{[key]:structuredClone(store[key])},set:async value=>Object.assign(store,structuredClone(value)),remove:async key=>delete store[key]}},downloads:{search:async()=>mode==='ambiguous'?[item,{...item,id:8}]:[item],resume:async()=>{calls.resumed++;item={...base};},onCreated:listener,onChanged:listener},tabs:{create:async()=>calls.generated++},runtime:{onInstalled:listener,onStartup:listener,onMessage:listener},alarms:{onAlarm:listener}};
 const fetch=async(url,options)=>{
  if(url.includes('/bridge/status'))return {ok:true,json:async()=>({task_status:'claimed',job_status:'running',job_stage:'clips'})};
  if(url.endsWith('/bridge/import-download')){calls.imports++;return{ok:true,json:async()=>({file:'clip_1_verified.mp4'})};}
  if(url.endsWith('/bridge/result')){calls.results.push(JSON.parse(options.body).result);return{ok:true,json:async()=>({task_status:'done'})};}
  throw Error('Unexpected request '+url);
 };
 const ctx=vm.createContext({chrome,fetch,URL,Date,setTimeout,structuredClone,Uint8Array});
 for(const f of ['recovery.js','download-policy.js','background-worker.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension',f),'utf8'),ctx);
 return {calls,store,poll:()=>vm.runInContext('poll()',ctx)};
}
(async()=>{
 const good=harness('complete');await good.poll();assert.equal(good.calls.imports,1);assert.equal(good.calls.results[0].file,'clip_1_verified.mp4');assert.equal(good.store.activeTask,undefined);assert.equal(good.calls.generated,0);
 for(const mode of ['unsafe','ambiguous']){const h=harness(mode);await h.poll();assert.equal(h.calls.imports,0);assert.equal(h.calls.results[0].ok,false);}
 const unrelated=harness('unrelated');await unrelated.poll();assert.equal(unrelated.calls.imports,0);assert.ok(unrelated.store.activeTask);
 const interrupted=harness('interrupted');await interrupted.poll();assert.equal(interrupted.calls.resumed,1);await interrupted.poll();assert.equal(interrupted.calls.imports,1);
 const late=harness('late-complete');await late.poll();assert.equal(late.calls.imports,1);assert.equal(late.calls.generated,0);
 const expired=harness('late-waiting');await expired.poll();assert.equal(expired.calls.imports,0);assert.equal(expired.calls.results[0].ok,false);assert.match(expired.calls.results[0].error,/cinq minutes/);
 console.log('7 parcours de récupération automatique vérifiés, dont téléchargement préparé après deux minutes et résultat terminé avant le réveil du worker.');
})().catch(e=>{console.error(e);process.exitCode=1;});
