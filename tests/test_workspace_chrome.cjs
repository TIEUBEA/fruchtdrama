// P5-1 in a real browser: Chromium loads the unpacked extension; the service worker opens the
// FruchtDrama window, creates a provider tab inside it and moves a foreign tab into it.
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),{spawn,execFileSync}=require('node:child_process');
const browser=['chromium','chromium-browser'].map(n=>{try{return execFileSync('which',[n]).toString().trim();}catch{return '';}}).find(Boolean);
if(!browser||typeof WebSocket==='undefined'){console.log('Fenêtre unique en navigateur réel ignorée : Chromium ou WebSocket indisponible.');process.exit(0);}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function waitFor(fn,timeout,label){const end=Date.now()+timeout;while(Date.now()<end){try{const v=await fn();if(v)return v;}catch{}await sleep(200);}throw Error('Délai dépassé : '+label);}
(async()=>{
 // Snap-confined Chromium cannot read /tmp nor hidden folders: work in a visible home folder.
 const temp=fs.mkdtempSync(path.join(os.homedir(),'frucht-ws-test-')),profile=path.join(temp,'profile'),ext=path.join(temp,'extension');
 fs.cpSync(path.join(__dirname,'../extension'),ext,{recursive:true});
 const chrome=spawn(browser,['--headless=new','--no-sandbox','--no-first-run','--disable-gpu','--remote-debugging-port=0','--user-data-dir='+profile,'--load-extension='+ext,'--disable-extensions-except='+ext,'about:blank'],{stdio:'ignore'});
 try{
  const port=await waitFor(()=>fs.readFileSync(path.join(profile,'DevToolsActivePort'),'utf8').split('\n')[0],20000,'Chromium');
  const worker=await waitFor(async()=>(await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find(t=>t.type==='service_worker'&&t.url.endsWith('/background.js')),20000,'service worker');
  const ws=new WebSocket(worker.webSocketDebuggerUrl);await new Promise((ok,ko)=>{ws.onopen=ok;ws.onerror=ko;});
  let n=0;const pending=new Map();ws.onmessage=e=>{const m=JSON.parse(e.data);if(pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);}};
  const run=expression=>new Promise((resolve,reject)=>{const id=++n;pending.set(id,m=>m.result?.exceptionDetails?reject(Error(JSON.stringify(m.result.exceptionDetails))):resolve(m.result?.result?.value));ws.send(JSON.stringify({id,method:'Runtime.evaluate',params:{expression,awaitPromise:true,returnByValue:true}}));});
  const before=await run('chrome.windows.getAll().then(w=>w.length)');
  const id=await run('FruchtWorkspace.open(chrome)');
  assert.equal(await run('chrome.windows.getAll().then(w=>w.length)'),before+1,'one new window');
  const tabs=await run(`chrome.tabs.query({windowId:${id}}).then(t=>t.map(x=>({url:x.pendingUrl||x.url,pinned:x.pinned})))`);
  assert.equal(tabs.length,1);assert.match(tabs[0].url,/^http:\/\/127\.0\.0\.1:8840\//);
  assert.equal(await run('FruchtWorkspace.open(chrome)'),id,'second click: same window');
  assert.equal(await run('chrome.windows.getAll().then(w=>w.length)'),before+1,'no duplicate window');
  const created=await run(`FruchtWorkspace.createTab(chrome,{url:'about:blank#provider',active:false}).then(t=>t.windowId)`);
  assert.equal(created,id,'provider tab inside the window');
  const moved=await run(`chrome.windows.create({url:'about:blank#foreign'}).then(w=>chrome.tabs.query({windowId:w.id})).then(t=>FruchtWorkspace.adopt(chrome,t[0])).then(t=>chrome.tabs.get(t.id)).then(t=>t.windowId)`);
  assert.equal(moved,id,'foreign tab moved into the window');
  await run(`chrome.windows.remove(${id})`);await sleep(500);
  assert.equal(await run(`chrome.storage.local.get('workspaceWindow').then(x=>x.workspaceWindow??null)`),null,'closing the window forgets it');
  ws.close();
  console.log('Fenêtre unique vérifiée dans Chromium réel : fenêtre dédiée ouverte sur le studio seul (aucun onglet passerelle), onglets créés et déplacés dedans, oubli à la fermeture.');
 }finally{chrome.kill('SIGKILL');await sleep(300);fs.rmSync(temp,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1;});
