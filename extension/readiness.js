// « Préparer mes comptes » (owner 06/11/2026): each useful service and each Google Flow account is read in a background
// tab of the FruchtDrama window, like ready() does before a task: page of the expected site, editor present, no sign-in
// page, no anti-robot check. Read only: no prompt is typed or sent, no credit is spent, no check is bypassed.
// A tab that needs the owner (sign-in, anti-robot check) stays open in the background; « Régler maintenant » shows it.
globalThis.FruchtReadiness={
 HOSTS:{chatgpt:['chatgpt.com'],claude:['claude.ai'],grok:['grok.com'],arena:['arena.ai','lmarena.ai'],vidogrid:['vidogrid.ai','www.vidogrid.ai'],flow:['flow.google.com','labs.google']},
 URLS:{chatgpt:'https://chatgpt.com/',claude:'https://claude.ai/new',grok:'https://grok.com/imagine',arena:'https://arena.ai/video',vidogrid:'https://vidogrid.ai/app/video-gen/grok'},
 EDITOR:['chatgpt','claude','grok'],
 // Pure: what the page shows -> Prêt / À régler (reason) / Pas d'accès.
 classify(info){
  info=info||{};
  const fix=reason=>({state:'fix',reason});
  if(info.unavailable)return {state:'no_access',reason:'Ce compte Google n’a pas accès à Flow'};
  if(info.challenge)return fix('Vérification anti-robot à faire : résous-la toi-même dans l’onglet');
  if(info.host&&info.expectedHosts&&!info.expectedHosts.includes(info.host))return fix(/accounts\.google|auth|login/i.test(info.host)?'Connexion requise':'Page inattendue ('+info.host+') : connexion ou blocage');
  if(info.signIn)return fix('Connexion requise');
  // Vidogrid shows no « Sign in » button: its sign-in page or a page without credits means not signed in.
  if(info.name==='vidogrid'&&info.loggedOut)return fix('Connexion requise : clique « Continue with Google » toi-même');
  if(info.kind==='flow'){
   if(!info.email)return fix('Connexion Google requise : aucun compte lu sur la page');
   if(info.expectedEmail&&info.email!==info.expectedEmail)return fix('Autre compte Google ouvert à cette place : clique « Détecter mes comptes »');
   if(!info.home&&!info.editor)return fix(info.text?'Projet Flow sans zone de saisie (page vide ou bloquée)':'Page vide');
   return {state:'ready',reason:''};
  }
  if(!info.text)return fix('Page vide ou bloquée');
  if(this.EDITOR.includes(info.name)&&!info.editor)return fix('Zone de saisie absente : connexion requise ou page bloquée');
  return {state:'ready',reason:''};
 },
 // Runs inside the tab (composer.js, sites.js and flow-session.js injected first).
 read(doc,name){
  const visibleEditor=[...doc.querySelectorAll('textarea:not([disabled]),[contenteditable="true"]')].some(el=>el.getClientRects().length>0);
  const site=name!=='flow'&&globalThis.FruchtSites?FruchtSites.probe(name,doc):{};
  const labels=[...doc.querySelectorAll('button,a,[role="button"]')].filter(b=>b.getClientRects().length).map(b=>[b.getAttribute('aria-label'),b.innerText].filter(Boolean).join(' ').replace(/\s+/g,' ').trim());
  const signIn=labels.some(l=>/^(log in|sign in|se connecter|connexion|anmelden|einloggen)$/i.test(l));
  return {editor:visibleEditor,signIn:name==='flow'?false:signIn&&!site.connected,challenge:!!globalThis.FruchtComposer?.challenge(doc),
   loggedOut:name==='vidogrid'&&site.connected===false,email:name==='flow'?(globalThis.FruchtFlowSession?.identity(doc)||null):(site.email||null),text:String(doc.body?.innerText||'').trim().length>0,
   ready:['interactive','complete'].includes(doc.readyState)};
 },
 hostOf(url){try{return new URL(url).hostname;}catch{return '';}},
 async probeTab(chrome,tabId,name){
  await chrome.scripting.executeScript({target:{tabId},files:['composer.js','sites.js','flow-session.js','readiness.js']});
  const [r]=await chrome.scripting.executeScript({target:{tabId},func:n=>globalThis.FruchtReadiness.read(document,n),args:[name]});
  return r?.result||{};
 },
 // One page: wait for it, read it a few times (a page still loading looks empty), classify.
 async look(chrome,tab,name,extra,wait,tries=6){
  let info={},verdict={state:'fix',reason:'Page vide'};
  for(let k=0;k<tries;k++){
   let current;try{current=await chrome.tabs.get(tab.id);}catch{return {verdict:{state:'fix',reason:'Onglet fermé pendant la vérification'},info};}
   const host=this.hostOf(current.url||current.pendingUrl);
   info={kind:name==='flow'?'flow':'site',name,host,expectedHosts:this.HOSTS[name],unavailable:/\/unavailable(?:[/?#]|$)/.test(current.url||''),...extra};
   if(this.HOSTS[name].includes(host)&&!info.unavailable){try{Object.assign(info,await this.probeTab(chrome,tab.id,name));}catch{}}
   verdict=this.classify(info);
   if(verdict.state!=='fix'||info.challenge||(k>=2&&!this.HOSTS[name].includes(host)))break;
   await wait(3000);
  }
  return {verdict,info};
 },
 async keep(chrome,key,tabId){const {readinessTabs={}}=await chrome.storage.local.get('readinessTabs');readinessTabs[key]=tabId;await chrome.storage.local.set({readinessTabs});},
 async forget(chrome,key){const {readinessTabs={}}=await chrome.storage.local.get('readinessTabs');if(key in readinessTabs){delete readinessTabs[key];await chrome.storage.local.set({readinessTabs});}},
 async site(chrome,ws,name,wait){
  const hosts=this.HOSTS[name],tabs=await chrome.tabs.query({});
  let tab=tabs.find(t=>hosts.includes(this.hostOf(t.url||t.pendingUrl))),opened=false;
  if(!tab){tab=await ws.createTab(chrome,{url:this.URLS[name],active:false});opened=true;await wait(6000);}
  const {verdict,info}=await this.look(chrome,tab,name,{},wait);
  if(verdict.state==='ready'){await this.forget(chrome,'site:'+name);if(opened)try{await ws.close(chrome,[tab.id]);}catch{}}
  else await this.keep(chrome,'site:'+name,tab.id);
  return {...verdict,email:info.email||null,challenge:!!info.challenge,connected:verdict.state==='ready'};
 },
 async profile(chrome,ws,target,wait){
  const tab=await ws.createTab(chrome,{url:target.url,active:false});
  for(let i=0;i<30;i++){await wait(500);let t;try{t=await chrome.tabs.get(tab.id);}catch{break;}if(t.status==='complete')break;}
  await wait(2500);
  const {verdict,info}=await this.look(chrome,tab,'flow',{expectedEmail:target.email,home:!!target.home},wait,5);
  let balance=null;
  if(verdict.state==='ready'){
   // Same reading as « Détecter mes comptes »: the account panel only, nothing bought or created.
   try{
    await chrome.scripting.executeScript({target:{tabId:tab.id},files:['flow-session.js','flow-credits.js','flow-scan.js']});
    const [r]=await chrome.scripting.executeScript({target:{tabId:tab.id},func:async()=>globalThis.FruchtFlowScan.read(document,ms=>new Promise(r=>setTimeout(r,ms)))});
    if(Number.isInteger(r?.result?.balance))balance=r.result.balance;
   }catch{}
  }
  if(verdict.state==='fix')await this.keep(chrome,'flow:'+target.id,tab.id);
  else{await this.forget(chrome,'flow:'+target.id);try{await ws.close(chrome,[tab.id]);}catch{}}
  return {...verdict,email:info.email||null,...(balance!==null?{balance}:{})};
 },
 // Service worker: a request from the studio -> report.
 async run(chrome,ws,request,wait=ms=>new Promise(r=>setTimeout(r,ms))){
  const report={id:request.id,sites:{},profiles:{}};
  for(const name of request.sites||[]){
   if(!this.HOSTS[name])continue;
   try{report.sites[name]=await this.site(chrome,ws,name,wait);}catch(e){report.sites[name]={state:'fix',reason:'Vérification interrompue : '+String(e.message||e).slice(0,120)};}
  }
  for(const target of request.profiles||[]){
   try{report.profiles[target.id]=await this.profile(chrome,ws,target,wait);}catch(e){report.profiles[target.id]={state:'fix',reason:'Vérification interrompue : '+String(e.message||e).slice(0,120)};}
  }
  return report;
 },
 // « Régler maintenant » (the owner clicked): the tab concerned comes to the front, nothing else.
 async show(chrome,ws,item){
  const key=item.site?'site:'+item.site:'flow:'+item.profile?.id;
  const {readinessTabs={}}=await chrome.storage.local.get('readinessTabs');
  let tab=null;
  if(Number.isInteger(readinessTabs[key]))try{tab=await chrome.tabs.get(readinessTabs[key]);}catch{tab=null;}
  if(!tab&&item.site){const tabs=await chrome.tabs.query({});tab=tabs.find(t=>(this.HOSTS[item.site]||[]).includes(this.hostOf(t.url||t.pendingUrl)))||null;}
  const url=item.site?this.URLS[item.site]:item.profile?.url;
  if(!tab&&!url)return false;
  if(tab){tab=await ws.adopt(chrome,tab);await chrome.tabs.update(tab.id,{active:true});}
  else tab=await ws.createTab(chrome,{url,active:true});
  await this.keep(chrome,key,tab.id);
  await chrome.windows.update(tab.windowId,{focused:true}).catch(()=>{});
  return true;
 }
};
