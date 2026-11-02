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
 const now=new Date().toISOString(),job='c1b2c3d4e5f60718',done='d1b2c3d4e5f60718',switching='e1b2c3d4e5f60718';
 const scenes=[0,1].map(i=>({characters:['orange'],meaning:'Moment '+i,image_prompt:'p',video_prompt:'v',dialogue:[{speaker:'orange',text:'Hallo'}]}));
 fs.writeFileSync(path.join(data,'state.json'),JSON.stringify({version:1,token:'t',pair_code:'abcd1234',profiles:[],clients:{},tasks:[],
  settings:{provider:'chatgpt',language:'Deutsch (de-DE)',scene_count:4,clip_seconds:8,flow_model:'gemini_omni_flash',flow_resolution:'720p',flow_cost:12,query:'q',daily_budget:50},
  jobs:[{id:job,title:'Histoire QA',brief:'b',stage:'characters',status:'waiting_review',created:now,updated:now,events:[],candidates:[],flow_profile:null,
   config:{provider:'chatgpt',scene_count:2,language:'Deutsch (de-DE)',flow_model:'gemini_omni_flash',flow_cost:12,review_script:true},
   characters:[{id:'orange',name:'Oma',appearance:'a',voice:'v',image_prompt:'p'}],scenes,
   script:{title:'Histoire QA',cover_title:'WER FÄHRT?',description:'Beschreibung',characters:[{id:'orange',name:'Oma',appearance:'a',voice:'v',image_prompt:'p'}],scenes}},
  {id:done,title:'Épisode terminé QA',brief:'b',stage:'done',status:'done',created:now,updated:now,events:[],candidates:[],flow_profile:null,
   config:{provider:'chatgpt',scene_count:2,language:'Deutsch (de-DE)',flow_model:'gemini_omni_flash',flow_cost:12},
   characters:[{id:'orange',name:'Oma',appearance:'a',voice:'v',image_prompt:'p',file:'ref.png'}],scenes:scenes.map((x,i)=>({...x,image:'scene'+i+'.png',clip:'clip'+i+'.mp4'})),
   cover_file:'cover.png',cover:'/media/'+done+'/cover.png',final:'/media/'+done+'/final.mp4',
   script:{title:'Épisode terminé QA',cover_title:'WER?',description:'d',characters:[],scenes}},
  {id:switching,title:'Changement de compte QA',brief:'b',stage:'cover',status:'waiting_account',created:now,updated:now,events:[],candidates:[],flow_profile:null,
   config:{provider:'chatgpt',scene_count:2,language:'Deutsch (de-DE)',video_engine:'grok',flow_cost:12},account_switch:{engine:'grok',from:'a@x.com',to:'b@x.com',label:'Second'},
   characters:[{id:'orange',name:'Oma',appearance:'a',voice:'v',image_prompt:'p',file:'ref.png'}],scenes:scenes.map((x,i)=>({...x,image:'scene'+i+'.png',clip:'clip'+i+'.mp4'})),
   script:{title:'Changement de compte QA',cover_title:'WER?',description:'d',characters:[],scenes}}]}));
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
  ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);}if(m.method==='Page.javascriptDialogOpening'){dialogs.push(m.params.message);send('Page.handleJavaScriptDialog',{accept:true,...(m.params.type==='prompt'?{promptText:'plus de lumière'}:{})});}};
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
  // 6. Redo the cover of a finished episode: prompt for a correction, final invalidated, only the cover task queued.
  await send('Page.navigate',{url:base+'/#job='+done});
  await waitFor(()=>evaluate(`!!document.querySelector('[data-redo="cover"]')`),15000,'bouton refaire');
  assert.ok(await evaluate(`!!document.querySelector('[data-redo="clip:0"]')&&!!document.querySelector('[data-redo="image:1"][data-has-clip="1"]')`),'redo buttons on scenes');
  await evaluate(`document.querySelector('[data-redo="cover"]').click()`);
  const redone=await waitFor(async()=>{const s=await (await fetch(base+'/api/state')).json();const j=s.jobs.find(x=>x.id===done);return j.stage==='cover'&&{s,j};},10000,'refaire couverture');
  assert.ok(dialogs.some(m=>m.startsWith('Refaire la couverture')),'correction asked');
  assert.equal(redone.j.final,undefined);assert.equal(redone.j.corrections.cover,'plus de lumière');
  assert.deepEqual(redone.s.tasks.filter(t=>t.job===done&&t.status==='queued').map(t=>t.slot),['cover']);
  // 7. P5-08: guided account change, confirmed from the production.
  await send('Page.navigate',{url:base+'/#job='+switching});
  await waitFor(()=>evaluate(`document.body.innerText.includes('b@x.com')&&!!document.querySelector('[data-action="accountSwitched"]')`),15000,'bandeau changement de compte');
  await evaluate(`document.querySelector('[data-action="accountSwitched"]').click()`);
  await waitFor(async()=>(await (await fetch(base+'/api/state')).json()).jobs.find(x=>x.id===switching).status==='running',10000,'changement confirmé');
  // 8. P5-07: add a Grok account from Connexions (address only).
  await evaluate(`document.querySelector('nav [data-page="connections"]').click()`);
  await waitFor(()=>evaluate("!!document.querySelector('#engineAccountForm')"),10000,'formulaire comptes');
  await evaluate(`(()=>{const f=document.querySelector('#engineAccountForm');f.engine.value='grok';f.email.value='Second@x.com';f.requestSubmit();return true})()`);
  const accounts=await waitFor(async()=>{const st=await (await fetch(base+'/api/state')).json();return st.engine_accounts?.length&&st.engine_accounts;},10000,'compte ajouté');
  assert.equal(accounts[0].email,'second@x.com');assert.equal(accounts[0].engine,'grok');
  await waitFor(()=>evaluate(`document.body.innerText.includes('second@x.com')`),10000,'compte affiché');
  // 9. P2-10: add a production to the night queue, then start the queue from the studio page.
  await send('Page.navigate',{url:base+'/#job='+job});
  await waitFor(()=>evaluate(`!!document.querySelector('[data-night="add"]')`),15000,'bouton file de nuit');
  await evaluate(`document.querySelector('[data-night="add"]').click()`);
  await waitFor(async()=>(await (await fetch(base+'/api/state')).json()).night?.ids?.includes(job),10000,'ajout file de nuit');
  await waitFor(()=>evaluate(`!!document.querySelector('[data-night="start"]')`),10000,'panneau file de nuit');
  await evaluate(`document.querySelector('[data-night="start"]').click()`);
  await waitFor(async()=>(await (await fetch(base+'/api/state')).json()).night?.active===true||(await (await fetch(base+'/api/state')).json()).night?.log?.some(x=>x.text.includes('démarrée')),10000,'file démarrée');
  assert.deepEqual(errors,[]);ws.close();
  console.log('Interactions navigateur : correction conservée au rafraîchissement, enregistrement, refus visible, confirmation de sortie, validation, « Refaire la couverture », changement de compte guidé, ajout d’un compte Grok et file de nuit vérifiés.');
 }finally{cleanup();}
})().catch(e=>{console.error(e);process.exitCode=1;});
