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
 const now=new Date().toISOString(),job='c1b2c3d4e5f60718',done='d1b2c3d4e5f60718',switching='e1b2c3d4e5f60718',castDraft='f1b2c3d4e5f60718';
 const scenes=[0,1].map(i=>({characters:['orange'],meaning:'Moment '+i,image_prompt:'p',video_prompt:'v',dialogue:[{speaker:'orange',text:'Hallo'}]}));
 fs.writeFileSync(path.join(data,'state.json'),JSON.stringify({version:1,token:'t',pair_code:'abcd1234',sites:{chatgpt:{connected:true,email:'olga@example.com',checked:now}},profiles:[],clients:{},tasks:[],
  settings:{provider:'chatgpt',language:'Deutsch (de-DE)',scene_count:4,clip_seconds:8,flow_model:'gemini_omni_flash',flow_resolution:'720p',flow_cost:12,query:'q',daily_budget:50},
  jobs:[{id:job,title:'Histoire QA',brief:'b',stage:'characters',status:'waiting_review',created:now,updated:now,events:[],candidates:[],flow_profile:null,
   config:{provider:'chatgpt',scene_count:2,language:'Deutsch (de-DE)',flow_model:'gemini_omni_flash',flow_cost:12,review_script:true},
   characters:[{id:'orange',name:'Oma',appearance:'a',voice:'v',image_prompt:'p'}],scenes,
   script:{title:'Histoire QA',cover_title:'WER FÄHRT?',description:'Beschreibung',characters:[{id:'orange',name:'Oma',appearance:'a',voice:'v',image_prompt:'p'}],scenes}},
  {id:done,title:'Épisode terminé QA',brief:'b',stage:'done',status:'done',created:now,updated:now,events:[],candidates:[{url:'https://www.tiktok.com/@oma/video/4242424242',title:'Oma Orange verliert ihren Kuchen #fruitdrama #oma',views:1200000,metric_kind:'views',age_days:2,score:600000,basis:'vues/jour'}],flow_profile:null,
   config:{provider:'chatgpt',scene_count:2,language:'Deutsch (de-DE)',flow_model:'gemini_omni_flash',flow_cost:12},
   characters:[{id:'orange',name:'Oma',appearance:'a',voice:'v',image_prompt:'p',file:'ref.png'}],scenes:scenes.map((x,i)=>({...x,image:'scene'+i+'.png',clip:'clip'+i+'.mp4'})),
   cover_file:'cover.png',cover:'/media/'+done+'/cover.png',final:'/media/'+done+'/final.mp4',
   script:{title:'Épisode terminé QA',cover_title:'WER?',description:'d',characters:[],scenes}},
  {id:switching,title:'Changement de compte QA',brief:'b',stage:'cover',status:'waiting_account',created:now,updated:now,events:[],candidates:[],flow_profile:null,
   config:{provider:'chatgpt',scene_count:2,language:'Deutsch (de-DE)',video_engine:'grok',flow_cost:12},account_switch:{engine:'grok',from:'a@x.com',to:'b@x.com',label:'Second'},
   characters:[{id:'orange',name:'Oma',appearance:'a',voice:'v',image_prompt:'p',file:'ref.png'}],scenes:scenes.map((x,i)=>({...x,image:'scene'+i+'.png',clip:'clip'+i+'.mp4'})),
   script:{title:'Changement de compte QA',cover_title:'WER?',description:'d',characters:[],scenes}},
  {id:castDraft,title:'Personnages à dessiner QA',brief:'b',stage:'script',status:'paused',created:now,updated:now,events:[],candidates:[],flow_profile:null,character_sheet:1,
   config:{provider:'chatgpt',scene_count:2,language:'Deutsch (de-DE)',flow_model:'gemini_omni_flash',flow_cost:12,characters_detail:'simple'},
   characters:[{id:'orange',name:'Oma',appearance:'a',voice:'v',image_prompt:'p'},{id:'kiwi',name:'Kiko',appearance:'k',voice:'v',image_prompt:'p'}],scenes,
   script:{title:'Personnages à dessiner QA',cover_title:'WER?',description:'d',characters:[],scenes}}]}));
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
  await evaluate(`document.querySelector('[data-page="guide"]').click()`);
  await waitFor(()=>dialogs.some(m=>m.includes('ne sont pas enregistrées')),5000,'confirmation before discarding');
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
  // Owner request: larger type, large images, click to enlarge.
  assert.ok(await evaluate(`parseFloat(getComputedStyle(document.body).fontSize)>=16`),'body text at least 16 px');
  assert.ok(await evaluate(`parseFloat(getComputedStyle(document.querySelector('.episode-title p')).fontSize)>=14`),'secondary text at least 14 px');
  // Atelier-like episode page: step cards, a wall of scenes; a scene opens its board and clip side by side.
  assert.equal(await evaluate(`document.querySelectorAll('.tracker .track').length`),5,'five step cards');
  assert.equal(await evaluate(`document.querySelectorAll('.scene-wall .scene-tile').length`),2,'one tile per scene');
  await evaluate(`document.querySelectorAll('.scene-tile[data-scene-open]')[1].click()`);
  await waitFor(()=>evaluate(`!!document.querySelector('#sceneBox[open] .scene-pair img')&&!!document.querySelector('#sceneBox[open] .scene-pair video')`),5000,'planche et clip côte à côte');
  const sizes=await evaluate(`JSON.stringify([...document.querySelectorAll('#sceneBox .scene-pair img,#sceneBox .scene-pair video')].map(i=>Math.round(i.getBoundingClientRect().width)))`);
  assert.ok(JSON.parse(sizes).every(w=>w>=200),'board and clip shown large '+sizes);
  assert.ok(await evaluate(`!!document.querySelector('#sceneBox [data-redo="clip:1"]')&&!!document.querySelector('#sceneBox [data-redo="image:1"][data-has-clip="1"]')`),'redo buttons in the scene');
  await evaluate(`document.querySelector('[data-scene-close]').click()`);
  await waitFor(()=>evaluate(`!document.querySelector('#sceneBox[open]')`),5000,'fermeture');
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
  // 7 bis. Interface: a Grok production shows its engine, not the Flow profile selector.
  assert.ok(await evaluate(`document.querySelector('#jobProfile').closest('label').hidden`),'Flow selector hidden for a Grok episode');
  // 8. P5-07: add a Grok account from Connexions (address only).
  await evaluate(`document.querySelector('nav [data-page="connections"]').click()`);
  // 0.1.74: Mes comptes keeps technical settings folded in « Avancé », opened here as the owner would.
  await sleep(400);await evaluate(`document.querySelector('[data-fold="advanced"]:not([open])>summary')?.click()`);
  await waitFor(()=>evaluate("!!document.querySelector('#accountForm')"),10000,'formulaire comptes');
  await evaluate(`(()=>{const f=document.querySelector('#accountForm');f.email.value='Second@x.com';[...f.querySelectorAll('[name=services]')].forEach(c=>c.checked=c.value==='grok');f.requestSubmit();return true})()`);
  const accounts=await waitFor(async()=>{const st=await (await fetch(base+'/api/state')).json();return st.engine_accounts?.length&&st.engine_accounts;},10000,'compte ajouté');
  assert.equal(accounts[0].email,'second@x.com');assert.equal(accounts[0].engine,'grok');
  await evaluate(`document.querySelector('[data-account-tab="limits"]').click()`);
  await waitFor(()=>evaluate(`document.body.innerText.includes('second@x.com')`),10000,'compte affiché');
  // 9. P2-10: add a production to the night queue, then start the queue from the studio page.
  await send('Page.navigate',{url:base+'/#job='+job});
  await waitFor(()=>evaluate(`!!document.querySelector('[data-night="add"]')`),15000,'bouton file de nuit');
  await evaluate(`document.querySelector('[data-night="add"]').click()`);
  await waitFor(async()=>(await (await fetch(base+'/api/state')).json()).night?.ids?.includes(job),10000,'ajout file de nuit');
  // Atelier-like navigation: part page → story page → Studio (stories with their next action).
  await evaluate(`document.querySelector('[data-back-story]').click()`);
  await waitFor(()=>evaluate(`!!document.querySelector('.story-card.add')&&document.body.innerText.includes('Les parties')`),10000,'page de l’histoire');
  // Owner report 04/11/2026: clicking a part card (an article, not a button) must open the episode and its progress.
  await evaluate(`document.querySelector('.story-card.part[data-job]').click()`);
  await waitFor(()=>evaluate(`!!document.querySelector('.detail.episode')&&location.hash.startsWith('#job=')`),10000,'partie ouverte au clic');
  await evaluate(`document.querySelector('[data-back-story]').click()`);
  await waitFor(()=>evaluate(`document.body.innerText.includes('Les parties')`),10000,'retour à l’histoire');
  await evaluate(`document.querySelector('[data-back-studio]').click()`);
  await waitFor(()=>evaluate(`document.querySelectorAll('.story-grid .story-card').length>=1&&document.body.innerText.includes('Tes histoires et leurs parties')`),10000,'Studio par histoires');
  await waitFor(()=>evaluate(`!!document.querySelector('[data-night="start"]')`),10000,'panneau file de nuit');
  await evaluate(`document.querySelector('[data-night="start"]').click()`);
  await waitFor(async()=>(await (await fetch(base+'/api/state')).json()).night?.active===true||(await (await fetch(base+'/api/state')).json()).night?.log?.some(x=>x.text.includes('démarrée')),10000,'file démarrée');
  // 10. Interface: the guide lists every new feature; the creation form hides Flow-only fields for Grok.
  await evaluate(`document.querySelector('[data-page="guide"]').click()`);
  const guideText=await waitFor(()=>evaluate(`document.querySelector('.guide-new')?.innerText`),10000,'guide');
  for(const word of ['Fenêtre FruchtDrama','Trois moteurs vidéo','Changement de compte','File de nuit','Séries et publication','Assistance'])assert.ok(guideText.includes(word),word);
  assert.match(guideText,/version 0\.1\.\d+/);
  // 10 bis. Full-page creation like the Atelier: fixed durations, engine choice, ten stories first.
  await evaluate(`document.querySelector('nav [data-action="new"]').click()`);
  await waitFor(()=>evaluate(`!!document.querySelector('#createForm.create-page')`),5000,'page Créer');
  await evaluate(`document.querySelector('[data-choice="engine"][data-value="grok"]').click()`);
  assert.ok(await evaluate(`document.querySelector('#createForm .flow-settings').hidden`),'Flow settings hidden for Grok');
  await evaluate(`document.querySelector('[data-choice="engine"][data-value="flow"]').click()`);
  assert.ok(await evaluate(`!document.querySelector('#createForm .flow-settings').hidden`),'Flow settings back');
  await evaluate(`document.querySelector('[data-choice="duration"][data-value="180"]').click()`);
  assert.ok(await evaluate(`document.querySelector('#createForm').innerText.includes('23 plans de 8 s')`),'3 min = 23 clips of 8 s');
  await evaluate(`document.querySelector('[data-choice="duration"][data-value="60"]').click()`);
  await evaluate(`document.querySelector('#createForm').requestSubmit()`);
  const ideasJob=await waitFor(async()=>(await (await fetch(base+'/api/state')).json()).jobs.find(j=>j.stage==='ideas'),10000,'dix histoires demandées');
  assert.equal(ideasJob.config.scene_count,8);assert.equal(ideasJob.config.duration,60);
  await waitFor(()=>evaluate(`[...document.querySelectorAll('.ideas,.notice')].some(n=>n.innerText.includes('dix histoires'))`),10000,'page épisode : attente des histoires');
  assert.match(await waitFor(()=>evaluate(`document.querySelector('.run-clock')?.textContent`),5000,'chrono'),/^(\d+ h \d\d|\d+ min \d\d) de travail · en général \d+ à \d+ min$/,'running clock with the usual time');
  // 10 ter. Atelier lots 1-2: quality, format, characters, subtitles, cost confirmation, montage settings, backups.
  await evaluate(`document.querySelector('nav [data-action="new"]').click()`);
  await waitFor(()=>evaluate(`!!document.querySelector('#createForm.create-page')`),5000,'page Créer bis');
  for(const [group,value] of [['mode','idea'],['format','both'],['quality','economy'],['characters','detailed'],['subtitles','without']]){
   await evaluate(`document.querySelector('[data-choice="${group}"][data-value="${value}"]').click()`);
   assert.ok(await evaluate(`document.querySelector('[data-choice="${group}"][data-value="${value}"]').classList.contains('on')`),group+' chosen');}
  assert.ok(await evaluate(`document.querySelector('#createForm').innerText.includes('Montage : coupes franches')`),'montage summary on the creation page');
  const before=dialogs.length;
  await evaluate(`document.querySelector('#createForm [name=brief]').value='Une petite mangue découvre que sa sœur lui ment depuis dix ans.';document.querySelector('#createForm').requestSubmit()`);
  const both=await waitFor(async()=>(await (await fetch(base+'/api/state')).json()).jobs.find(j=>j.brief.startsWith('Une petite mangue')),10000,'épisode « Les deux » créé');
  assert.ok(dialogs.slice(before).some(t=>t.includes('On y va')&&t.includes('16:9')&&!t.includes('refaits au plus')),'cost confirmed before anything is spent (economy: no redo)');
  assert.deepEqual([both.config.quality,both.config.controls,both.config.also_horizontal,both.config.characters_detail,both.config.subtitles],['economy','report',true,'detailed',false]);
  await evaluate(`document.querySelector('nav [data-page="connections"]').click()`);
  // 0.1.74: Mes comptes keeps technical settings folded in « Avancé », opened here as the owner would.
  await sleep(400);await evaluate(`document.querySelector('[data-fold="advanced"]:not([open])>summary')?.click()`);
  for(const k of ['montage','backups','controls'])await waitFor(()=>evaluate(`(()=>{const d=document.querySelector('[data-fold="${k}"]');if(!d)return false;if(!d.open)d.querySelector('summary').click();return d.open})()`),10000,'bloc '+k+' ouvert');
  await waitFor(()=>evaluate(`!!document.querySelector('.montage-panel [data-montage-transition="fade_long"]')`),5000,'réglages du montage');
  await evaluate(`document.querySelector('[data-montage-transition="fade_long"]').click()`);
  await waitFor(async()=>(await (await fetch(base+'/api/state')).json()).montage.transition==='fade_long',5000,'fondu long enregistré');
  await waitFor(()=>evaluate(`!!document.querySelector('[data-montage-toggle="cut_silences"]')`),5000,'case silences');
  await evaluate(`document.querySelector('[data-montage-toggle="cut_silences"]').click()`);
  await waitFor(async()=>(await (await fetch(base+'/api/state')).json()).montage.cut_silences===false,5000,'silences gardés enregistrés');
  assert.ok(await waitFor(()=>evaluate(`document.querySelector('.montage-panel')?.innerText.includes('fondu long · coupes rapides · silences gardés')`),5000,'résumé du montage'));
  await evaluate(`document.querySelector('[data-backup="save"]').click()`);
  await waitFor(()=>evaluate(`document.querySelector('#toast')?.textContent==='Histoires sauvegardées'`),5000,'sauvegarde');
  await evaluate(`document.querySelector('[data-backup="restore"]').click()`);
  await waitFor(()=>evaluate(`document.querySelector('#toast')?.textContent==='Aucune histoire à remettre'`),5000,'rien à remettre : tout est déjà là');
  // 11. Atelier-like interface: dark theme by default, Le Filon, creation from a found video.
  assert.ok(await evaluate(`!document.body.classList.contains('dark')`),'light theme by default');
  await evaluate(`document.querySelector('#theme').click()`);assert.ok(await evaluate(`document.body.classList.contains('dark')`),'dark theme on demand');
  await evaluate(`document.querySelector('#theme').click()`);
  // 11 a. Apparence like the Atelier: seven palettes in cards (four colour dots), old names moved to their palette.
  assert.ok(await evaluate(`document.body.classList.contains('theme-papier')`),'Papier is the light default');
  await evaluate(`document.querySelector('nav [data-page="connections"]').click()`);
  await waitFor(()=>evaluate(`document.querySelectorAll('[data-fold="theme"] .palette').length===7`),10000,'sept palettes');
  assert.equal(await evaluate(`document.querySelector('[data-fold="theme"] .fold-title').textContent`),'Apparence');
  assert.deepEqual(await evaluate(`[...document.querySelectorAll('.palette b')].map(b=>b.textContent)`),['Ardoise','Laiton','Lagon','Cinéma','Papier','Verre','Éditorial']);
  assert.ok(await evaluate(`[...document.querySelectorAll('.palette')].every(p=>p.querySelectorAll('.swatches i').length===4&&p.querySelector('small').textContent.length>5)`),'four dots and a subtitle per palette');
  await evaluate(`document.querySelector('[data-theme-pick="cinema"]').click()`);
  await waitFor(()=>evaluate(`document.body.classList.contains('theme-cinema')&&document.body.classList.contains('dark')&&document.querySelector('[data-theme-pick="cinema"]').classList.contains('on')`),5000,'palette Cinéma');
  assert.equal(await evaluate(`localStorage.getItem('frucht-theme')`),'cinema');
  await evaluate(`localStorage.setItem('frucht-theme','dark');true`);await send('Page.reload',{});
  await waitFor(()=>evaluate(`!!document.body&&document.body.classList.contains('theme-ardoise')&&localStorage.getItem('frucht-theme')==='ardoise'`),15000,'ancien « Sombre » devenu Ardoise');
  await evaluate(`localStorage.setItem('frucht-theme','light');true`);await send('Page.reload',{});
  await waitFor(()=>evaluate(`!!document.body&&document.body.classList.contains('theme-papier')&&!document.body.classList.contains('dark')&&localStorage.getItem('frucht-theme')==='papier'`),15000,'ancien « Clair » devenu Papier');
  // 11 b. Personnages like the Atelier: compact pills that unfold; Simple | Détaillé switch; Refaire on the right.
  await send('Page.navigate',{url:base+'/#job='+done});
  await waitFor(()=>evaluate(`!!document.querySelector('.cast-head .seg-switch')&&!!document.querySelector('.cast-pill')`),15000,'pastilles des personnages');
  assert.ok(await evaluate(`document.querySelector('.cast-head .seg-switch.locked .on').textContent==='Simple'&&!document.querySelector('.cast-head [data-cast-detail]')`),'drawn cast: the switch only shows the level');
  assert.ok(await evaluate(`document.querySelector('.cast-head [data-redo="character:orange"]').textContent==='Refaire'`),'Refaire on the right');
  assert.ok(await evaluate(`(()=>{const d=document.querySelector('.cast-pill');return !d.open&&d.querySelector('summary').innerText.includes('OMA')&&!d.querySelector('.cast-more').checkVisibility()})()`),'folded pill: name only');
  await evaluate(`document.querySelector('.cast-pill summary').click()`);
  await waitFor(()=>evaluate(`(()=>{const d=document.querySelector('.cast-pill');return d.open&&d.querySelector('.cast-more').checkVisibility()&&!!d.querySelector('.cast-more img')&&d.querySelector('[data-upload="character:orange"]')?.textContent==='Remplacer'})()`),5000,'pastille dépliée : image, description, Remplacer');
  await evaluate(`render();true`);
  assert.ok(await evaluate(`document.querySelector('.cast-pill').open`),'unfolded pill survives the refresh');
  await send('Page.navigate',{url:base+'/#job='+castDraft});
  await waitFor(()=>evaluate(`!!document.querySelector('.cast-head [data-cast-detail="detailed"]')`),15000,'bascule Simple | Détaillé');
  await evaluate(`document.querySelector('[data-cast-detail="detailed"]').click()`);
  await waitFor(async()=>(await (await fetch(base+'/api/state')).json()).jobs.find(x=>x.id===castDraft).config.characters_detail==='detailed',10000,'niveau Détaillé enregistré');
  await waitFor(()=>evaluate(`document.querySelector('[data-cast-detail="detailed"]').classList.contains('on')`),10000,'Détaillé affiché');
  await evaluate(`document.querySelector('nav [data-page="filon"]').click()`);
  await waitFor(()=>evaluate(`document.querySelector('.filon-card')?.innerText.includes('1,2 M')`),10000,'Filon');
  assert.equal(await waitFor(()=>evaluate(`document.querySelector('.filon-card iframe.filon-player')?.src.split('?')[0]`),5000,'lecture automatique'),'https://www.tiktok.com/player/v1/4242424242','video plays by itself when visible');
  // 11 bis. Lot 5: niches (own search each), next refresh time, hashtags that carry, 6 h counts, stacked runs.
  assert.ok(await evaluate(`document.querySelector('.hashtags')?.innerText.includes('#fruitdrama')`),'hashtags bar');
  await evaluate(`document.querySelector('[data-filon-tag="#fruitdrama"]').click()`);
  assert.equal(await evaluate(`document.querySelector('#filonSearch').value`),'#fruitdrama','hashtag filters the videos');
  await evaluate(`document.querySelector('#filonSearch').value='';document.querySelector('#filonSearch').dispatchEvent(new Event('input',{bubbles:true}))`);
  await waitFor(()=>evaluate(`document.querySelectorAll('.filon-card').length>0`),5000,'Filon sans recherche');
  await evaluate(`document.querySelector('[data-niche-editor]').click()`);
  await waitFor(()=>evaluate(`!!document.querySelector('.niche-editor [data-niche-toggle="Animaux"]')`),5000,'éditeur de niches');
  await evaluate(`document.querySelector('[data-niche-toggle="Animaux"]').click()`);
  await waitFor(async()=>(await (await fetch(base+'/api/state')).json()).settings.filon_niches?.join()==='Fruits,Animaux',5000,'niche ajoutée');
  await waitFor(()=>evaluate(`!!document.querySelector('[data-filon-niche="Animaux"]')`),5000,'puce Animaux');
  await evaluate(`document.querySelector('[data-filon-niche="Animaux"]').click()`);
  await waitFor(()=>evaluate(`document.querySelector('.intro p')?.innerText.includes('niche animaux')&&!document.querySelector('.filon-card')`),5000,'Animaux : vidéos fruits masquées');
  await evaluate(`document.querySelector('[data-filon-refresh]').click()`);
  const filonJob=await waitFor(async()=>(await (await fetch(base+'/api/state')).json()).jobs.find(j=>j.filon_only&&j.config.filon_niche==='Animaux'),5000,'actualisation Animaux');
  assert.match(filonJob.config.query,/animal|Tiere|animaux/i,'niche has its own TikTok search');
  await evaluate(`document.querySelector('[data-filon-niche="Fruits"]').click()`);
  await waitFor(()=>evaluate(`document.querySelectorAll('.filon-card').length>0`),5000,'retour Fruits');
  await evaluate(`document.querySelector('nav [data-page="studio"]').click()`);
  // The episode then its story are open: go back level by level, like the owner would.
  await waitFor(async()=>{if(await evaluate(`!!document.querySelector('.quota-box')`))return true;await evaluate(`document.querySelector('[data-back-story],[data-back-studio]')?.click()`);return false;},8000,'liste du Studio');
  assert.equal(await waitFor(()=>evaluate(`[...document.querySelectorAll('.quota-box .qchip')].filter(x=>x.textContent.includes('en 6 h')).length`),5000,'compteurs 6 h'),3,'images, clips and videos made in 6 h');
  assert.ok(await waitFor(()=>evaluate(`document.querySelectorAll('#runWidget button').length>=2&&document.querySelector('#runWidget small').textContent.startsWith('EN COURS ·')`),5000,'pile des productions en cours'));
  await evaluate(`document.querySelector('nav [data-page="filon"]').click()`);
  await waitFor(()=>evaluate(`document.querySelectorAll('.filon-card').length>0`),5000,'retour au Filon');
  assert.ok(await evaluate(`document.querySelector('.filon-card img.filon-cover').src.includes('/api/thumb?url=')`),'cover loaded at once, no hover');
  await evaluate(`document.querySelector('.filon-card [data-action="new"]').click()`);
  assert.equal(await waitFor(()=>evaluate(`document.querySelector('#createForm [name=source_url]')?.value`),5000,'formulaire prérempli'),'https://www.tiktok.com/@oma/video/4242424242');
  // Paste a TikTok link anywhere on the page: the creation page opens, prefilled.
  await evaluate(`document.querySelector('nav [data-page="filon"]').click()`);
  await evaluate(`(()=>{const d=new DataTransfer();d.setData('text/plain','regarde https://www.tiktok.com/@x/video/77 !');document.body.dispatchEvent(new ClipboardEvent('paste',{clipboardData:d,bubbles:true}));return true})()`);
  assert.equal(await waitFor(()=>evaluate(`document.querySelector('#createForm [name=source_url]')?.value`),5000,'collage'),'https://www.tiktok.com/@x/video/77');
  assert.ok(await evaluate(`[...document.querySelectorAll('nav small')].map(x=>x.textContent).join('|').includes('vidéo(s) relevée(s)')`),'live nav subtitles');
  // 12 a. Atelier-like site cards: six sites plus file access, Re-check queues a request, default language follows into the form.
  await evaluate(`document.querySelector('[data-page="connections"]').click()`);
  // 0.1.74: Mes comptes keeps technical settings folded in « Avancé », opened here as the owner would.
  await sleep(400);await evaluate(`document.querySelector('[data-fold="advanced"]:not([open])>summary')?.click()`);
  await waitFor(()=>evaluate(`document.querySelectorAll('.site-card').length===7`),10000,'cartes des sites');
  assert.ok(await evaluate(`document.querySelector('.files-card').innerText.includes('Accès à tes fichiers')`),'file access card');
  // 12 a bis. Lot 4: guided account change in three steps, checks with three levels.
  await evaluate(`document.querySelector('[data-switch-help="chatgpt"]').click()`);
  const help=await waitFor(()=>evaluate(`document.querySelector('.switch-help')?.innerText`),5000,'aide changer de compte');
  assert.ok(help.includes('Se déconnecter')&&help.includes('C’est fait')&&help.includes('Tes histoires ne bougent pas'),help);
  await evaluate(`document.querySelector('[data-switch-done]').click()`);
  await waitFor(()=>evaluate(`!document.querySelector('.switch-help')`),5000,'aide fermée après C’est fait');
  await waitFor(async()=>(await (await fetch(base+'/api/state')).json()).bridge_requests?.some(r=>r.type==='check'),5000,'revérification après changement');
  await evaluate(`document.querySelector('[data-board-controls="redo"]').click()`);
  await waitFor(async()=>(await (await fetch(base+'/api/state')).json()).settings.board_controls==='redo',5000,'planches : refaire');
  await waitFor(()=>evaluate(`!!document.querySelector('[data-clip-look="ear"]')`),5000,'regard sur les clips');
  await evaluate(`document.querySelector('[data-clip-look="ear"]').click()`);
  await waitFor(async()=>(await (await fetch(base+'/api/state')).json()).settings.clip_look==='ear',5000,'clips à l’oreille');
  assert.ok(await waitFor(()=>evaluate(`document.querySelector('[data-board-controls="redo"]')?.classList.contains('primary')&&document.querySelector('[data-clip-look="ear"]').classList.contains('primary')`),5000,'choix visibles'));
  assert.ok(await evaluate(`document.querySelector('.site-card').innerText.includes('NÉCESSAIRE')`));
  await evaluate(`document.querySelector('[data-sites-check]').click()`);
  await waitFor(async()=>(await (await fetch(base+'/api/state')).json()).bridge_requests?.some(r=>r.type==='check'),5000,'revérification demandée');
  await evaluate(`document.querySelector('[data-default-language="English (en-US)"]').click()`);
  await waitFor(async()=>(await (await fetch(base+'/api/state')).json()).settings.language==='English (en-US)',5000,'langue');
  await waitFor(()=>evaluate(`document.querySelector('[data-default-language="English (en-US)"]').classList.contains('primary')`),5000,'langue affichée');
  await evaluate(`document.querySelector('nav [data-action="new"]').click()`);
  assert.ok(await waitFor(()=>evaluate(`document.querySelector('[data-choice="language"][data-value="English (en-US)"]')?.classList.contains('on')`),5000,'langue préremplie'));
  // 12. Accounts like the Atelier: one form for every platform, tables per platform; no emoji icons anywhere.
  await evaluate(`document.querySelector('nav [data-page="connections"]').click()`);
  // 0.1.74: Mes comptes keeps technical settings folded in « Avancé », opened here as the owner would.
  await sleep(400);await evaluate(`document.querySelector('[data-fold="advanced"]:not([open])>summary')?.click()`);
  await waitFor(()=>evaluate(`document.querySelectorAll('[data-account-tab]').length===3&&!!document.querySelector('table.accounts')`),10000,'tableaux de comptes');
  await evaluate(`(()=>{const f=document.querySelector('#accountForm');f.email.value='flow.qa@x.com';[...f.querySelectorAll('[name=services]')].forEach(c=>c.checked=c.value==='flow');f.balance.value='88';f.requestSubmit();return true})()`);
  const flow=await waitFor(async()=>(await (await fetch(base+'/api/state')).json()).profiles.find(p=>p.label==='flow.qa@x.com'),10000,'compte Flow ajouté');
  assert.equal(flow.balance,88);
  await evaluate(`document.querySelector('[data-account-tab="limits"]').click()`);
  await waitFor(()=>evaluate(`[...document.querySelectorAll('table.accounts')].some(t=>t.innerText.includes('flow.qa@x.com'))`),10000,'compte Flow affiché');
  // 12 bis. Unified accounts: one address, several services, one row; hidden studio key.
  await evaluate(`(()=>{const f=document.querySelector('#accountForm');f.email.value='Moi.QA@x.com';f.balance.value='40';[...f.querySelectorAll('[name=services]')].forEach(c=>c.checked=['chatgpt','flow','grok','arena'].includes(c.value));f.requestSubmit();return true})()`);
  const unified=await waitFor(async()=>(await (await fetch(base+'/api/state')).json()).accounts.find(a=>a.email==='moi.qa@x.com'),10000,'compte unifié ajouté');
  assert.deepEqual(unified.order,['chatgpt','flow','grok','arena']);assert.equal(unified.services.flow.balance,40);
  await evaluate(`document.querySelector('.more-accounts').open=true`);
  assert.ok(await evaluate(`!!document.querySelector('[data-bridge-action="scan_flow"]')`),'Détecter mes comptes');
  assert.ok(await evaluate(`/Retirer tous les comptes \\(\\d+\\)/.test(document.querySelector('[data-delete-all-accounts]')?.textContent||'')`),'bouton retirer tous les comptes');
  await waitFor(()=>evaluate(`[...document.querySelectorAll('table.unified tbody tr')].filter(r=>r.textContent.includes('moi.qa@x.com')).length===1`),10000,'une ligne par adresse');
  assert.ok(await evaluate(`document.querySelector('.key-panel').textContent.includes('Clé du studio')&&!document.querySelector('.key-panel').textContent.includes(${JSON.stringify('')}+'token')`),'key panel');
  await evaluate(`document.querySelector('[data-add-service="moi.qa@x.com"][data-service="claude"]').click()`);
  await waitFor(async()=>(await (await fetch(base+'/api/state')).json()).accounts.find(a=>a.email==='moi.qa@x.com').services.claude,10000,'service ajouté sur la ligne');
  // 12 ter. No gateway tab: its buttons live in Mes comptes › Navigateur and reach the extension through the studio.
  await evaluate(`document.querySelector('[data-account-tab="bridge"]').click()`);
  await waitFor(()=>evaluate(`!!document.querySelector('[data-bridge-action="register_flow"]')`),10000,'panneau navigateur');
  await evaluate(`document.querySelector('[data-bridge-action="register_flow"]').click()`);
  await waitFor(async()=>(await (await fetch(base+'/api/state')).json()).bridge_requests?.some(r=>r.type==='register_flow'),5000,'demande transmise');
  await waitFor(()=>evaluate(`document.querySelector('.bridge-notice')?.innerText.includes('Demande envoyée')`),10000,'retour affiché');
  const emoji=/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{2B50}\u{2B06}\u{2190}-\u{21FF}\u{25A0}-\u{25FF}]/u;
  for(const pageName of ['filon','studio','connections','guide']){
   await evaluate(`document.querySelector('[data-page="${pageName}"]').click()`);await sleep(400);
   const text=await evaluate('document.body.innerText');assert.ok(!emoji.test(text),'no emoji icon on '+pageName+': '+(text.match(emoji)||[])[0]);
  }
  assert.ok(await evaluate(`document.querySelectorAll('nav svg.ico').length===4`),'nav uses the line-icon set');
  assert.deepEqual(errors,[]);ws.close();
  console.log('Interactions navigateur : correction conservée au rafraîchissement, enregistrement, refus visible, confirmation de sortie, validation, « Refaire la couverture », changement de compte guidé, ajout d’un compte Grok, file de nuit, guide, page Créer (durées, moteur, dix histoires), page épisode (étapes, scènes, planche et clip côte à côte), thème sombre, Filon (miniatures immédiates) et création depuis un lien vérifiés.');
 }finally{cleanup();}
})().catch(e=>{console.error(e);process.exitCode=1;});
