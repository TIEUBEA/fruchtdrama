const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../extension/background-worker.js'),'utf8');
function harness({failures=0,error='Could not establish connection. Receiving end does not exist.',state={state:'absent'},saved}={}){
 const task={id:'clip-task',job:'production',kind:'engine_video',slot:'clip:0',payload:{engine:'grok',attachments:[]}};
 const store={token:'test',activeVideoTask:saved};const calls={injections:0,probes:0,runs:0,ready:0};
 const listener={addListener(){}};
 const chrome={storage:{local:{get:async k=>k===null?store:{[k]:store[k]},set:async data=>Object.assign(store,data)}},tabs:{get:async()=>({id:7,url:'https://grok.com/imagine',status:'complete'}),sendMessage:async(id,m)=>{
  if(m.type==='frucht-status'){calls.probes++;if(calls.probes<=failures)throw Error(error);return state;}
  if(m.type==='frucht-run'){calls.runs++;return {accepted:true};}
 }},scripting:{executeScript:async()=>{calls.injections++;return [];}},runtime:{onInstalled:listener,onStartup:listener,onMessage:listener},alarms:{onAlarm:listener}};
 const ctx=vm.createContext({chrome,URL,Date,setTimeout:fn=>setTimeout(fn,0),FruchtRecovery:{isScenario:()=>false},FruchtEngines:{owns:(_,url)=>url==='https://grok.com/imagine'}});
 vm.runInContext(source,ctx);ctx.task=task;ctx.observed=calls;
 vm.runInContext('ready=async()=>{observed.ready++;}',ctx);
 return {ctx,task,store,calls,start:()=>vm.runInContext('begin(task,{id:7},{client:"client"})',ctx)};
}
(async()=>{
 let h=harness({failures:1});await h.start();assert.equal(h.calls.injections,2);assert.equal(h.calls.runs,1);
 h=harness({failures:99});await assert.rejects(h.start(),/Could not establish/);assert.equal(h.calls.injections,3);assert.equal(h.calls.runs,0);
 h=harness({failures:1,error:'The message port closed before a response was received.'});await assert.rejects(h.start(),/message port closed/);assert.equal(h.calls.injections,1);assert.equal(h.calls.runs,0,'Ambiguous acknowledgement is never replayed');
 for(const state of ['running','completed']){h=harness({state:{state,task:'clip-task'}});await h.start();assert.equal(h.calls.runs,0);}
 h=harness({saved:{task:{id:'clip-task'},submissionIntent:true}});await assert.rejects(h.start(),/Envoi déjà commencé/);assert.equal(h.calls.runs,0);
 h=harness({saved:{task:{id:'clip-task'},submissionIntent:false,startedAt:123,recoveryAttempts:1}});await h.start();assert.equal(h.store.activeVideoTask.startedAt,123);assert.equal(h.store.activeVideoTask.recoveryAttempts,1);
 for(const sent of [true,false]){
  h=harness();h.ctx.active={task:h.task,key:'activeVideoTask',tabId:7,client:'client',startedAt:Date.now(),submissionIntent:false,recoveryAttempts:0};
  h.store.activeVideoTask={...h.ctx.active,submissionIntent:sent};
  h.ctx.begun=0;vm.runInContext('begin=async()=>{begun++;}',h.ctx);
  const result=await vm.runInContext('recoverEnginePreparation(active)',h.ctx);
  assert.equal(result,!sent);assert.equal(h.ctx.begun,sent?0:1,'Read the latest persisted intent before reconnecting');
 }
 console.log('Grok connection: bounded receiver reconnect, same-task recovery, ambiguous acknowledgement and submitted generation protected.');
})().catch(e=>{console.error(e);process.exitCode=1;});
