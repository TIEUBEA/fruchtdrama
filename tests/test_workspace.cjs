// P5-1: a single FruchtDrama window. Icon click opens/refocuses it; every provider tab lives inside it.
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
function harness(){
 const store={},windows=new Map(),tabs=new Map(),log=[];let nextWin=1,nextTab=100;
 const tab=(windowId,data)=>{const t={id:nextTab++,windowId,active:false,pinned:false,lastAccessed:nextTab,...data};tabs.set(t.id,t);return t;};
 const chrome={runtime:{getURL:p=>'chrome-extension://ext/'+p},
  storage:{local:{get:async k=>({[k]:store[k]}),set:async d=>Object.assign(store,d),remove:async k=>{delete store[k];}}},
  windows:{get:async id=>{if(!windows.has(id))throw Error('No window');return windows.get(id);},
   create:async d=>{const w={id:nextWin++,...d};windows.set(w.id,w);log.push('window');for(const url of [].concat(d.url))tab(w.id,{url,active:true});return w;},
   update:async(id,d)=>{log.push('focus:'+id);return Object.assign(windows.get(id),d);}},
  tabs:{query:async q=>[...tabs.values()].filter(t=>q.windowId===undefined||t.windowId===q.windowId),
   create:async d=>{log.push('tab:'+d.url);return tab(d.windowId,d);},
   update:async(id,d)=>Object.assign(tabs.get(id),d),
   remove:async ids=>{for(const id of [].concat(ids)){log.push('remove:'+id);tabs.delete(id);}},
   move:async(id,d)=>{log.push('move:'+id);tabs.get(id).windowId=d.windowId;return tabs.get(id);}}};
 const ctx={chrome};vm.createContext(ctx);
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/workspace.js'),'utf8'),ctx);
 return {ws:ctx.FruchtWorkspace,chrome,store,windows,tabs,log,tab};
}
(async()=>{
 const h=harness();
 // 1. Icon click: one new window with the studio only (no gateway tab, like the Atelier).
 const id=await h.ws.open(h.chrome);
 assert.equal(h.windows.size,1);assert.equal(h.store.workspaceWindow,id);
 const inWindow=[...h.tabs.values()].filter(t=>t.windowId===id);
 assert.deepEqual(inWindow.map(t=>t.url),['http://127.0.0.1:8840/']);assert.ok(inWindow[0].active,'studio shown');
 // 1 bis. A gateway tab left by an older version is closed on the next click.
 const old=h.tab(id,{url:'chrome-extension://ext/popup.html',pinned:true});
 // 2. Second click: same window refocused, nothing duplicated.
 await h.ws.open(h.chrome);
 assert.ok(h.log.includes('remove:'+old.id),'old gateway tab closed');
 assert.equal(h.windows.size,1);assert.equal([...h.tabs.values()].length,1);assert.ok(h.log.includes('focus:'+id));
 // 3. Provider tabs are created inside the window.
 const chat=await h.ws.createTab(h.chrome,{url:'https://chatgpt.com/',active:true});assert.equal(chat.windowId,id);
 // 4. A registered Flow tab found in another window is moved in, session intact (same tab id).
 const other=h.tab(99,{url:'https://flow.google.com/u/1/project/p1'});
 const adopted=await h.ws.adopt(h.chrome,other);
 assert.equal(adopted.id,other.id);assert.equal(h.tabs.get(other.id).windowId,id);assert.ok(h.log.includes('move:'+other.id));
 assert.equal(await h.ws.adopt(h.chrome,adopted),adopted,'already inside: untouched');
 // 5. "Latest" replaces the active tab of the current window (now the gateway tab).
 h.tabs.get(chat.id).url='https://chatgpt.com/c/abc';h.tabs.get(chat.id).lastAccessed=1e9;
 assert.equal((await h.ws.latest(h.chrome,/^https:\/\/chatgpt\.com\//)).id,chat.id);
 assert.equal((await h.ws.latest(h.chrome,/flow\.google\.com\/.*\/project\//)).id,other.id);
 assert.equal(await h.ws.latest(h.chrome,/claude\.ai/),null);
 // 5 bis. Real check 02/11/2026: Flow project URLs without /u/N must be found too.
 const worker2=fs.readFileSync(path.join(__dirname,'../extension/background-worker.js'),'utf8');
 const FLOW_PROJECT=eval(worker2.match(/const FLOW_PROJECT=(\/.*\/);/)[1]);
 for(const u of ['https://flow.google.com/project/0d99','https://flow.google.com/u/1/project/x','https://labs.google/fx/tools/flow/project/y'])assert.ok(FLOW_PROJECT.test(u),u);
 assert.ok(!FLOW_PROJECT.test('https://flow.google.com/about'));
 // 6. Window closed by the owner: forgotten, then recreated on the next task (never a random window).
 h.windows.delete(id);await h.ws.closed(h.chrome,id);assert.equal(h.store.workspaceWindow,undefined);
 const again=await h.ws.createTab(h.chrome,{url:'https://grok.com/imagine'});
 assert.notEqual(again.windowId,id);assert.equal(h.store.workspaceWindow,again.windowId);assert.equal(h.windows.size,1);
 // 7. A stale id after a browser restart is cleared.
 await h.ws.reset(h.chrome);assert.equal(h.store.workspaceWindow,undefined);
 // 8. Manifest: the icon opens the window (no popup), and the worker loads the workspace first.
 const manifest=JSON.parse(fs.readFileSync(path.join(__dirname,'../extension/manifest.json'),'utf8'));
 assert.equal(manifest.action.default_popup,undefined,'a popup would prevent action.onClicked');
 assert.match(fs.readFileSync(path.join(__dirname,'../extension/background.js'),'utf8'),/importScripts\('workspace\.js'/);
 const worker=fs.readFileSync(path.join(__dirname,'../extension/background-worker.js'),'utf8');
 assert.match(worker,/action\?\.onClicked\?\.addListener\(\(\)=>FruchtWorkspace\.open/);
 assert.doesNotMatch(worker,/chrome\.tabs\.create\(/,'no tab created outside the window');
 assert.doesNotMatch(worker,/currentWindow:true/,'no dependence on the focused window');
 for(const file of ['chat-session.js','flow-session.js','flow-credits.js'])
  assert.doesNotMatch(fs.readFileSync(path.join(__dirname,'../extension/'+file),'utf8'),/chrome\.tabs\.create\(/,file);
 console.log('Fenêtre unique : ouverture au clic, recentrage sans doublon, onglets créés dedans, onglet Flow déplacé avec sa session, recréation après fermeture.');
})().catch(e=>{console.error(e);process.exitCode=1;});
