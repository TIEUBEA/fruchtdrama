// One dedicated window for the studio and every provider tab (P5-1).
// Clicking the extension icon opens (or refocuses) this window; ChatGPT, Claude, Flow, TikTok,
// Grok tabs are created inside it, and tabs found elsewhere are moved into it.
globalThis.FruchtWorkspace={
 STUDIO:'http://127.0.0.1:8840/',
 settingsUrl(chrome){return chrome.runtime.getURL('popup.html');},
 async windowId(chrome){
  const {workspaceWindow}=await chrome.storage.local.get('workspaceWindow');
  if(Number.isInteger(workspaceWindow)){try{const w=await chrome.windows.get(workspaceWindow);if(w?.id!=null)return w.id;}catch{}}
  // One window only (like the Atelier): a studio page already open somewhere becomes the window, no new one.
  const studio=await this.studioTab(chrome);
  if(studio&&Number.isInteger(studio.windowId)){await chrome.storage.local.set({workspaceWindow:studio.windowId});return studio.windowId;}
  return null;
 },
 // The studio page, wherever it is (filtered here: no match pattern with a port, localhost accepted).
 isStudio(url){return /^http:\/\/(127\.0\.0\.1|localhost):8840\//.test(String(url||''));},
 async studioTab(chrome,windowId){
  const tabs=await chrome.tabs.query(windowId===undefined?{}:{windowId});
  return tabs.filter(t=>this.isStudio(t.url||t.pendingUrl)).sort((a,b)=>(b.active-a.active)||((b.lastAccessed||0)-(a.lastAccessed||0)))[0]||null;
 },
 // Create the window on demand: a task never runs in a random window of the browser.
 // Single flight (owner report 04/11/2026, several windows on « Revérifier »): checks running at the same
 // time all wait for the same window instead of each creating one.
 async ensure(chrome,{focus=false}={}){
  if(!this._ensuring)this._ensuring=this._ensure(chrome,focus).finally(()=>{this._ensuring=null;});
  const {id,created}=await this._ensuring;
  if(focus&&!created)await chrome.windows.update(id,{focused:true});
  return id;
 },
 async _ensure(chrome,focus=false){
  const id=await this.windowId(chrome);
  if(id!==null)return {id,created:false};
  // Like the Atelier: the window opens on the studio only; accounts and gateway live in its Mes comptes page.
  // Opened for a task (not by the owner's click): it never takes the foreground (owner, 06/11/2026: « on doit rester
  // dans l'onglet FruchtDrama, ce qui se passe à côté ne nous concerne pas »).
  const w=await chrome.windows.create({url:this.STUDIO,focused:!!focus,type:'normal'});
  await chrome.storage.local.set({workspaceWindow:w.id});
  return {id:w.id,created:true};
 },
 // Icon click: show the studio (one tab, no gateway tab).
 async open(chrome){
  const id=await this.ensure(chrome,{focus:true});
  const tabs=await chrome.tabs.query({windowId:id});
  const url=t=>t.url||t.pendingUrl||'';
  // Older versions pinned a gateway tab: close it, its controls are now in the studio.
  const old=tabs.filter(t=>url(t).startsWith(this.settingsUrl(chrome))).map(t=>t.id);
  if(old.length)await chrome.tabs.remove(old);
  const studio=tabs.find(t=>url(t).startsWith(this.STUDIO));
  if(studio)await chrome.tabs.update(studio.id,{active:true});
  else await chrome.tabs.create({windowId:id,url:this.STUDIO,active:true});
  return id;
 },
 async createTab(chrome,props){
  const windowId=await this.ensure(chrome);
  return this.keep(chrome,await chrome.tabs.create({active:false,...props,windowId}));
 },
 // A tab working in the background must not be unloaded by Chrome's memory saver in the middle of a task.
 async keep(chrome,tab){
  try{if(tab?.id!=null&&chrome.tabs.update)await chrome.tabs.update(tab.id,{autoDiscardable:false});}catch{}
  return tab;
 },
 // Close finished tabs without moving the owner's view: if one of them is on screen, the studio comes back first.
 async close(chrome,ids){
  ids=(ids||[]).filter(Number.isInteger);if(!ids.length)return;
  let tabs=[];try{tabs=await Promise.all(ids.map(id=>chrome.tabs.get(id).catch(()=>null)));}catch{}
  const shown=tabs.find(t=>t?.active);
  if(shown){
   const studio=await this.studioTab(chrome,shown.windowId);
   if(studio&&!ids.includes(studio.id))await chrome.tabs.update(studio.id,{active:true});
  }
  await chrome.tabs.remove(ids);
 },
 // A reused tab (registered Flow project, previous research tab) is moved into the window, session intact.
 async adopt(chrome,tab){
  if(!tab)return tab;
  const windowId=await this.ensure(chrome);
  await this.keep(chrome,tab);
  if(tab.windowId===windowId)return tab;
  await chrome.tabs.move(tab.id,{windowId,index:-1});
  return {...tab,windowId};
 },
 // The tab the owner looked at last in the window (replaces "active tab of the current window",
 // which is now the gateway tab itself).
 async latest(chrome,pattern){
  const windowId=await this.windowId(chrome);
  const tabs=(await chrome.tabs.query(windowId===null?{}:{windowId})).filter(t=>pattern.test(t.url||''));
  return tabs.sort((a,b)=>(b.lastAccessed||0)-(a.lastAccessed||0))[0]||null;
 },
 // Background reading (balances, refill) waits while the owner has closed the window: never reopen it for that.
 async isOpen(chrome){return (await this.windowId(chrome))!==null;},
 async closed(chrome,windowId){
  const {workspaceWindow}=await chrome.storage.local.get('workspaceWindow');
  if(workspaceWindow===windowId)await chrome.storage.local.remove('workspaceWindow');
 },
 // Window ids do not survive a browser restart and may be reused by another window.
 async reset(chrome){await chrome.storage.local.remove('workspaceWindow');}
};
