const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const code=fs.readFileSync(path.join(__dirname,'../extension/runner.js'),'utf8');
async function check(mode){
 let listener;
 const runtime={id:'extension',onMessage:{addListener:fn=>listener=fn},sendMessage:()=>{
  if(mode==='sync')throw Error('Extension context invalidated.');
  return mode==='async'?Promise.reject(Error('Extension context invalidated.')):Promise.resolve();
 }};
 const ctx=vm.createContext({chrome:{runtime}});vm.runInContext(code,ctx);
 vm.runInContext('run=async()=>({ok:true,text:"saved"})',ctx);
 listener({type:'frucht-run',task:{id:'task',kind:'chat_text'}},null,()=>{});
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(ctx.fruchtRunState.result.ok,true,'A notification failure must not change a completed result');
 assert.equal(ctx.fruchtRunState.result.text,'saved');
 let repeats=0;ctx.countRepeat=()=>repeats++;
 vm.runInContext('run=async()=>{countRepeat();return {ok:true};}',ctx);
 let ack;listener({type:'frucht-run',task:{id:'task',kind:'chat_text'}},null,x=>ack=x);
 assert.equal(ack.already_started,true);assert.equal(repeats,0,'A completed task is never regenerated after reconnection');
 ctx.fruchtRunState={state:'running',task:'task'};
 listener({type:'frucht-run',task:{id:'task',kind:'chat_text'}},null,x=>ack=x);
 assert.equal(ack.accepted,true);assert.equal(repeats,0,'An in-flight task is acknowledged without a duplicate run');
 runtime.id=undefined;
 assert.throws(()=>vm.runInContext('requireLiveExtension()',ctx),/refresh this tab/);
}
(async()=>{for(const mode of ['ok','sync','async'])await check(mode);console.log('3 tests de cycle de vie réussis : envoi normal, contexte invalidé synchrone et rejet asynchrone.');})().catch(e=>{console.error(e);process.exitCode=1;});
