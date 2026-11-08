const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
function fixture(slot,{late=false,response=false}={}){
 const active={task:{id:'review-task',job:'production',kind:'chat_text',slot,payload:{provider:'chatgpt',response_kind:slot}},tabId:7,client:'client',startedAt:Date.now()-(late?11*60000:1000)};
 const store={activeTask:active,token:'test'};const calls={order:[],results:[],runs:0};const listener={addListener(){}};
 const chrome={storage:{local:{get:async key=>({[key]:store[key]}),set:async data=>Object.assign(store,data),remove:async key=>delete store[key]}},scripting:{executeScript:async()=>calls.order.push('response')},tabs:{sendMessage:async(id,m)=>{if(m.type==='frucht-scenario-probe'){calls.order.push('probe');return response?{text:'{"ok":true}'}:{diagnostic:{hasJob:true,hasTask:true}};}if(m.type==='frucht-run')calls.runs++;return {task:'review-task',state:'running'};}},runtime:{onMessage:listener,onInstalled:listener,onStartup:listener},alarms:{onAlarm:listener}};
 const c=vm.createContext({chrome,URL,Date,setTimeout,FruchtReadiness:{reveal:async()=>calls.order.push('reveal')},fetch:async(url,opts)=>({ok:true,json:async()=>{
  if(url.includes('/bridge/status'))return {task_status:'claimed',job_stage:slot==='cover_review'?'cover':'quality',job_status:'running'};
  if(url.endsWith('/bridge/result')){const body=JSON.parse(opts.body);calls.results.push(body.result);return {task_status:body.result.ok?'done':'failed'};}
  return {ok:true};
 }})});
 for(const name of ['recovery.js','background-worker.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension',name),'utf8'),c);
 c.active=active;return {calls,store,poll:()=>vm.runInContext('checkActive(active)',c)};
}
(async()=>{
 for(const slot of ['cover_review','quality_review','board_review']){
  const fresh=fixture(slot);await fresh.poll();assert.deepEqual(fresh.calls.order.slice(0,3),['reveal','response','probe']);assert.equal(fresh.calls.results.length,0);
  const old=fixture(slot,{late:true});await old.poll();assert.equal(old.calls.results[0].ok,false);assert.equal(old.calls.results[0].error_kind,'timeout');assert.equal(old.calls.runs,0);
  const complete=fixture(slot,{late:true,response:true});await complete.poll();await complete.poll();assert.equal(complete.calls.results[0].ok,true,'Recover a valid late response before applying the deadline');assert.equal(complete.calls.runs,0);assert.equal(complete.store.activeTask,undefined);
 }
 console.log('Review recovery: reveal hidden responses first, preserve valid late replies, bound missing-review waits and never resend a prompt.');
})().catch(e=>{console.error(e);process.exitCode=1;});
