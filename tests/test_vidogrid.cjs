// 0.1.93: Vidogrid connector (Grok Imagine Video 1.5 Lite) on a DOM fixture shaped like the page used by
// fruit-france/outils/vidogrid/vidogrid_clip.py (not a test of the live site). Also: the Flow import gives up after 90 s
// without any progress, nothing sent.
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const code=fs.readFileSync(path.join(__dirname,'../extension/engine-video.js'),'utf8');
const el=(text,props={})=>({innerText:text,textContent:text,hidden:false,disabled:false,clicks:0,attrs:{},getAttribute(k){return this.attrs[k]??null;},
 getBoundingClientRect:()=>({width:60,height:30}),click(){this.clicks++;this.onclick?.();},dispatchEvent(){},...props});
function page({loggedOut=false,fileField=true,importDone=true,outcome='video',checked=false,lite=true}={}){
 const st={attached:false,sent:false,polls:0,filled:null,intent:0};
 const model=el('Grok Imagine Video 1.5 Lite');
 const thumb=el('');const counter=el('0/1',{get innerText(){return st.attached?'1/1':'0/1';},get textContent(){return this.innerText;},previousElementSibling:thumb});
 const select=el('Select Files',{onclick(){if(importDone)st.attached=true;}});
 const input=el('',{accept:'image/*',dispatchEvent(){if(importDone)st.attached=true;}});
 const done=el('Done');const ratio=el('9:16'),wide=el('16:9'),res=el('720p'),dur=el('10s');
 const box=el('',{checked,attrs:{}});
 const editor=el('',{tagName:'TEXTAREA'});
 const send=el('GENERATE WITH GROK',{onclick(){st.sent=true;}});
 const showcase={src:'https://vidogrid.ai/showcase/demo.mp4',currentSrc:'https://vidogrid.ai/showcase/demo.mp4'};
 const doc={
  location:{pathname:loggedOut?'/auth/login':'/app/video-gen/grok'},
  get body(){return {innerText:loggedOut?'Continue with Google':'FREE TRIAL Credits remaining: 40 '+(lite?'Grok Imagine Video 1.5 Lite ':'')+(st.attached?'1/1':'0/1')+' cost: 0 Credits OUTPUT '+(st.sent&&st.polls>=2&&outcome==='failed'?'Generation failed STATUS 503':'')};},
  querySelectorAll(q){
   if(q.startsWith('button,[role="button"],[role="option"]'))return [model,counter,select,done,ratio,wide,res,dur,send].filter(x=>lite||x!==model);
   if(q.startsWith('button'))return [select,send,done];
   if(q.startsWith('textarea'))return loggedOut?[]:[editor];
   if(q.startsWith('[contenteditable'))return [];
   if(q==='input[type="file"]')return fileField?[input]:[];
   if(q.startsWith('input[type="checkbox"]'))return [box];
   if(q==='video'){if(st.sent)st.polls++;return st.sent&&st.polls>=3&&outcome==='video'?[showcase,{src:'https://cdn.vidogrid.ai/out/clip.mp4',currentSrc:'https://cdn.vidogrid.ai/out/clip.mp4'}]:[showcase];}
   return [];
  }};
 const ctx={URL,Uint8Array};vm.createContext(ctx);vm.runInContext(code,ctx);
 let t=0;
 const h={document:doc,sleep:async()=>{t+=1000;},now:()=>t,blocked(){},fail:(kind,message,extra={})=>Object.assign(Error(message),{kind},extra),atob:x=>x,
  fill:(e,v)=>{st.filled=v;},DataTransfer:class{constructor(){this.files=[];this.items={add:f=>this.files.push(f)};}},File:class{constructor(b,n){this.name=n;}},Event:class{},
  intent:async()=>{st.intent++;return true;},submitted:()=>{st.submitted=true;},videoPayload:async v=>({ok:true,src:v.currentSrc}),retryAfter:()=>null};
 return {E:ctx.FruchtEngines,h,st,send,thumb,ratio,wide,res,dur,box,model,select};
}
const task=(extra={})=>({id:'t',kind:'engine_video',payload:{engine:'vidogrid',prompt:'One continuous shot, 10 seconds',seconds:10,...extra}});
const img=[{name:'scene0.jpg',data:'abc',mime:'image/jpeg'}];
(async()=>{
 const p=page();const r=await p.E.run(task(),img,p.h);
 assert.deepEqual(JSON.parse(JSON.stringify(r)),{ok:true,src:'https://cdn.vidogrid.ai/out/clip.mp4'},'new clip read, showcase video ignored');
 assert.equal(p.thumb.clicks,1,'image slot opened (element before « 0/1 »)');assert.equal(p.model.clicks,1,'Grok Lite chosen');
 assert.match(p.st.filled,/^Start exactly from @image1 .*10 seconds/);assert.equal(p.ratio.clicks,1);assert.equal(p.res.clicks,1);assert.equal(p.dur.clicks,1);assert.equal(p.wide.clicks,0);
 assert.equal(p.box.clicks,1,'unchecked box checked like the reference');assert.equal(p.st.intent,1);assert.equal(p.send.clicks,1,'sent exactly once');
 const w=page();await w.E.run(task({aspect:'16:9'}),img,w.h);assert.equal(w.wide.clicks,1);assert.equal(w.ratio.clicks,0,'horizontal episode: 16:9');
 const c=page({checked:true});await c.E.run(task(),img,c.h);assert.equal(c.box.clicks,0,'checked box left alone');
 const sel=page({fileField:false});await sel.E.run(task(),img,sel.h);assert.equal(sel.select.clicks,1,'« Select Files » when the page has no file field (the worker gives it the board)');
 const dry=page();const d=await dry.E.run(task({dry_run:true}),img,dry.h);assert.equal(d.dry_run,true);assert.equal(d.generation_submitted,false);assert.equal(dry.send.clicks,0);assert.equal(dry.st.intent,0);
 const out=page({loggedOut:true});const e1=await out.E.run(task(),img,out.h).then(()=>null,e=>e);assert.equal(e1.kind,'login');assert.match(e1.message,/Continue with Google.*Aucun envoi/);assert.equal(out.send.clicks,0);
 const stuck=page({importDone:false});const e2=await stuck.E.run(task(),img,stuck.h).then(()=>null,e=>e);
 assert.equal(e2.kind,'interface');assert.match(e2.message,/90 s.*Aucun envoi/);assert.equal(stuck.send.clicks,0,'import stuck 90 s: nothing sent');
 const nolite=page({lite:false});const e3=await nolite.E.run(task(),img,nolite.h).then(()=>null,e=>e);assert.equal(e3.kind,'interface');assert.equal(nolite.send.clicks,0);
 const failed=page({outcome:'failed'});const e4=await failed.E.run(task(),img,failed.h).then(()=>null,e=>e);
 assert.equal(e4.kind,'other');assert.match(e4.message,/STATUS 503/);assert.equal(failed.send.clicks,1,'one try only: never clicked again');
 const slow=page({outcome:'none'});const e5=await slow.E.run(task(),img,slow.h).then(()=>null,e=>e);assert.equal(e5.kind,'timeout');assert.match(e5.message,/7 minutes/);
 // Each clip starts from a freshly loaded Vidogrid page (the form keeps the last image).
 const updated=[];const chrome={tabs:{query:async()=>[{id:4,url:'https://vidogrid.ai/app/video-gen/grok?x=1',windowId:2}],update:async(id,d)=>{updated.push([id,d.url]);return {id,...d};}}};
 const ctx2={FruchtWorkspace:{adopt:async(c,t)=>t,createTab:async(c,d)=>({id:9,...d})},URL};vm.createContext(ctx2);vm.runInContext(code,ctx2);
 await ctx2.FruchtEngines.tabFor(task(),chrome);assert.deepEqual(updated,[[4,'https://vidogrid.ai/app/video-gen/grok']]);
 const manifest=JSON.parse(fs.readFileSync(path.join(__dirname,'../extension/manifest.json'),'utf8'));
 assert.ok(manifest.host_permissions.includes('https://vidogrid.ai/*'));
 // « Préparer mes comptes »: Vidogrid's sign-in page is « À régler », its app page « Prêt ».
 const rctx={};vm.createContext(rctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/readiness.js'),'utf8'),rctx);
 const R=rctx.FruchtReadiness,base={kind:'site',name:'vidogrid',host:'vidogrid.ai',expectedHosts:R.HOSTS.vidogrid,text:true};
 assert.equal(R.classify({...base,loggedOut:true}).state,'fix');assert.equal(R.classify({...base,loggedOut:false}).state,'ready');
 assert.equal(R.URLS.vidogrid,'https://vidogrid.ai/app/video-gen/grok');
 // Flow import: 90 s without any visible change ends the wait, nothing sent.
 const fctx={};vm.createContext(fctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/flow-controls.js'),'utf8'),fctx);
 const flow=fctx.FruchtFlow;let ticks=0;
 const fdoc={body:{innerText:'Import'},querySelectorAll:()=>[],querySelector:()=>null};
 const e6=await flow.confirmImport(fdoc,async()=>{ticks++;},()=>{},'board.png').then(()=>null,e=>e);
 assert.match(e6.message,/rien ne progresse depuis 90 s.*Aucun envoi/);assert.ok(ticks<=200,'given up after about 90 s, not 5 min ('+ticks+' pauses)');
 console.log('Vidogrid (fixture) : Grok Lite, image en @image1, 9:16/16:9, 720p, 10 s, envoi unique, essai à blanc, connexion, import bloqué 90 s, échec 503 sans nouvel essai, délai 7 min, page rechargée par clip ; import Flow sans progrès abandonné à 90 s.');
})().catch(e=>{console.error(e);process.exitCode=1;});
