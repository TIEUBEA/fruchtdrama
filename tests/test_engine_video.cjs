// P5-09/P5-10: Grok Imagine and LMArena connectors on DOM fixtures (not a test of the live sites).
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const code=fs.readFileSync(path.join(__dirname,'../extension/engine-video.js'),'utf8');
const el=(props={})=>({hidden:false,disabled:false,clicks:0,attrs:{},innerText:'',textContent:'',getAttribute(k){return this.attrs[k]??null;},
 getBoundingClientRect:()=>({width:60,height:30}),click(){this.clicks++;this.onclick?.();},dispatchEvent(){},...props});
function page({engine='grok',loggedOut=false,account=null,videoAfter=3,after='',before='',pressed=false,buy=false}={}){
 const state={polls:0,sent:false,intent:0,filled:null,files:null};
 const mode=el({innerText:engine==='grok'?'Video':'Vidéo',attrs:{'aria-pressed':pressed?'true':'false'}});
 const send=el({innerText:engine==='grok'?'Submit':'Send',onclick(){state.sent=true;}});
 const upgrade=el({innerText:'Upgrade to SuperGrok'});
 const login=el({innerText:'Sign in'});
 const editor=el({tagName:'TEXTAREA'});
 const input=el({accept:'image/*',dispatchEvent(){state.files=this.files;}});
 const avatar=el({attrs:{alt:account||''}});
 const oldVideo={src:'https://cdn/old.mp4',currentSrc:'https://cdn/old.mp4',readyState:4,duration:6};
 const doc={
  get body(){return {innerText:before+(state.sent&&state.polls>=1?after:'')};},
  querySelectorAll(q){
   if(q.startsWith('button'))return [...(loggedOut?[login]:[]),mode,...(buy?[upgrade]:[]),send];
   if(q.startsWith('textarea'))return loggedOut?[]:[editor];
   if(q.startsWith('[contenteditable'))return [];
   if(q==='input[type="file"]')return [input];
   if(q==='video'){state.polls++;return state.sent&&state.polls>=videoAfter?[oldVideo,{src:'blob:new',currentSrc:'blob:new',readyState:4,duration:6}]:[oldVideo];}
   if(q.includes('img[alt*="@"]'))return account?[avatar]:[];
   return [];
  }};
 const ctx={URL};vm.createContext(ctx);vm.runInContext(code,ctx);
 const fail=(kind,message,extra={})=>Object.assign(Error(message),{kind},extra);
 let t=0;
 const h={document:doc,sleep:async()=>{t+=1000;},now:()=>t,blocked(){},fail,atob:x=>x,
  fill:(e,v)=>{state.filled=v;},DataTransfer:class{constructor(){this.items={add:f=>this.files.push(f)};this.files=[];}},File:class{constructor(b,n){this.name=n;}},Event:class{},
  intent:async()=>{state.intent++;return true;},submitted:()=>{},videoPayload:async v=>({ok:true,src:v.src}),retryAfter:()=>7200};
 return {E:ctx.FruchtEngines,h,state,mode,send,upgrade};
}
const task=(engine,extra={})=>({id:'t',kind:'engine_video',payload:{engine,prompt:'One continuous shot, 6 seconds',seconds:6,...extra}});
const img=[{name:'scene0.jpg',data:'abc',mime:'image/jpeg'}];
(async()=>{
 for(const engine of ['grok','arena']){
  const p=page({engine});
  const result=await p.E.run(task(engine),img,p.h);
  assert.deepEqual(JSON.parse(JSON.stringify(result)),{ok:true,src:'blob:new'},engine+': new video returned, old one ignored');
  assert.equal(p.mode.clicks,1,'video mode selected');assert.equal(p.state.files.length,1,'reference image attached');
  assert.match(p.state.filled,/6 seconds/);assert.equal(p.state.intent,1);assert.equal(p.send.clicks,1,'sent exactly once');
  // Dry run: everything prepared, nothing sent.
  const d=page({engine});const dry=await d.E.run(task(engine,{dry_run:true}),img,d.h);
  assert.equal(dry.dry_run,true);assert.equal(dry.generation_submitted,false);assert.equal(d.send.clicks,0);assert.equal(d.state.intent,0);
 }
 const already=page({pressed:true});await already.E.run(task('grok'),img,already.h);assert.equal(already.mode.clicks,0,'video mode already on: untouched');
 const out=page({loggedOut:true});const e1=await out.E.run(task('grok'),img,out.h).then(()=>null,e=>e);
 assert.equal(e1.kind,'login');assert.equal(out.send.clicks,0);
 const wrong=page({account:'other@gmail.com'});const e2=await wrong.E.run(task('grok',{account:{email:'Main@gmail.com'}}),img,wrong.h).then(()=>null,e=>e);
 assert.equal(e2.kind,'login');assert.match(e2.message,/other@gmail.com.*main@gmail.com/);assert.equal(wrong.send.clicks,0,'wrong account: nothing sent');
 const right=page({account:'main@gmail.com'});await right.E.run(task('grok',{account:{email:'main@gmail.com'}}),img,right.h);assert.equal(right.send.clicks,1);
 const quota=page({after:' Rate limit reached. Try again in 2 hours.',videoAfter:99});const e3=await quota.E.run(task('grok'),img,quota.h).then(()=>null,e=>e);
 assert.equal(e3.kind,'quota');assert.equal(e3.retryAfter,7200);
 const refused=page({engine:'arena',after:' This prompt was flagged by our content filter.',videoAfter:99});const e4=await refused.E.run(task('arena'),img,refused.h).then(()=>null,e=>e);
 assert.equal(e4.kind,'refusal');
 const stale=page({before:'Rate limit reached yesterday. ',videoAfter:4});const ok=await stale.E.run(task('grok'),img,stale.h);
 assert.equal(ok.ok,true,'an old limit message already on the page is not a new wall');
 const shop=page({buy:true});await shop.E.run(task('grok'),img,shop.h);assert.equal(shop.upgrade.clicks,0,'never clicks a purchase button');
 const slow=page({videoAfter:1e9});const e5=await slow.E.run(task('grok'),img,slow.h).then(()=>null,e=>e);assert.equal(e5.kind,'timeout');
 const noFile=page();noFile.E.fileInput=()=>null;const e6=await noFile.E.run(task('grok'),img,noFile.h).then(()=>null,e=>e);assert.equal(e6.kind,'interface');assert.equal(noFile.send.clicks,0);
 // Tab routing inside the FruchtDrama window.
 const E=page().E;const moved=[],created=[];
 const chrome={tabs:{query:async()=>[{id:5,url:'https://grok.com/imagine/post/1',windowId:9}],update:async(id,d)=>({id,...d})}};
 const ws={adopt:async(c,t)=>{moved.push(t.id);return t;},createTab:async(c,d)=>{created.push(d.url);return {id:7,...d};}};
 const ctx2={FruchtWorkspace:ws,URL};vm.createContext(ctx2);vm.runInContext(code,ctx2);
 await ctx2.FruchtEngines.tabFor(task('grok'),chrome);assert.deepEqual(moved,[5]);
 await ctx2.FruchtEngines.tabFor(task('arena'),chrome);assert.deepEqual(created,['https://arena.ai/video']);assert.equal(ctx2.FruchtEngines.owns('arena','https://arena.ai/video'),true,'real redirect target');
 assert.equal(E.owns('grok','https://evil.example/grok.com'),false);assert.equal(E.owns('grok','https://grok.com/imagine'),true);
 const manifest=JSON.parse(fs.readFileSync(path.join(__dirname,'../extension/manifest.json'),'utf8'));
 for(const host of ['https://grok.com/*','https://lmarena.ai/*','https://arena.ai/*'])assert.ok(manifest.host_permissions.includes(host),host);
 console.log('Connecteurs Grok/Arena (fixtures) : mode vidéo, image, prompt, envoi unique, essai à blanc, connexion, mauvais compte, quota, modération, ancien message ignoré, achat jamais cliqué, délai, onglet dans la fenêtre.');
})().catch(e=>{console.error(e);process.exitCode=1;});
