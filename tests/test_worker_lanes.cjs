// 0.1.89: two lanes in the extension, like the Atelier (clips leave while ChatGPT draws the boards).
// The chat lane (ChatGPT) and the video lane (Grok/Flow) each follow one task, in their own tab, with their own
// saved state, and each resumes alone after a service-worker restart.
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const URLS={10:'https://chatgpt.com/',11:'https://chatgpt.com/',20:'https://grok.com/imagine',21:'https://grok.com/imagine'};
const IMAGE={id:'img1',job:'job1',kind:'chat_image',slot:'image:1',payload:{provider:'chatgpt',prompt:'board 2',attachments:[]}};
const IMAGE2={id:'img2',job:'job1',kind:'chat_image',slot:'image:2',payload:{provider:'chatgpt',prompt:'board 3',attachments:[]}};
const CLIP={id:'clip0',job:'job1',kind:'engine_video',slot:'clip:0',payload:{engine:'grok',prompt:'clip 1',attachments:[]}};
const FLOW={id:'flow0',job:'job1',kind:'flow_video',slot:'clip:0',payload:{prompt:'clip 1',attachments:[]}};
function harness(store,queues){
 const calls=[],runs=[],tabState={};let handler;const listener={addListener:()=>{}};let nextChatTab=10;
 const clone=v=>v===undefined?undefined:structuredClone(v);
 const chrome={
  storage:{local:{get:async key=>key===null?clone(store):Array.isArray(key)?Object.fromEntries(key.map(k=>[k,clone(store[k])])):{[key]:clone(store[key])},set:async data=>Object.assign(store,clone(data)),remove:async key=>{delete store[key];}}},
  tabs:{get:async id=>({id,windowId:1,status:'complete',url:URLS[id]}),update:async(id)=>({id,windowId:1,url:URLS[id]}),
   sendMessage:async(id,m)=>{
    if(m.type==='frucht-run'){
     // The content script refuses a second task in its tab (runner.js); the test counts any attempt.
     runs.push({tab:id,task:m.task.id});if(tabState[id]?.state==='running')return {accepted:false,error:'Une tâche est déjà en cours dans cet onglet.'};
     tabState[id]={task:m.task.id,state:'running'};return {accepted:true};
    }
    if(m.type==='frucht-status')return tabState[id]||{state:'absent'};
    return {};
   }},
  scripting:{executeScript:async()=>[{result:true}]},
  runtime:{onInstalled:listener,onStartup:listener,onMessage:{addListener:fn=>handler=fn}},alarms:{onAlarm:listener}
 };
 const fetch=async(url,init)=>{
  calls.push(url);const body=init?.body?JSON.parse(init.body):null;const ok=v=>({ok:true,json:async()=>v});
  if(url.includes('/bridge/task?')){const lane=new URL(url).searchParams.get('lane');return ok((queues[lane]||[]).shift()||null);}
  if(url.includes('/bridge/status'))return ok({task_status:'claimed',job_stage:'images',job_status:'running'});
  if(url.includes('/bridge/result')){calls.push('result:'+body.task);return ok({ok:true,task_status:'done'});}
  if(url.includes('/bridge/recoverable')||url.includes('/bridge/requests'))return ok([]);
  return ok({});
 };
 const FruchtChats={isAI:t=>['chat_text','chat_image','chat_collect','chat_image_collect'].includes(t?.kind),tabFor:async()=>({id:nextChatTab++,windowId:1}),queueClose:async()=>{},closeCompleted:async()=>true};
 const FruchtEngines={hosts:()=>['grok.com'],tabFor:async()=>({id:20,windowId:1})};
 const context=vm.createContext({chrome,fetch,URL,Date,structuredClone,console,setTimeout,Uint8Array,atob,FruchtChats,FruchtEngines});
 for(const f of ['recovery.js','background-worker.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension',f),'utf8'),context);
 return {store,calls,runs,tabState,run:code=>vm.runInContext(code,context),message:(m,tab)=>new Promise(resolve=>handler(m,{tab:{id:tab}},resolve))};
}
const base=()=>({client:'c1',token:'t',enabled:true,lastResearchReadingRecovery:Date.now(),lastMediaRecovery:Date.now(),lastVideoRecovery:Date.now()});
(async()=>{
 // 1. One pass: the board goes to ChatGPT and the clip to Grok at the same time, each in its own tab and lane.
 const h=harness(base(),{chat:[IMAGE,IMAGE2],video:[CLIP]});
 await h.run('poll()');
 assert.ok(h.calls.some(u=>u.includes('/bridge/task?')&&u.includes('lane=chat')));
 assert.ok(h.calls.some(u=>u.includes('/bridge/task?')&&u.includes('lane=video')));
 assert.equal(h.store.activeTask.task.id,'img1');assert.equal(h.store.activeTask.tabId,10);
 assert.equal(h.store.activeVideoTask.task.id,'clip0');assert.equal(h.store.activeVideoTask.tabId,20);assert.equal(h.store.activeVideoTask.key,'activeVideoTask');
 assert.deepEqual(h.runs.slice().sort((a,b)=>a.tab-b.tab),[{tab:10,task:'img1'},{tab:20,task:'clip0'}]);
 // 2. Following both: no new claim while each lane has its task.
 const claims=h.calls.filter(u=>u.includes('/bridge/task?')).length;
 await h.run('poll()');
 // 0.1.91: while the first video lane works, the second one asks the studio for a clip of another Flow account (none here).
 const asked=h.calls.filter(u=>u.includes('/bridge/task?')).slice(claims);
 assert.equal(asked.length,1,'one task per lane: only the second clip lane asks while both work');assert.ok(asked[0].includes('lane=video'));
 assert.equal(h.store.activeVideoTask2,undefined);
 assert.equal(h.calls.filter(u=>u.includes('/bridge/status')).length,2,'each lane checks its own task');
 // 3. The board finishes first: the chat lane delivers it and takes the next board, the clip keeps going.
 h.tabState[10]={task:'img1',state:'completed',result:{ok:true,file:'board2.png'}};
 await h.run('poll()');
 assert.ok(h.calls.includes('result:img1'));assert.ok(!h.calls.includes('result:clip0'));
 assert.equal(h.store.activeVideoTask.task.id,'clip0','clip untouched');
 await h.run('poll()');
 assert.equal(h.store.activeTask.task.id,'img2');assert.equal(h.store.activeTask.tabId,11,'new board in a new ChatGPT tab');
 const perTab={};for(const r of h.runs)perTab[r.tab]=(perTab[r.tab]||0)+1;
 assert.deepEqual(perTab,{10:1,11:1,20:1},'never two tasks in the same tab');
 // 4. Submission intent reaches the lane that is about to send, and only it.
 assert.equal((await h.message({type:'submission-intent',task:'clip0'},20)).ok,true);
 assert.equal(h.store.activeVideoTask.submissionIntent,true);assert.equal(h.store.activeTask.submissionIntent,false);
 assert.equal((await h.message({type:'submission-intent',task:'clip0'},11)).ok,false,'wrong tab refused');
 // 5. Service-worker restart: a new worker finds both saved tasks and resumes each one, without any new prompt.
 const saved=structuredClone(h.store);
 const r=harness(saved,{chat:[],video:[]});
 r.tabState[11]={task:'img2',state:'completed',result:{ok:true,file:'board3.png'}};r.tabState[20]={task:'clip0',state:'completed',result:{ok:true,file:'clip1.mp4'}};
 await r.run('poll()');
 assert.ok(r.calls.includes('result:img2'));assert.ok(r.calls.includes('result:clip0'));
 assert.equal(r.runs.length,0,'resumed by reading the tabs: nothing sent again');
 assert.equal(r.calls.filter(u=>u.includes('/bridge/task?')).length,0,'no claim in the pass that resumes');
 assert.equal(r.store.activeTask,undefined);assert.equal(r.store.activeVideoTask,undefined);
 // 6. A clip saved by 0.1.88 (in activeTask) is followed by the chat loop; the video lane claims nothing meanwhile.
 const old=harness({...base(),activeTask:{task:FLOW,tabId:20,client:'c1',startedAt:Date.now(),submissionIntent:true,submitted:true}},{chat:[IMAGE],video:[CLIP]});
 old.tabState[20]={task:'flow0',state:'running'};
 await old.run('poll()');
 assert.equal(old.calls.filter(u=>u.includes('/bridge/task?')).length,0);assert.equal(old.runs.length,0);assert.equal(old.store.activeTask.task.id,'flow0');
 // 7. Studio buttons: recover waits for the chat lane only; Flow registration waits for any followed task.
 const b=harness({...base(),activeVideoTask:{task:CLIP,key:'activeVideoTask',tabId:20,client:'c1',startedAt:Date.now()}},{});
 b.run('busy.chat=true');
 await assert.rejects(b.run("recover('job1')"),/occupé/);
 b.run('busy.chat=false;busy.video=true');
 await assert.rejects(b.run("recover('job1')"),e=>!/occupé/.test(e.message),'a clip in progress does not block a chat recovery');
 b.run('busy.video=false');
 await assert.rejects(b.run('registerFlow()'),/Attendez la fin/);
 // 8. 0.1.91 parallel clips: while the first video lane works, the second takes another clip, in another tab, with its own state.
 const v=harness(base(),{video:[CLIP,{...CLIP,id:'clip1',slot:'clip:1'}]});
 v.run("FruchtEngines.tabFor=async t=>({id:t.id==='clip0'?20:21,windowId:1})");
 await v.run('poll()');
 assert.equal(v.store.activeVideoTask.task.id,'clip0');assert.equal(v.store.activeVideoTask2.task.id,'clip1');
 assert.equal(v.store.activeVideoTask2.tabId,21);assert.equal(v.store.activeVideoTask2.key,'activeVideoTask2');
 assert.deepEqual(v.runs.map(r=>r.tab).sort(),[20,21],'two clips, two tabs');
 assert.equal((await v.message({type:'submission-intent',task:'clip1'},21)).ok,true);assert.equal(v.store.activeVideoTask2.submissionIntent,true);
 v.tabState[21]={task:'clip1',state:'completed',result:{ok:true,file:'c1.mp4'}};
 await v.run('poll()');
 assert.ok(v.calls.includes('result:clip1'));assert.equal(v.store.activeVideoTask2,undefined);assert.equal(v.store.activeVideoTask.task.id,'clip0','first clip untouched');
 console.log('8 scénarios des voies réussis : planche et clip en parallèle, une tâche par voie et par onglet, reprise des deux voies, compatibilité 0.1.88, boutons du studio.');
})().catch(e=>{console.error(e);process.exitCode=1;});
