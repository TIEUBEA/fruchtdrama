// Owner report 04/11/2026: « Se connecter » opened ChatGPT, the owner was signed in, and nothing happened.
// Now the tab is watched: once signed in, the card turns green, the tab the studio opened closes, the studio is back.
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
(async()=>{
 const store={client:'c1',token:'t'},calls=[],tabs=new Map(),windows=new Map([[7,{id:7}]]),listener={addListener:()=>{}};
 let next=100,signedIn=false;
 tabs.set(1,{id:1,windowId:7,url:'http://127.0.0.1:8840/#page=connections',active:true});
 const chrome={storage:{local:{get:async key=>key==null?{...store}:Array.isArray(key)?Object.fromEntries(key.map(k=>[k,store[k]])):{[key]:store[key]},set:async d=>Object.assign(store,d),remove:async k=>{delete store[k];}}},
  tabs:{query:async q=>[...tabs.values()].filter(t=>(q.windowId===undefined||t.windowId===q.windowId)&&(!q.url||String(t.url).startsWith(String(q.url).replace(/\*$/,'')))),
   get:async id=>{if(!tabs.has(id))throw Error('No tab');return tabs.get(id);},
   create:async d=>{const t={id:next++,...d};if(t.active)for(const o of tabs.values())if(o.windowId===t.windowId)o.active=false;tabs.set(t.id,t);return t;},
   update:async(id,d)=>{const t=tabs.get(id);if(d.active)for(const o of tabs.values())if(o.windowId===t.windowId)o.active=false;return Object.assign(t,d);},
   remove:async ids=>{for(const id of [].concat(ids))tabs.delete(id);},move:async(id,d)=>Object.assign(tabs.get(id),d),onUpdated:listener},
  windows:{get:async id=>windows.get(id),update:async()=>{},create:async()=>{throw Error('no new window expected');},onRemoved:listener},
  scripting:{executeScript:async({func,args})=>func?[{result:{connected:signedIn,email:signedIn?'owner@example.com':null,challenge:false,site:args[0]}}]:[]},
  runtime:{onInstalled:listener,onStartup:listener,onMessage:listener,getURL:p=>'chrome-extension://x/'+p},alarms:{onAlarm:listener}};
 const fetch=async(url,init)=>{calls.push([url,init?.body?JSON.parse(init.body):null]);return {ok:true,json:async()=>({ok:true})};};
 const context=vm.createContext({chrome,URL,Date,setTimeout,fetch});
 for(const f of ['workspace.js','sites.js','recovery.js','background-worker.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/'+f),'utf8'),context);
 await vm.runInContext("openLogin('chatgpt')",context);
 const login=[...tabs.values()].find(t=>t.url==='https://chatgpt.com/');
 assert.ok(login&&login.windowId===7&&login.active,'opened in the FruchtDrama window, in view so the owner can sign in');
 await vm.runInContext('watchLogins()',context);
 assert.ok(tabs.has(login.id),'not signed in yet: the tab stays');assert.equal(calls.length,0);
 signedIn=true;await vm.runInContext('watchLogins()',context);
 const sites=calls.find(c=>c[0].endsWith('/api/bridge/sites'));
 assert.deepEqual(sites[1].sites.chatgpt.connected,true);assert.equal(sites[1].partial,true,'only this card changes');
 assert.ok(calls.some(c=>c[0].endsWith('/api/bridge/notice')&&/ChatGPT connecté/.test(c[1].text)));
 assert.ok(!tabs.has(login.id),'the tab it opened is closed');assert.equal(tabs.get(1).active,true,'the studio is back on screen');
 assert.equal(Object.keys(store.pendingLogins).length,0);
 // An owner's existing tab is reused and kept open.
 signedIn=false;tabs.set(50,{id:50,windowId:7,url:'https://grok.com/imagine',active:false});
 await vm.runInContext("openLogin('grok')",context);assert.equal(tabs.get(50).active,true);
 signedIn=true;await vm.runInContext('watchLogins()',context);
 assert.ok(tabs.has(50),'owner tab kept');assert.equal(tabs.get(1).active,true);
 // « Ajouter un compte Google » (no Flow credits left): Google's page in the window, then detection by itself.
 context.FruchtFlowScan={scan:async()=>[{slot:3,email:'new@example.com',balance:50}]};
 calls.length=0;await vm.runInContext('addGoogle()',context);
 const g=[...tabs.values()].find(t=>String(t.url).startsWith('https://accounts.google.com/AddSession'));
 assert.ok(g&&g.windowId===7&&g.active,'Google add-account page in view');
 await vm.runInContext('watchGoogle()',context);assert.ok(tabs.has(g.id),'still signing in: kept');
 g.url='https://flow.google.com/u/3/';await vm.runInContext('watchGoogle()',context);
 assert.ok(!tabs.has(g.id),'closed once Google sends it on to Flow');assert.equal(tabs.get(1).active,true,'studio back');
 const scan=calls.find(c=>c[0].endsWith('/api/bridge/flow-scan'));assert.equal(scan[1].accounts[0].email,'new@example.com','accounts detected again');
 console.log('Se connecter : onglet dans la fenêtre FruchtDrama, connexion détectée seule, carte mise à jour, onglet refermé, retour au studio.');
})().catch(e=>{console.error(e);process.exitCode=1;});
