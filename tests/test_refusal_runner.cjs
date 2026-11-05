// P2-01/P2-03/P2-04: the runner reports typed failures; a refusal is confirmed on a NEW reply, without the 8-minute wait.
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const runner=fs.readFileSync(path.join(__dirname,'../extension/runner.js'),'utf8');
const composer=fs.readFileSync(path.join(__dirname,'../extension/composer.js'),'utf8');
function context({oldReply=null,newReply=null,body='',imageAfter=Infinity,challenge=false}={}){
 const state={polls:0,sent:false};
 const box=t=>({innerText:t,textContent:t,hidden:false,getAttribute:()=>null,getBoundingClientRect:()=>({width:50,height:30}),getClientRects:()=>[{}]});
 const replies=oldReply?[box(oldReply)]:[];
 const editor={tagName:'TEXTAREA',value:'',focus(){},dispatchEvent(){},closest:()=>null,getAttribute:()=>null,hidden:false,getBoundingClientRect:()=>({width:200,height:40}),getClientRects:()=>[{}]};
 const send={id:'composer-submit-button',dataset:{},hidden:false,disabled:false,innerText:'',getAttribute:()=>null,getBoundingClientRect:()=>({width:30,height:30}),getClientRects:()=>[{}],click(){state.sent=true;if(newReply)replies.push(box(newReply));}};
 const document={location:{hostname:'chatgpt.com'},images:[],
  body:{get innerText(){return (challenge?'Verify you are human ':'')+(state.sent?body:'');}},
  querySelectorAll:q=>q==='[data-message-author-role="assistant"]'?replies:q.startsWith('textarea')?[editor]:q==='button'?[send]:[],execCommand:()=>true};
 const chrome={runtime:{id:'ext',onMessage:{addListener(){}},sendMessage:async m=>m.type==='submission-intent'?{ok:true}:undefined}};
 const ctx=vm.createContext({chrome,document,location:{hostname:'chatgpt.com'},window:{getSelection:()=>({removeAllRanges(){},addRange(){}})},
  HTMLTextAreaElement:{prototype:Object.defineProperty({},'value',{set(v){this._v=v;},get(){return this._v;}})},HTMLInputElement:{prototype:{}},
  InputEvent:class{},Event:class{},setTimeout:fn=>setImmediate(fn),DataTransfer:class{},File:class{},atob:x=>x});
 vm.runInContext(composer,ctx);
 ctx.FruchtMedia={image:()=>{state.polls++;if(state.polls>50)throw Error('échec rapide : aucun refus détecté');return state.polls>=imageAfter?{src:'blob:new',currentSrc:'blob:new',alt:'Generated'}:null;},payload:async()=>({ok:true,file:'x.png'})};
 vm.runInContext(runner,ctx);ctx.fruchtRunState={state:'running'};
 return {ctx,state};
}
const task={id:'t',kind:'chat_image',payload:{prompt:'Oma Orange in the kitchen',provider:'chatgpt'}};
(async()=>{
 const refusal="I can't create that image because it violates our content policies.";
 const a=context({newReply:refusal});
 const error=await a.ctx.run(task,[]).then(()=>null,e=>e);
 assert.equal(error?.kind,'refusal');assert.match(error.message,/refuse cette image/);
 assert.ok(a.state.polls<=3,'confirmed after two identical readings, not after 8 minutes');
 // The same refusal left in the chat by a previous attempt is not a refusal of this prompt.
 const b=context({oldReply:refusal,imageAfter:4});
 assert.deepEqual(JSON.parse(JSON.stringify(await b.ctx.run(task,[]))),{ok:true,file:'x.png'});
 const c=context({body:"You've hit the plus plan limit for image generations requests. You can create more images when the limit resets in 2 hours and 5 minutes."});
 const quota=await c.ctx.run(task,[]).then(()=>null,e=>e);
 assert.equal(quota.kind,'quota');assert.equal(quota.retryAfter,7500);
 const d=context({challenge:true});
 const blocked=await d.ctx.run(task,[]).then(()=>null,e=>e);
 assert.equal(blocked.kind,'challenge');assert.equal(d.state.sent,false,'nothing sent behind an anti-robot check');
 // The message handler forwards the type and the delay to the studio.
 let handler;
 const f=context({body:'Usage limit reached. Resets in 3 hours.'});
 f.ctx.chrome.runtime.onMessage.addListener=fn=>{handler=fn;};
 const messages=[];f.ctx.chrome.runtime.sendMessage=async m=>{messages.push(m);return m.type==='submission-intent'?{ok:true}:undefined;};
 vm.runInContext(runner,f.ctx);f.ctx.fruchtRunState=undefined;
 handler({type:'frucht-run',task,attachments:[]},null,()=>{});
 for(let i=0;i<200&&f.ctx.fruchtRunState.state!=='completed';i++)await new Promise(r=>setImmediate(r));
 const result=f.ctx.fruchtRunState.result;
 assert.equal(result.error_kind,'quota');assert.equal(result.retry_after,10800);
 console.log('Connecteur : refus confirmé sur nouvelle réponse, ancien refus ignoré, quota avec délai, anti-robot sans envoi, type transmis au studio.');
})().catch(e=>{console.error(e);process.exitCode=1;});
