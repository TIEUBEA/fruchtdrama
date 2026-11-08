const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
async function run(boundUrl){
 const state={client:'owner',token:'test-only',scenarioTabs:{production:{client:'owner',tabId:12}}};
 const calls={latest:0,posts:[],begun:[]};
 const chrome={storage:{local:{get:async k=>k===null?state:{[k]:state[k]}}},tabs:{get:async()=>({id:12,url:boundUrl})},runtime:{onInstalled:{addListener(){}},onStartup:{addListener(){}},onMessage:{addListener(){}}},alarms:{create(){},onAlarm:{addListener(){}}}};
 const ctx=vm.createContext({chrome,console,URL,Date,setTimeout,Uint8Array,atob,fetch:async(url,opts)=>{calls.posts.push(JSON.parse(opts.body));return {ok:true,json:async()=>({id:'collector',job:'production',kind:'chat_collect'})};},FruchtWorkspace:{latest:async()=>{calls.latest++;return {id:99,url:'https://chatgpt.com/c/unrelated'};}}});
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/background-worker.js'),'utf8'),ctx);
 ctx.record=(task,tab)=>calls.begun.push({task,tab});
 vm.runInContext('begin=async(task,tab)=>record(task,tab)',ctx);
 await vm.runInContext('recover("production")',ctx);
 assert.equal(calls.posts.length,1);assert.equal(calls.posts[0].job,'production');
 assert.equal(calls.begun[0].task.kind,'chat_collect');
 return calls;
}
(async()=>{
 const bound=await run('https://chatgpt.com/c/correct');
 assert.equal(bound.latest,0);assert.equal(bound.begun[0].tab.id,12);
 const moved=await run('https://unrelated.example/');
 assert.equal(moved.latest,1);assert.equal(moved.begun[0].tab.id,99);
 console.log('Manual recovery uses the production-bound tab and rejects a moved unrelated page.');
})().catch(e=>{console.error(e);process.exitCode=1;});
