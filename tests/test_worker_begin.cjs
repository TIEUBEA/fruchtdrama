const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
async function check(oldStatus,submitted){
 let reloads=0,runs=0;const store={token:'local'};const listener={addListener:()=>{}};
 const chrome={storage:{local:{get:async key=>({[key]:store[key]}),set:async data=>Object.assign(store,data)}},tabs:{update:async()=>({}),get:async()=>({url:'https://flow.google.com/project/test',status:'complete'}),reload:async()=>reloads++,sendMessage:async(id,m)=>{
  if(m.type==='frucht-status')return{state:'running',task:'old',submitted};runs++;return{accepted:true};
 }},scripting:{executeScript:async()=>[{result:true}]},runtime:{onInstalled:listener,onStartup:listener,onMessage:listener},alarms:{onAlarm:listener}};
 const context=vm.createContext({chrome,URL,Date,setTimeout,fetch:async()=>({ok:true,json:async()=>({task_status:oldStatus})})});
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/recovery.js'),'utf8'),context);
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/background-worker.js'),'utf8'),context);
 const promise=vm.runInContext("begin({id:'new',job:'job',kind:'flow_video',slot:'clip:1',payload:{attachments:[]}}, {id:1},{client:'client'})",context);
 if(oldStatus==='done'||(!submitted&&oldStatus==='failed')){await promise;assert.equal(reloads,1);assert.equal(runs,1);}
 else{await assert.rejects(promise,/précédente reste à vérifier/);assert.equal(reloads,0);assert.equal(runs,0);}
}
(async()=>{await check('done',true);await check('failed',false);await check('failed',true);await check('claimed',true);console.log('4 transitions vérifiées : tâche terminée, échec avant envoi, envoi incertain et tâche active.');})().catch(e=>{console.error(e);process.exitCode=1;});
