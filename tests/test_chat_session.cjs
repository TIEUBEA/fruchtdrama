const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
function harness(){
 const store={client:'client'},tabs=new Map(),created=[],closed=[],events=[];let next=10,failClose=false;const responses=new Map();
 const chrome={storage:{local:{get:async keys=>keys===null?structuredClone(store):Array.isArray(keys)?Object.fromEntries(keys.map(k=>[k,store[k]])):{[keys]:store[keys]},set:async data=>Object.assign(store,data),remove:async key=>delete store[key]}},
 tabs:{get:async id=>{if(!tabs.has(id))throw Error('closed');return tabs.get(id);},create:async data=>{const tab={id:next++,...data};tabs.set(tab.id,tab);created.push(tab);events.push('create');return tab;},query:async()=>[...tabs.values()],remove:async ids=>{if(failClose)throw Error('temporary failure');for(const id of ids){closed.push(id);tabs.delete(id);events.push('close');}},sendMessage:async(id,m)=>responses.get(id)?.(m)||null},scripting:{executeScript:async()=>[]},runtime:{onMessage:{addListener:()=>{}},onInstalled:{addListener:()=>{}},onStartup:{addListener:()=>{}}},alarms:{onAlarm:{addListener:()=>{}}}};
 const ctx={URL,Date,setTimeout,chrome,fetch:async url=>{events.push('ack');return{ok:true,json:async()=>({task_status:'done'})};}};vm.createContext(ctx);
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/chat-session.js'),'utf8'),ctx);
 return {store,tabs,chrome,created,closed,events,responses,ctx,chats:ctx.FruchtChats,failClose:value=>failClose=value};
}
const task=(job,kind='chat_text',provider='chatgpt')=>({id:job+'-'+kind,job,kind,payload:{provider,prompt:'Unique prompt of production '+job+' with enough original content for verification'}});
(async()=>{
 const h=harness(),cfg={client:'client'},t=task('A');
 const first=await h.chats.tabFor(t,cfg,h.chrome);
 h.store.aiSessions={'A:chatgpt':{url:'https://chatgpt.com/c/old',tabId:first.id,client:'client'}};
 const second=await h.chats.tabFor(task('A','chat_image'),cfg,h.chrome);
 assert.equal(h.created.length,2);assert.equal(second.url,'https://chatgpt.com/','Each request opens a fresh chat even for the same production');
 const claude=await h.chats.tabFor(task('B','chat_text','claude'),cfg,h.chrome);assert.equal(claude.url,'https://claude.ai/new');
 h.tabs.set(first.id,{...first,url:'https://chatgpt.com/c/finished'});
 h.responses.set(first.id,()=>({task:t.id,url:'https://chatgpt.com/c/finished',busy:false}));
 const active={task:t,tabId:first.id,client:'client'};
 await h.chats.queueClose(active,h.chrome);await h.chats.queueClose(active,h.chrome);assert.equal(h.store.completedAITabs.length,1);
 h.failClose(true);assert.equal(await h.chats.closeCompleted(h.chrome),false);assert.equal(h.store.completedAITabs.length,1);
 h.failClose(false);assert.equal(await h.chats.closeCompleted(h.chrome),true);assert.deepEqual(h.closed,[first.id]);assert.equal(h.store.completedAITabs.length,0);
 const protect=harness();for(const id of [1,2,3])protect.tabs.set(id,{id,url:'https://chatgpt.com/c/chat-'+id});
 protect.responses.set(1,()=>null);protect.responses.set(2,()=>({task:t.id,url:'https://chatgpt.com/c/chat-2',busy:true}));protect.responses.set(3,()=>({task:t.id,url:'https://chatgpt.com/c/chat-3',busy:false}));
 for(const id of [1,2,3])await protect.chats.queueClose({...active,tabId:id},protect.chrome);
 await protect.chats.closeCompleted(protect.chrome);assert.deepEqual(protect.closed,[3]);assert.ok(protect.tabs.has(1),'Keep repurposed tabs');assert.ok(protect.tabs.has(2),'Keep drafts');
 const integration=harness();integration.tabs.set(8,{id:8,url:'https://chatgpt.com/c/acknowledged'});integration.responses.set(8,()=>({task:t.id,url:'https://chatgpt.com/c/acknowledged',busy:false}));
 integration.ctx.active={...active,tabId:8};integration.store.activeTask=integration.ctx.active;integration.store.scenarioTabs={A:{pending:true}};
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/background-worker.js'),'utf8'),integration.ctx);
 await vm.runInContext('finish(active,{ok:true,text:"scenario"})',integration.ctx);
 assert.deepEqual(integration.events,['ack','close'],'Server acknowledgement must precede closing');assert.equal(integration.store.activeTask,undefined);
 const offline=harness();offline.ctx.active={...active,tabId:8};offline.ctx.fetch=async()=>{throw Error('Failed to fetch')};vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/background-worker.js'),'utf8'),offline.ctx);
 await assert.rejects(vm.runInContext('finish(active,{ok:true,text:"scenario"})',offline.ctx),/Failed to fetch/);assert.equal(offline.closed.length,0);assert.equal(offline.store.activeTask.pendingResult.ok,true);
 const rejected=harness();rejected.ctx.active={...active,tabId:8};rejected.ctx.fetch=async()=>({ok:true,json:async()=>({task_status:'failed'})});vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/background-worker.js'),'utf8'),rejected.ctx);
 await vm.runInContext('finish(active,{ok:true,text:"scenario"})',rejected.ctx);assert.equal(rejected.closed.length,0,'Do not close a rejected result');
 console.log('Fresh AI chats, close after acknowledgement, durable closure retry, original tabs/drafts protected, no closure on transfer failure or rejected result.');
})().catch(e=>{console.error(e);process.exitCode=1;});
