// P1-4: a Flow dry run prepares everything but never declares a submission intent nor clicks Send.
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const code=fs.readFileSync(path.join(__dirname,'../extension/runner.js'),'utf8');
function context(){
 const calls={send:0,intent:0,configure:0};
 const editor={tagName:'TEXTAREA',value:'',focus(){},dispatchEvent(){},getBoundingClientRect:()=>({left:0,right:500,top:0,bottom:50})};
 const send={innerText:'arrow_forward',getAttribute:()=>'',click(){calls.send++;}};
 const document={body:{innerText:'Generation will use 12 credits'},images:[],querySelectorAll:()=>[],execCommand:()=>true};
 const flow={closeAccountPanel(){},async prepareFrames(){calls.configure++;},async configure(){calls.configure++;},settingsButton:()=>null,cost:()=>12,outputCount:()=>1,
  verifyModel(){},sendButton:()=>send,creditBlocked:()=>false,openNewVideo:()=>{throw Error('stop after submission');}};
 const chrome={runtime:{id:'ext',onMessage:{addListener(){}},sendMessage:async m=>{if(m.type==='submission-intent'){calls.intent++;return {ok:true};}}}};
 class InputEvent{constructor(){}};class Event{constructor(){}};
 const ctx=vm.createContext({chrome,document,location:{hostname:'flow.google.com'},window:{getSelection:()=>({removeAllRanges(){},addRange(){}})},
  HTMLTextAreaElement:{prototype:Object.defineProperty({},'value',{set(v){this._v=v;},get(){return this._v;}})},HTMLInputElement:{prototype:{}},InputEvent,Event,
  setTimeout:(fn)=>setImmediate(fn),DataTransfer:class{},File:class{},atob:x=>x});
 ctx.FruchtFlow=flow;ctx.FruchtComposer={challenge:()=>false,editor:()=>editor,diagnostic:()=>({})};
 ctx.FruchtFlowSession={verify:()=>true};ctx.FruchtMedia={};
 vm.runInContext(code,ctx);ctx.fruchtRunState={state:'running'};
 return {ctx,calls};
}
(async()=>{
 const task=dry=>({id:'t',kind:'flow_video',payload:{prompt:'One continuous shot',cost:12,balance:40,model:'gemini_omni_flash',resolution:'720p',seconds:8,...(dry?{dry_run:true}:{})}});
 const a=context();const result=await a.ctx.run(task(true),[]);
 assert.equal(result.dry_run,true);assert.equal(result.ok,false);assert.equal(result.generation_submitted,false);
 assert.match(result.error,/Essai à blanc réussi.*12 crédits/);
 assert.equal(a.calls.send,0,'Send never clicked');assert.equal(a.calls.intent,0,'no submission intent');assert.ok(a.calls.configure>0,'Flow configured and verified');
 const b=context();
 await assert.rejects(()=>b.ctx.run(task(false),[]),/stop after submission/);
 assert.equal(b.calls.intent,1);assert.equal(b.calls.send,1,'real run clicks Send exactly once');
 const c=context();await assert.rejects(()=>c.ctx.run({...task(true),payload:{...task(true).payload,cost:20}},[]),/coût affiché différent/);
 assert.equal(c.calls.send,0,'a cost mismatch is reported by the dry run too');
 console.log('Essai à blanc Flow : réglages vérifiés, aucun envoi ni intention, envoi réel inchangé, écart de coût détecté.');
})().catch(e=>{console.error(e);process.exitCode=1;});
