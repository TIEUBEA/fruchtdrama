// One dedicated window for the studio and every provider tab (P5-1).
// Clicking the extension icon opens (or refocuses) this window; ChatGPT, Claude, Flow, TikTok,
// Grok and Arena tabs are created inside it, and tabs found elsewhere are moved into it.
globalThis.FruchtWorkspace={
 STUDIO:'http://127.0.0.1:8840/',
 settingsUrl(chrome){return chrome.runtime.getURL('popup.html');},
 async windowId(chrome){
  const {workspaceWindow}=await chrome.storage.local.get('workspaceWindow');
  if(!Number.isInteger(workspaceWindow))return null;
  try{const w=await chrome.windows.get(workspaceWindow);return w?.id??null;}catch{return null;}
 },
 // Create the window on demand: a task never runs in a random window of the browser.
 async ensure(chrome,{focus=false}={}){
  let id=await this.windowId(chrome);
  if(id===null){
   // Like the Atelier: the window opens on the studio only; accounts and gateway live in its Mes comptes page.
   const w=await chrome.windows.create({url:this.STUDIO,focused:true,type:'normal'});
   id=w.id;await chrome.storage.local.set({workspaceWindow:id});
  }else if(focus)await chrome.windows.update(id,{focused:true});
  return id;
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
  return chrome.tabs.create({...props,windowId});
 },
 // A reused tab (registered Flow project, previous research tab) is moved into the window, session intact.
 async adopt(chrome,tab){
  if(!tab)return tab;
  const windowId=await this.ensure(chrome);
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
 async closed(chrome,windowId){
  const {workspaceWindow}=await chrome.storage.local.get('workspaceWindow');
  if(workspaceWindow===windowId)await chrome.storage.local.remove('workspaceWindow');
 },
 // Window ids do not survive a browser restart and may be reused by another window.
 async reset(chrome){await chrome.storage.local.remove('workspaceWindow');}
};
