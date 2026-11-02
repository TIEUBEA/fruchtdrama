// Public DOM identity only. No passwords, cookies, or authentication automation.
globalThis.FruchtFlowSession={
 project(value){
  try{const u=new URL(value),m=u.pathname.match(/^((?:\/u\/\d+)?\/project\/[a-zA-Z0-9_-]+)(?:\/edit\/[a-zA-Z0-9_-]+)?\/?$/);
   return u.protocol==='https:'&&['flow.google.com','labs.google'].includes(u.hostname)&&!u.username&&!u.password&&!u.port&&!u.search&&!u.hash&&m?u.origin+m[1]:null;
  }catch{return null;}
 },
 home(value){const url=this.project(value);if(!url)return null;const u=new URL(url);return u.origin+u.pathname.split('/project/')[0]+'/';},
 identity(doc){
  const emails=new Set();
  for(const b of doc.querySelectorAll('button,[role="button"]')){
   if(!b.getClientRects().length)continue;
   const label=b.getAttribute('aria-label')||'';
   if(!/\bGoogle\b/i.test(label))continue;
   const found=label.match(/[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g)||[];
   for(const email of found)emails.add(email.toLowerCase());
  }
  return emails.size===1?[...emails][0]:null;
 },
 describe(doc){
  const url=this.project(doc.location?.href),email=this.identity(doc);
  return url&&email?{url,email}:null;
 },
 verify(doc,target){
  const actual=this.describe(doc);
  return !!actual&&actual.url===this.project(target?.url)&&actual.email===target?.email?.toLowerCase();
 },
 newProject(doc,target,task){
  const home=this.home(target?.url);if(!home||doc.location?.href!==home||this.identity(doc)!==target.email?.toLowerCase())throw Error('Compte Flow non confirmé sur la page d’accueil. Reconnexion nécessaire.');
  const buttons=[...doc.querySelectorAll('button,[role="button"]')].filter(b=>b.getClientRects().length&&!b.disabled&&b.getAttribute('aria-disabled')!=='true');
  const candidates=buttons.filter(b=>[b.getAttribute('aria-label'),b.innerText].filter(Boolean).some(v=>/^(?:Nouveau projet|Créer un projet|New project|Create project|Neues Projekt|Projekt erstellen|Nuevo proyecto|Novo projeto|Nuovo progetto)$/i.test(v.replace(/^(?:add|add_2|add_circle)\s+/i,'').trim())));
  if(candidates.length!==1)throw Error('Bouton Nouveau projet absent ou ambigu ; aucun projet créé.');
  this.projectRequests=this.projectRequests||{};
  if(!this.projectRequests[task]){this.projectRequests[task]=true;candidates[0].click();}
  return {ok:true};
 },
 async prepareProject(task,tab,chrome,pause){
  const target=task.payload.flow_route,key=task.job+':'+task.profile;
  const saved=(await chrome.storage.local.get('flowProjects')).flowProjects||{};
  // chrome.tabs.update may still report the previous URL while navigating: return the remembered project.
  if(saved[key]&&this.home(saved[key])===this.home(target.url))return {...await chrome.tabs.update(tab.id,{url:saved[key],active:true}),url:saved[key]};
  const home=this.home(target.url);await chrome.tabs.update(tab.id,{url:home,active:true});
  let requested=false,lastError='';
  for(let i=0;i<180;i++){
   const current=await chrome.tabs.get(tab.id);
   const project=this.project(current.url);
   if(requested&&project&&this.home(project)===home){
    saved[key]=project;await chrome.storage.local.set({flowProjects:saved});return current;
   }
   if(!requested&&current.url===home){
    try{
     await chrome.scripting.executeScript({target:{tabId:tab.id},files:['flow-session.js']});
     const reply=await chrome.tabs.sendMessage(tab.id,{type:'frucht-flow-new-project',target,task:task.id});
     if(reply?.ok)requested=true;else lastError=reply?.error||'';
    }catch(e){lastError=e.message;}
   }
   await pause(500);
  }
  throw Error('Ouverture du nouveau projet Flow non terminée. '+lastError);
 },
 async tabFor(task,chrome){
  const target=task.payload?.flow_route;if(!target)throw Error('Compte Flow non enregistré.');
  const url=this.project(target.url);if(!url)throw Error('Adresse Flow enregistrée invalide.');
  const tabs=await chrome.tabs.query({url:['https://labs.google/*','https://flow.google.com/*']});
  let tab=tabs.find(t=>this.project(t.url)===url);
  if(!tab){
   const saved=(await chrome.storage.local.get('flowTab')).flowTab;
   // Reuse only the tab previously owned by this connector.
   const owned=tabs.find(t=>t.id===saved);
   tab=owned?await chrome.tabs.update(owned.id,{url,active:true}):await chrome.tabs.create({url,active:true});
  }
  await chrome.storage.local.set({flowTab:tab.id});return tab;
 }
};
try{if(globalThis.fruchtSessionHandler)chrome.runtime.onMessage.removeListener(globalThis.fruchtSessionHandler);}catch{}
globalThis.fruchtSessionHandler=(m,s,reply)=>{
 if(m.type==='frucht-flow-session'){reply(FruchtFlowSession.describe(document));return false;}
 if(m.type==='frucht-flow-verify'){reply({ok:FruchtFlowSession.verify(document,m.target)});return false;}
 if(m.type==='frucht-flow-new-project'){
  try{reply(FruchtFlowSession.newProject(document,m.target,m.task));}catch(e){reply({ok:false,error:e.message});}return false;
 }
 return false;
};
chrome.runtime.onMessage.addListener(globalThis.fruchtSessionHandler);
