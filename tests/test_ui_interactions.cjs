// Real interaction test: studio server + headless Chrome driven through the DevTools protocol.
// Covers P1-1 in the browser: an unsaved story correction survives the periodic refresh, then Save and Approve.
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),net=require('node:net'),{spawn,execFileSync}=require('node:child_process');
const root=path.join(__dirname,'..');
const chromePath=['google-chrome','chromium','chromium-browser'].map(name=>{try{return execFileSync('which',[name]).toString().trim();}catch{return '';}}).find(Boolean);
if(!chromePath||typeof WebSocket==='undefined'){console.log('Interactions navigateur ignorées : Chrome ou WebSocket indisponible.');process.exit(0);}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const freePort=()=>new Promise(resolve=>{const s=net.createServer();s.listen(0,'127.0.0.1',()=>{const p=s.address().port;s.close(()=>resolve(p));});});
async function waitFor(fn,timeout=20000,label='condition'){const end=Date.now()+timeout;while(Date.now()<end){try{const v=await fn();if(v)return v;}catch{}await sleep(150);}throw Error('Délai dépassé : '+label);}

(async()=>{
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),'frucht-ui-')),data=path.join(temp,'data');fs.mkdirSync(data);
 const now=new Date().toISOString(),job='c1b2c3d4e5f60718';
 const scenes=[0,1].map(i=>({characters:['orange'],meaning:'Moment '+i,image_prompt:'p',video_prompt:'v',dialogue:[{speaker:'orange',text:'Hallo'}]}));
 fs.writeFileSync(path.join(data,'state.json'),JSON.stringify({version:1,token:'t',pair_code:'abcd1234',profiles:[],clients:{},tasks:[],
  settings:{provider:'chatgpt',language:'Deutsch (de-DE)',scene_count:4,clip_seconds:8,flow_model:'gemini_omni_flash',flow_resolution:'720p',flow_cost:12,query:'q',daily_budget:50},
  jobs:[{id:job,title:'Histoire QA',brief:'b',stage:'characters',status:'waiting_review',created:now,updated:now,events:[],candidates:[],flow_profile:null,
   config:{provider:'chatgpt',scene_count:2,language:'Deutsch (de-DE)',flow_model:'gemini_omni_flash',flow_cost:12,review_script:true},
   characters:[{id:'orange',name:'Oma',appearance:'a',voice:'v',image_prompt:'p'}],scenes,
   script:{title:'Histoire QA',cover_title:'WER FÄHRT?',description:'Beschreibung',characters:[{id:'orange',name:'Oma',appearance:'a',voice:'v',image_prompt:'p'}],scenes}}]}));
 const port=await freePort(),base='http://127.0.0.1:'+port;
 const server=spawn('python3',[path.join(root,'server.py')],{cwd:root,env:{...process.env,FRUCHT_DATA:data,FRUCHT_PORT:String(port)},stdio:'ignore'});
 let chrome;
 const cleanup=()=>{try{chrome?.kill('SIGKILL');}catch{}try{server.kill();}catch{}try{fs.rmSync(temp,{recursive:true,force:true});}catch{}};
 try{
  await waitFor(async()=>(await fetch(base+'/api/state')).ok,15000,'serveur');
  const profile=path.join(temp,'chrome');
  chrome=spawn(chromePath,['--headless=new','--disable-gpu','--no-sandbox','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,'--window-size=1300,1800','about:blank'],{stdio:'ignore'});
  const devtools=await waitFor(()=>{try{return fs.readFileSync(path.join(profile,'DevToolsActivePort'),'utf8').split('\n')[0];}catch{return null;}},15000,'Chrome');
  const target=await waitFor(async()=>(await (await fetch(`http://127.0.0.1:${devtools}/json/list`)).json()).find(t=>t.type==='page'),10000,'onglet');
  const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise((ok,ko)=>{ws.onopen=ok;ws.onerror=ko;});
  let id=0;const pending=new Map();const dialogs=[];
  ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);}if(m.method==='Page.javascriptDialogOpening'){dialogs.push(m.params.message);send('Page.handleJavaScriptDialog',{accept:true});}};
  const send=(method,params={})=>new Promise(r=>{const n=++id;pending.set(n,r);ws.send(JSON.stringify({id:n,method,params}));});
  const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.result?.exceptionDetails)throw Error(JSON.stringify(r.result.exceptionDetails));return r.result?.result?.value;};
  await send('Page.enable');await send('Runtime.enable');
  const errors=[];
  await send('Page.navigate',{url:base+'/#job='+job});
  await waitFor(()=>evaluate("!!document.querySelector('#scriptReview')"),15000,'éditeur');

  // 1. Unsaved correction survives a refresh triggered by a real state change.
  await evaluate(`(()=>{const i=document.querySelector('#scriptReview [data-scene="1"]');i.value='Bis morgen, Oma.';i.dispatchEvent(new Event('input',{bubbles:true}));document.activeElement.blur();return true})()`);
  await fetch(base+'/api/flow-auto',{method:'POST',headers:{'Content-Type':'application/json',Origin:base},body:JSON.stringify({enabled:true})});
  await sleep(5000);
  assert.equal(await evaluate(`document.querySelector('#scriptReview [data-scene="1"]').value`),'Bis morgen, Oma.','unsaved correction kept across refresh');

  // 2. Save writes to the server.
  await evaluate(`document.querySelector('[data-action="saveScript"]').click()`);
  await waitFor(async()=>(await (await fetch(base+'/api/state')).json()).jobs[0].script.scenes[1].dialogue[0].text==='Bis morgen, Oma.',10000,'enregistrement');

  // 3. An invalid correction is refused with a visible message and nothing changes on the server.
  await evaluate(`(()=>{const i=document.querySelector('#scriptReview [data-field="title"]');i.value='   ';i.dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('[data-action="saveScript"]').click();return true})()`);
  await waitFor(()=>evaluate(`document.querySelector('#toast').textContent.includes('Titre')`),5000,'message d’erreur');
  assert.equal((await (await fetch(base+'/api/state')).json()).jobs[0].title,'Histoire QA');

  // 4. Navigation with unsaved changes asks for confirmation.
  await evaluate(`document.querySelector('nav [data-page="guide"]').click()`);await sleep(300);
  assert.ok(dialogs.some(m=>m.includes('ne sont pas enregistrées')),'confirmation before discarding');
  await evaluate(`document.querySelector('nav [data-page="studio"]').click()`);
  await waitFor(()=>evaluate("!!document.querySelector('#scriptReview')"),10000,'retour éditeur');

  // 5. Approve starts the images.
  await evaluate(`document.querySelector('[data-action="approveScript"]').click()`);
  const state=await waitFor(async()=>{const s=await (await fetch(base+'/api/state')).json();return s.jobs[0].script_approved&&s;},10000,'validation');
  assert.equal(state.jobs[0].status,'running');assert.deepEqual(state.tasks.filter(t=>t.status==='queued').map(t=>t.slot),['character:orange']);
  await waitFor(()=>evaluate("!document.querySelector('#scriptReview')"),10000,'éditeur fermé');
  assert.deepEqual(errors,[]);ws.close();
  console.log('Interactions navigateur : correction conservée au rafraîchissement, enregistrement, refus visible, confirmation de sortie et validation vérifiés.');
 }finally{cleanup();}
})().catch(e=>{console.error(e);process.exitCode=1;});
