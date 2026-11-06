// P5-09/P5-10: Grok Imagine and LMArena connectors on DOM fixtures (not a test of the live sites).
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const code=fs.readFileSync(path.join(__dirname,'../extension/engine-video.js'),'utf8');
const el=(props={})=>({hidden:false,disabled:false,clicks:0,attrs:{},innerText:'',textContent:'',getAttribute(k){return this.attrs[k]??null;},
 getBoundingClientRect:()=>({width:60,height:30}),click(){this.clicks++;this.onclick?.();},dispatchEvent(){},...props});
function page({engine='grok',loggedOut=false,account=null,videoAfter=3,after='',before='',pressed=false,buy=false,spent=false,newVideo=null,menu=false}={}){
 const state={polls:0,sent:false,intent:0,filled:null,files:null};
 const mode=el({innerText:engine==='grok'?'Video':'Vidéo',attrs:{'aria-pressed':pressed?'true':'false',...(menu?{'aria-haspopup':'dialog'}:{})}});
 // Real labels (06/11/2026): Grok « Submit » (aria-label), Arena « Send message » (aria-label).
 const send=el({attrs:{'aria-label':engine==='grok'?'Submit':'Send message'},onclick(){state.sent=true;}});
 const gauge=el({attrs:{'aria-label':'100% credits used','data-credit-notice':'true'}});
 const remove=el({attrs:{'aria-label':'Remove image'}});
 const upgrade=el({innerText:'Upgrade to SuperGrok'});
 const login=el({innerText:'Sign in'});
 const editor=el({tagName:'TEXTAREA'});
 const input=el({accept:'image/*',dispatchEvent(){state.files=this.files;}});
 const avatar=el({attrs:{alt:account||''}});
 const oldVideo={src:'https://cdn/old.mp4',currentSrc:'https://cdn/old.mp4',readyState:4,duration:6};
 const doc={
  get body(){return {innerText:before+(state.sent&&state.polls>=1?after:'')};},
  querySelectorAll(q){
   if(q.startsWith('button'))return [...(loggedOut?[login]:[]),...(engine==='grok'&&state.files?[remove]:[]),mode,...(buy?[upgrade]:[]),...(spent&&state.filled?[gauge]:[]),send];
   if(q.startsWith('[data-credit-notice]'))return spent&&state.filled?[gauge]:[];
   if(q.startsWith('textarea'))return loggedOut?[]:[editor];
   if(q.startsWith('[contenteditable'))return [];
   if(q==='input[type="file"]')return [input];
   if(q==='video'){state.polls++;return state.sent&&state.polls>=videoAfter?[oldVideo,newVideo||{src:'blob:new',currentSrc:'blob:new',readyState:4,duration:6}]:[oldVideo];}
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
 // Arena: « Video ▾ » is the modality menu (aria-haspopup): never clicked, it only opens a list.
 const arenaMenu=page({engine:'arena',menu:true});await arenaMenu.E.run(task('arena'),img,arenaMenu.h);assert.equal(arenaMenu.mode.clicks,0,'menu trigger untouched');assert.equal(arenaMenu.send.clicks,1);
 // Grok at its weekly limit: the composer shows « 100% credits used » once the prompt is in: nothing is sent.
 const spent=page({spent:true});const e7=await spent.E.run(task('grok'),img,spent.h).then(()=>null,e=>e);
 assert.equal(e7.kind,'quota');assert.equal(spent.send.clicks,0,'no send at 100% credits');assert.equal(spent.state.intent,0);
 // Real toast after a send: « You've hit your weekly limit · Resets November 7 ».
 const weekly=page({after:" You've hit your weekly limit\nResets November 7, or increase your limits to keep going now.\nIncrease Limits",videoAfter:99});
 weekly.h.retryAfter=()=>null;const e8=await weekly.E.run(task('grok'),img,weekly.h).then(()=>null,e=>e);
 assert.equal(e8.kind,'quota');assert.ok(e8.retryAfter>=60,'reset date read');
 assert.equal(weekly.E.resetIn('Resets November 7',new Date(2026,10,6,15,36)),Math.round((new Date(2026,10,7)-new Date(2026,10,6,15,36))/1000));
 assert.equal(weekly.E.resetIn('Resets Jan 2',new Date(2026,11,30)),3*86400,'next year');assert.equal(weekly.E.resetIn('no date'),null);
 // Arena clips (preload="none") and Grok clips in a background tab never load: readyState 0, https .mp4 address.
 const lazySource={src:'https://messages-prod.x.r2.cloudflarestorage.com/a/b.mp4?X-Amz=1'};
 const lazy=page({engine:'arena',newVideo:{src:'',currentSrc:'',readyState:0,duration:NaN,querySelector:()=>lazySource}});
 await lazy.E.run(task('arena'),img,lazy.h);assert.equal(lazy.send.clicks,1,'unloaded Arena clip found');
 const cta=page({engine:'arena',videoAfter:1e9});
 assert.equal(cta.E.newVideo({querySelectorAll:()=>[{src:'https://arena.ai/videos/cta/agents-cta.mp4',readyState:4,duration:44}]},new Set()),null,'Arena promo clip ignored');
 assert.equal(cta.E.newVideo({querySelectorAll:()=>[{src:'https://assets.grok.com/u/generated/1/generated_video.mp4#t=0.1',readyState:0}]},new Set())?.readyState,0,'unloaded Grok clip found');
 assert.equal(cta.E.newVideo({querySelectorAll:()=>[{src:'blob:https://x/1',readyState:0}]},new Set()),null,'unloaded blob still waits');
 // Grok /imagine (real page): 3 hidden file fields, the first two start template tools; the composer's own is in its form.
 const card1={accept:'image/jpeg,image/png'},card2={accept:'image/jpeg,image/png'},composerInput={accept:'image/jpeg,image/png',name:'files',multiple:true};
 const form={contains:x=>x===composerInput},three={querySelectorAll:()=>[card1,card2,composerInput]};
 assert.equal(cta.E.fileInput(three,{closest:()=>form}),composerInput,'form field chosen');
 assert.equal(cta.E.fileInput(three,null),composerInput,'name=files chosen');
 assert.equal(cta.E.fileInput({querySelectorAll:()=>[card1]},null),card1);
 // Grok: no « Remove image » after the import: nothing sent.
 const stuck=page();const realButtons=stuck.E.buttons.bind(stuck.E);stuck.E.buttons=d=>realButtons(d).filter(b=>b.attrs['aria-label']!=='Remove image');
 const e9=await stuck.E.run(task('grok'),img,stuck.h).then(()=>null,e=>e);assert.equal(e9.kind,'interface');assert.match(e9.message,/image non importée/);assert.equal(stuck.send.clicks,0);
 // runner.js gives the connectors a bound atob (bare h.atob = « Illegal invocation » in Chrome).
 assert.match(fs.readFileSync(path.join(__dirname,'../extension/runner.js'),'utf8'),/atob:s=>atob\(s\)/);
 // Arena in a background tab (real page): React 19 waits for an animation frame to show its content.
 const queue=[],shown=[];const win={document:{hidden:true},$RB:['a','b'],$RV(list){shown.push(...list);list.length=0;},
  requestAnimationFrame:()=>'raf',cancelAnimationFrame(){},setTimeout:f=>{queue.push(f);return 41;},clearTimeout(){},performance:{now:()=>1}};
 win.window=win;const rctx=vm.createContext(win);vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/readiness.js'),'utf8'),rctx);
 vm.runInContext('('+String(rctx.FruchtReadiness.revealHidden)+')()',rctx);
 assert.deepEqual(shown,['a','b'],'pending content revealed');let ran=0;assert.equal(win.requestAnimationFrame(()=>ran++),41);queue.splice(0).forEach(f=>f());assert.equal(ran,1,'frames run while hidden');
 win.document.hidden=false;assert.equal(win.requestAnimationFrame(()=>ran++),'raf','visible: real frames');
 assert.ok(!/^revealHidden\s*\(/.test(String(rctx.FruchtReadiness.revealHidden)),'serializable function');
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
