// Each generation opens a fresh conversation; close its verified tab after studio acknowledgement.
globalThis.FruchtChats={
 provider(task){return task.kind==='chat_image'?'chatgpt':task.payload?.provider==='claude'?'claude':'chatgpt';},
 isAI(task){return ['chat_text','chat_image','chat_collect','chat_image_collect'].includes(task?.kind);},
 key(task){return task.job+':'+this.provider(task);},
 allowed(value,provider){try{const u=new URL(value);return u.protocol==='https:'&&u.hostname===(provider==='claude'?'claude.ai':'chatgpt.com')&&!u.username&&!u.password;}catch{return false;}},
 conversation(value,provider){
  if(!this.allowed(value,provider))return null;
  const u=new URL(value),pattern=provider==='claude'?/^\/chat\/[a-zA-Z0-9-]+$/:/^\/c\/[a-zA-Z0-9-]+$/;
  return pattern.test(u.pathname)?u.origin+u.pathname:null;
 },
 context(doc,prompt,provider){
  const url=this.conversation(doc.location?.href,provider);
  return url&&globalThis.FruchtMedia?.matches(doc,prompt)?{url}:null;
 },
 busy(doc){
  const editor=globalThis.FruchtComposer?.editor(doc);
  if(String(editor?.value||editor?.innerText||'').trim())return true;
  return [...doc.querySelectorAll('button')].some(b=>b.getClientRects().length&&(b.getAttribute('data-testid')==='stop-button'||/^(?:Stop generating|Stop streaming|Arrêter|Arrêter la génération|Anhalten|Generierung stoppen)$/i.test(b.getAttribute('aria-label')||'')));
 },
 async tabFor(task,cfg,chrome){
  const provider=this.provider(task);
  // No reuse or navigation of a previous conversation. Recovery keeps active.tabId.
  return globalThis.FruchtWorkspace.createTab(chrome,{url:provider==='claude'?'https://claude.ai/new':'https://chatgpt.com/',active:false});
 },
 async queueClose(active,chrome){
  if(!this.isAI(active.task))return;
  const data=await chrome.storage.local.get('completedAITabs');
  const pending=data.completedAITabs||[];
  if(!pending.some(x=>x.task.id===active.task.id&&x.tabId===active.tabId))pending.push({task:active.task,tabId:active.tabId,client:active.client});
  await chrome.storage.local.set({completedAITabs:pending});
 },
 async closeCompleted(chrome){
  const data=await chrome.storage.local.get(['completedAITabs','client']);
  const pending=data.completedAITabs||[];
  for(const active of [...pending]){
   if(active.client!==data.client)continue;
   let tab;
   try{tab=await chrome.tabs.get(active.tabId);}catch{tab=null;}
   const provider=this.provider(active.task);
   if(tab&&this.allowed(tab.url,provider)){
    try{
     await chrome.scripting.executeScript({target:{tabId:tab.id},files:['composer.js','media.js','chat-session.js']});
     const owned=await chrome.tabs.sendMessage(tab.id,{type:'frucht-chat-owned',provider,tasks:[{id:active.task.id,job:active.task.job,kind:active.task.kind,prompt:active.task.payload.prompt}]});
     // A repurposed tab or a user draft is left open. Never close an unrelated chat.
     if(owned?.task===active.task.id&&!owned.busy&&this.conversation(owned.url,provider))await globalThis.FruchtWorkspace.close(chrome,[tab.id]);
    }catch{
     await chrome.storage.local.set({status:'Résultat enregistré ; fermeture de son onglet IA en attente. Nouvelle tâche différée.'});
     return false;
    }
   }
   pending.splice(pending.indexOf(active),1);
   await chrome.storage.local.set({completedAITabs:pending});
  }
  return true;
 },
 async tidy(cfg,tasks,chrome){
  const completed=tasks.filter(t=>t.client===cfg.client&&t.status==='done'&&['chat_text','chat_image'].includes(t.kind));
  const protectedTabs=new Set(Object.values(cfg.scenarioTabs||{}).filter(x=>x.pending).map(x=>x.tabId));
  if(cfg.activeTask)protectedTabs.add(cfg.activeTask.tabId);
  const tabs=await chrome.tabs.query({url:['https://chatgpt.com/*','https://claude.ai/*']});
  const verified=[];
  for(const tab of tabs){
   const provider=this.allowed(tab.url,'claude')?'claude':'chatgpt';
   const candidates=completed.filter(t=>this.provider(t)===provider).map(t=>({id:t.id,job:t.job,kind:t.kind,prompt:t.payload.prompt}));
   if(!candidates.length||!this.conversation(tab.url,provider))continue;
   try{
    await chrome.scripting.executeScript({target:{tabId:tab.id},files:['composer.js','media.js','chat-session.js']});
    const match=await chrome.tabs.sendMessage(tab.id,{type:'frucht-chat-owned',tasks:candidates,provider});
    const task=candidates.find(t=>t.id===match?.task);
    if(task&&this.conversation(match.url,provider)){
     if(match.busy)protectedTabs.add(tab.id);
     verified.push({tab,provider,task,url:match.url,busy:!!match.busy});
    }
   }catch{}
  }
  const keep=protectedTabs;
  const close=verified.filter(x=>!keep.has(x.tab.id)).map(x=>x.tab.id);
  if(close.length)await globalThis.FruchtWorkspace.close(chrome,close);
  return {ok:true,closed:close.length,recognized:verified.length,message:close.length+' onglet(s) fermé(s), '+verified.length+' onglet(s) du studio reconnu(s). Conversations conservées ; onglets non identifiés laissés ouverts.'};
 }
};
try{if(globalThis.fruchtChatHandler)chrome.runtime.onMessage.removeListener(globalThis.fruchtChatHandler);}catch{}
globalThis.fruchtChatHandler=(m,s,reply)=>{
 if(m.type==='frucht-chat-context'){reply(FruchtChats.context(document,m.prompt,m.provider));return false;}
 if(m.type==='frucht-chat-owned'){
  const matches=m.tasks.filter(t=>FruchtMedia.matches(document,t.prompt));
  if(new Set(matches.map(t=>t.job)).size!==1){reply(null);return false;}
  const match=matches.find(t=>t.kind==='chat_text')||matches[0];
  reply(match?{task:match.id,url:FruchtChats.conversation(document.location?.href,m.provider),busy:FruchtChats.busy(document)}:null);return false;
 }
 return false;
};
chrome.runtime.onMessage.addListener(globalThis.fruchtChatHandler);
