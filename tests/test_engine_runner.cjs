// Exercise the real runner bridge with a Window API that requires its native receiver.
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../extension/runner.js'),'utf8');
const event={addListener(){},removeListener(){}};
const c=vm.createContext({setTimeout:fn=>fn(),location:{hostname:'grok.com'},
 document:{body:{innerText:''}},chrome:{runtime:{onMessage:event,sendMessage:async()=>({ok:true}),id:'fixture'}},
 FruchtComposer:{challenge:()=>false},DataTransfer:class{},File:class{},Event:class{}});
vm.runInContext(`globalThis.atob=function(value){
 if(this!==globalThis)throw TypeError('Illegal invocation');return value;
};globalThis.FruchtEngines={run:async(task,attachments,helpers)=>({ok:true,decoded:helpers.atob('reference')})};`,c);
vm.runInContext(source,c);
(async()=>{
 const result=await vm.runInContext("run({id:'fixture',kind:'engine_video',payload:{engine:'grok'}},[])",c);
 assert.equal(result.decoded,'reference');
 const background=fs.readFileSync(path.join(__dirname,'../extension/background-worker.js'),'utf8');
 const writes=[],uploads=[];
 const worker=vm.createContext({writes,uploads,chrome:{runtime:{onInstalled:event,onStartup:event,onMessage:event},alarms:{onAlarm:event},
  storage:{local:{get:async()=>({}),set:async()=>{},remove:async()=>{}}}}});
 vm.runInContext(background,worker);
 await vm.runInContext(`saveActive=async active=>{
   if(active.pendingResult?.base64)throw Error('Resource::kQuotaBytes quota exceeded');
   writes.push(active.pendingResult);
  };
  receiveMedia=async(task,result)=>{uploads.push(result.base64);return {ok:true,file:'clip.mp4'};};
  call=async()=>({task_status:'done'});
  finish({task:{id:'t',job:'j',slot:'clip:0',kind:'engine_video'},client:'c'},{ok:true,base64:'video'})`,worker);
 assert.deepEqual(uploads,['video']);
 assert.equal(writes[0].file,'clip.mp4');
 console.log('Grok runner bridge preserves the native Window receiver for attachment decoding. No submission.');
})().catch(e=>{console.error(e);process.exitCode=1});
