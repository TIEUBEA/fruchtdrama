const BASE='http://127.0.0.1:8840';
// Two lanes, like the Atelier (clips leave while ChatGPT draws the boards): 'chat' (ChatGPT, Claude, TikTok) and
// 'video' (Flow, Grok, Arena). Each lane follows one task at a time, in its own tabs, with its own saved state:
// activeTask (chat; also any task saved by 0.1.88 and older) and activeVideoTask (video).
// 0.1.91, parallel clips: a second video lane (activeVideoTask2) takes another Flow clip on another Google account, in its
// own tab; the studio never gives two lanes the same account.
const LANE_KEY={chat:'activeTask',video:'activeVideoTask',video2:'activeVideoTask2'};
const VIDEO_KINDS=['flow_video','flow_collect','engine_video'];
function laneOf(task){return VIDEO_KINDS.includes(task?.kind)?'video':'chat';}
function keyOf(active){return active?.key||LANE_KEY.chat;}
async function saveActive(active,extra={}){await chrome.storage.local.set({[keyOf(active)]:active,...extra});}
async function loadActive(active){const key=keyOf(active);return (await chrome.storage.local.get(key))[key];}
async function dropActive(active){await chrome.storage.local.remove(keyOf(active));}
const busy={chat:false,video:false,video2:false};
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function call(path,body){
 const cfg=await chrome.storage.local.get('token');
 const r=await fetch(BASE+path,{method:body?'POST':'GET',headers:{Authorization:'Bearer '+cfg.token,...(body?{'Content-Type':'application/json'}:{})},body:body?JSON.stringify(body):undefined});
 const data=await r.json();if(!r.ok)throw Error(data.error||'Studio inaccessible');return data;
}
// Which service a task's page belongs to (for « Préparer mes comptes » and the « À régler » mark).
function serviceOf(task){return task.kind==='flow_video'?'flow':task.kind==='engine_video'?task.payload?.engine:task.kind==='tiktok_search'?null:(task.payload?.provider==='claude'?'claude':'chatgpt');}
async function ready(id,task,targetUrl){
 const expected=task.kind==='flow_video'?['flow.google.com','labs.google']:task.kind==='engine_video'?FruchtEngines.hosts(task.payload.engine):task.kind==='tiktok_search'?['www.tiktok.com','tiktok.com']:[task.payload.provider==='claude'?'claude.ai':'chatgpt.com'];
 for(let i=0;i<180;i++){
  const tab=await chrome.tabs.get(id);let host;
  try{host=new URL(tab.url).hostname;}catch{}
  if(expected.includes(host)&&(!targetUrl||tab.url===targetUrl)){
   // Sites may keep loading trackers after the editor is already usable.
   // This probe only reads the DOM; it never fills or submits anything.
   try{
    const probes=await chrome.scripting.executeScript({target:{tabId:id},args:[targetUrl||tab.url,['tiktok_search','engine_video'].includes(task.kind)],func:(expectedUrl,isSearch)=>{
     if(location.href!==expectedUrl)return false;
     if(!['interactive','complete'].includes(document.readyState))return false;
     if(isSearch)return !!document.body?.innerText;
     return [...document.querySelectorAll('textarea:not([disabled]),[contenteditable="true"]')].some(el=>el.getClientRects().length>0);
    }});
    if(probes.some(p=>p.result===true))return;
   }catch{}
  }
  await delay(500);
 }
 // Say what was seen (06/11/2026: Flow clip refused here twice with no clue).
 let seen='';try{const tab=await chrome.tabs.get(id);let host='';try{host=new URL(tab.url).hostname;}catch{}const [probe]=!expected.includes(host)?[]:await chrome.scripting.executeScript({target:{tabId:id},func:()=>({href:location.href,ready:document.readyState,editors:[...document.querySelectorAll('textarea:not([disabled]),[contenteditable="true"]')].map(e=>e.getClientRects().length).join(','),dialog:[...document.querySelectorAll('[role="dialog"]')].map(d=>(d.innerText||'').slice(0,50)).join(' | ')})});seen=' Vu : '+JSON.stringify({tab:tab.url,status:tab.status,discarded:tab.discarded,frozen:tab.frozen,expected:targetUrl||'',...(probe?.result||{})}).slice(0,400);}catch(e){seen=' Vu : onglet illisible ('+e.message+')';}
 // Say exactly what is wrong (0.1.91): the account is marked « À régler » in Mes comptes and the next ready Flow account
 // takes the clip; nothing was sent, so nothing is paid twice.
 let verdict=null;const service=serviceOf(task);
 if(service&&globalThis.FruchtReadiness)try{
  const tab=await chrome.tabs.get(id),host=FruchtReadiness.hostOf(tab.url);
  const info={kind:service==='flow'?'flow':'site',name:service,host,expectedHosts:FruchtReadiness.HOSTS[service]||expected,unavailable:/\/unavailable(?:[/?#]|$)/.test(tab.url||''),expectedEmail:task.payload?.flow_route?.email?.toLowerCase()};
  if((FruchtReadiness.HOSTS[service]||expected).includes(host)&&!info.unavailable)Object.assign(info,await FruchtReadiness.probeTab(chrome,id,service));
  verdict=FruchtReadiness.classify(info);if(verdict.state==='ready')verdict={state:'fix',reason:'Page du fournisseur sans réponse après 90 secondes'};
 }catch{}
 const error=Error('Page du fournisseur indisponible ou vide après 90 secondes ('+(verdict?.reason||'connexion requise, vérification anti-robot ou blocage')+') : aucun prompt envoyé. Le compte est marqué « À régler » dans Mes comptes.'+seen);
 if(verdict)error.notReady=verdict;
 if(task.kind==='flow_video')error.flowBlocked=verdict?.state==='no_access'?'unavailable':'not_ready';
 throw error;
}
async function loadAttachments(paths){
 const files=[];
 for(const path of paths||[]){
  if(!/^\/media\/[a-f0-9]{16}\/[a-zA-Z0-9_.-]+$/.test(path))throw Error('Référence locale invalide.');
  const r=await fetch(BASE+path);if(!r.ok)throw Error('Référence locale introuvable.');
  const bytes=new Uint8Array(await r.arrayBuffer());let binary='';
  for(let i=0;i<bytes.length;i+=16384)binary+=String.fromCharCode(...bytes.subarray(i,i+16384));
  files.push({name:path.split('/').pop(),mime:r.headers.get('Content-Type'),data:btoa(binary)});
 }
 return files;
}
function allowedMedia(url){try{const u=new URL(url);return u.protocol==='https:'&&['chatgpt.com','oaiusercontent.com','googleusercontent.com','googlevideo.com','labs.google','flow.google.com'].some(d=>u.hostname===d||u.hostname.endsWith('.'+d));}catch{return false;}}
async function receiveMedia(task,result){
 let bytes,mime=result.mime;
 if(result.base64){bytes=Uint8Array.from(atob(result.base64),c=>c.charCodeAt(0));}
 else{
  if(!allowedMedia(result.url))throw Error('Adresse média non prise en charge. Import manuel disponible.');
  const r=await fetch(result.url,{credentials:'include'});if(!r.ok)throw Error('Téléchargement refusé. Import manuel disponible.');
  mime=r.headers.get('Content-Type')||mime;bytes=new Uint8Array(await r.arrayBuffer());
 }
 if(bytes.length>100*1024*1024)throw Error('Média limité à 100 Mo.');
 const ext=mime?.includes('webm')?'webm':['flow_video','flow_collect','engine_video'].includes(task.kind)?'mp4':mime?.includes('jpeg')?'jpg':mime?.includes('webp')?'webp':'png';
 const cfg=await chrome.storage.local.get('token');
 const r=await fetch(`${BASE}/api/bridge/upload?job=${task.job}&slot=${encodeURIComponent(task.slot)}&ext=${ext}`,{method:'POST',headers:{Authorization:'Bearer '+cfg.token},body:bytes});
 const data=await r.json();if(!r.ok)throw Error(data.error);return {ok:true,file:data.file};
}
async function finish(active,result){
 // Persist a completed reply before delivery. A temporary local-server outage
 // must never cause another prompt to be sent.
 await saveActive({...active,pendingResult:result});
 if(result.ok&&(result.url||result.base64))result=await receiveMedia(active.task,result);
 await saveActive({...active,pendingResult:result});
 const ack=await call('/api/bridge/result',{task:active.task.id,client:active.client,result});
 if(ack.task_status==='done'&&result.ok&&globalThis.FruchtChats)await FruchtChats.queueClose(active,chrome);
 const data=await chrome.storage.local.get('scenarioTabs');const tabs=data.scenarioTabs||{};
 if(tabs[active.task.job])tabs[active.task.job].pending=false;
 await chrome.storage.local.set({scenarioTabs:tabs});
 await dropActive(active);
 await chrome.storage.local.set({status:ack.task_status==='failed'?'À vérifier : '+(ack.error||'Scénario refusé par le studio'):result.ok?'Terminé : '+active.task.slot:'À vérifier : '+result.error});
 // Chat tabs are closed by the chat lane only (never two closings of the same list at once).
 if(globalThis.FruchtChats&&laneOf(active.task)==='chat')await FruchtChats.closeCompleted(chrome);
}
async function clearBinding(active){
 const data=await chrome.storage.local.get('scenarioTabs');const tabs=data.scenarioTabs||{};
 if(tabs[active.task.job])tabs[active.task.job].pending=false;
 await chrome.storage.local.set({scenarioTabs:tabs});await dropActive(active);
}
async function checkActive(active){
 if(!active.startedAt)active.startedAt=Date.now();
 const context=await call('/api/bridge/status?client='+encodeURIComponent(active.client)+'&task='+encodeURIComponent(active.task.id));
 if(context.task_status==='done'||context.task_status==='cancelled'||(FruchtRecovery.isScenario(active.task)&&context.job_stage!=='script')){await clearBinding(active);return;}
 if(context.job_status==='paused'){await chrome.storage.local.set({status:'Production en pause ; association avec l’onglet conservée.'});return;}
 if(context.task_status==='failed'&&!FruchtRecovery.isScenario(active.task)){await clearBinding(active);return;}
 if(active.preparingProject){
  const cfg=await chrome.storage.local.get(null),tab=await FruchtFlowSession.tabFor(active.task,chrome);
  const prepared=await prepareNewFlowProject(active.task,tab,cfg,keyOf(active));
  await begin(active.task,prepared,cfg,keyOf(active));return;
 }
 if(active.download){await pollFlowDownload(active);return;}
 if(active.pendingResult){
  if(context.task_status==='failed'&&FruchtRecovery.isScenario(active.task)){
   active.task=await call('/api/bridge/recover',{client:active.client,job:active.task.job,previous_task:active.task.id,automatic:true});
   await saveActive(active);
  }
  await finish(active,active.pendingResult);return;
 }
 if(FruchtRecovery.isScenario(active.task)||['quality_review','board_review','cover_review'].includes(active.task.slot)){
  try{
   await chrome.scripting.executeScript({target:{tabId:active.tabId},files:['response.js']});
   const probe=await chrome.tabs.sendMessage(active.tabId,{type:'frucht-scenario-probe',job:active.expectedJob||active.task.job,task:active.expectedTask||active.task.id,scenes:active.task.payload.scene_count,response_kind:active.task.payload.response_kind});
   if(probe?.text){
    if(active.observedScenario===probe.text){await finish(active,{ok:true,text:probe.text});return;}
    active.observedScenario=probe.text;await saveActive(active);
   }
   if(probe?.diagnostic){
    const diagnostic=JSON.stringify(probe.diagnostic);
    if(diagnostic!==active.scenarioDiagnostic){
     await call('/api/bridge/progress',{task:active.task.id,client:active.client,message:'Lecture du scénario : '+diagnostic});
     active.scenarioDiagnostic=diagnostic;await saveActive(active);
    }
   }
  }catch{}
 }
 let status;
 if(['chat_image','flow_video'].includes(active.task.kind)){
  // Refresh only the reader; a finished image must not require another prompt.
  try{
   await chrome.scripting.executeScript({target:{tabId:active.tabId},files:['media.js','flow-controls.js','flow-download.js','chat-session.js']});
   const image=await chrome.tabs.sendMessage(active.tabId,{type:active.task.kind==='flow_video'?'frucht-video-probe':'frucht-media-probe',prompt:active.task.payload.prompt});
   if(image?.matched&&image.ok){await finish(active,image);return;}
   if(active.task.kind==='chat_image'&&image?.matched&&image.localNetworkError&&!active.localNetworkRetryIntent){
    // A local conversation plus an explicit network alert denotes failure before
    // a server conversation exists. Retry the site's same request once only.
    active.localNetworkRetryIntent=true;
    await saveActive(active);
    const retried=await chrome.tabs.sendMessage(active.tabId,{type:'frucht-retry-local-network',prompt:active.task.payload.prompt});
    await call('/api/bridge/progress',{task:active.task.id,client:active.client,message:retried?.retried?'ChatGPT : erreur réseau avant création de la conversation ; reprise unique dans le même onglet.':'ChatGPT : reprise réseau suspendue car l’interface a changé.'});
    return;
   }
   if(active.task.kind==='flow_video'&&image?.matched&&image.canDownload){await requestFlowDownload(active);return;}
  }catch(e){
   // A reader unavailable during navigation is retried by the next poll.
   // Delivery/upload errors must retain the pending result for retry.
   const saved=await loadActive(active);
   if(saved?.pendingResult)throw e;
  }
 }
 try{status=await chrome.tabs.sendMessage(active.tabId,{type:'frucht-status'});}catch{}
 if(!status||status.task!==active.task.id){
  if(await recoverResearchReading(active,status))return;
  if(active.task.kind==='chat_image'&&(active.submissionIntent===true||active.submitted||active.localNetworkRetryIntent)&&Date.now()-active.startedAt<15*60*1000){
   await chrome.storage.local.set({status:'Image déjà demandée : suivi conservé après navigation, lecture seule sans nouveau prompt.'});return;
  }
  if(FruchtRecovery.mayCollect(active,context,Date.now())){await collectBound(active,context);return;}
  if(await recoverFlowPreparation(active))return;
  throw Error('Suivi interrompu : récupération du clip à vérifier avant toute nouvelle génération.');
 }
 if(status.submitted&&!active.submitted){active.submitted=true;await saveActive(active);}
 if(status.state==='completed'){
  if(!status.result.ok&&/Extension reloaded|context invalidated|Interface non reconnue|association.*perdue/i.test(status.result.error||'')&&await recoverFlowPreparation(active))return;
  if(!status.result.ok&&status.result.recoverable&&FruchtRecovery.mayCollect(active,context,Date.now())){await collectBound(active,context);return;}
  if(context.task_status==='failed'&&status.result.ok){await collectBound(active,context);return;}
  await finish(active,status.result);
 }else{
  await chrome.storage.local.set({status:status.progress||'En cours : '+active.task.slot+' · récupération automatique, aucun clic requis'});
  if(status.progress&&status.progress!==active.lastProgress){
   await call('/api/bridge/progress',{task:active.task.id,client:active.client,message:status.progress});
   active.lastProgress=status.progress;await saveActive(active);
  }
 }
}
async function recoverResearchReading(active,status){
 if(active.task.kind!=='tiktok_search'||status?.state==='running'||(active.researchReadingAttempts||0)>=3||Date.now()-active.startedAt>5*60*1000)return false;
 const tab=await chrome.tabs.get(active.tabId);let host;
 try{host=new URL(tab.url).hostname;}catch{}
 if(!['www.tiktok.com','tiktok.com'].includes(host))return false;
 active.researchReadingAttempts=(active.researchReadingAttempts||0)+1;
 await saveActive(active,{status:'Relecture automatique de la recherche TikTok après navigation · même tâche.'});
 await chrome.scripting.executeScript({target:{tabId:active.tabId},files:['composer.js','response.js','media.js','flow-controls.js','flow-session.js','research.js','chat-session.js','claude-model.js','runner.js']});
 const response=await chrome.tabs.sendMessage(active.tabId,{type:'frucht-run',task:active.task,attachments:[]});
 if(!response?.accepted)throw Error(response?.error||'Lecture de la recherche indisponible.');
 return true;
}
function executionTaskFor(task){
 const executionTask={...task,payload:{...task.payload}};
 if(task.kind==='chat_text'){
  executionTask.payload.expected_job=task.job;
  executionTask.payload.expected_task=task.id;
  executionTask.payload.prompt+='\nTechnical requirement: include the exact field "production_id": "'+task.job+'" in the final JSON object. Also include the exact field "generation_task_id": "'+task.id+'". Do not omit these identifiers.';
 }
 return executionTask;
}
async function recoverFlowPreparation(active){
 if(active.task.kind!=='flow_video'||active.submissionIntent!==false||active.submitted||(active.recoveryAttempts||0)>=3||Date.now()-active.startedAt>10*60*1000)return false;
 const latest=await loadActive(active);
 if(!latest||latest.task.id!==active.task.id||latest.submissionIntent!==false||latest.submitted)return false;
 active.recoveryAttempts=(active.recoveryAttempts||0)+1;
 await saveActive(active,{status:'Reconnexion automatique avant envoi : même tâche, aucune réservation supplémentaire.'});
 await ready(active.tabId,active.task);
 await chrome.scripting.executeScript({target:{tabId:active.tabId},files:['composer.js','response.js','media.js','flow-controls.js','flow-session.js','research.js','chat-session.js','claude-model.js','runner.js']});
 const reply=await chrome.tabs.sendMessage(active.tabId,{type:'frucht-run',task:active.task,attachments:await loadAttachments(active.task.payload.attachments)});
 if(!reply?.accepted)throw Error(reply?.error||'Préparation Flow indisponible après reconnexion.');
 return true;
}
async function collectBound(active,context){
 const tab=await chrome.tabs.get(active.tabId);
 if(!FruchtRecovery.allowedTab(active.task,tab.url))throw Error('L’onglet associé a changé de site. Récupération suspendue pour ne pas mélanger les conversations.');
 if(context.task_status==='failed'){
  const renewed=await call('/api/bridge/recover',{client:active.client,job:active.task.job,previous_task:active.task.id,automatic:true});
  active.task=renewed;
 }
 active.recoveryAttempts=(active.recoveryAttempts||0)+1;
 const task={...active.task,kind:'chat_collect',payload:{...active.task.payload,expected_job:active.expectedJob,expected_task:active.expectedTask}};
 await chrome.scripting.executeScript({target:{tabId:active.tabId},files:['composer.js','response.js','media.js','flow-controls.js','flow-session.js','research.js','chat-session.js','claude-model.js','runner.js']});
 // Clear only a completed/lost reader. Never restart a live generator.
 const response=await chrome.tabs.sendMessage(active.tabId,{type:'frucht-run',task,attachments:[]});
 if(!response?.accepted)throw Error(response?.error||'Lecture automatique indisponible.');
 await saveActive(active,{status:'Récupération automatique du scénario existant · tentative '+active.recoveryAttempts+' · aucun nouveau prompt'});
 const data=await chrome.storage.local.get('scenarioTabs');const tabs=data.scenarioTabs||{};tabs[active.task.job]={...active,pending:true};await chrome.storage.local.set({scenarioTabs:tabs});
}
async function begin(task,tab,cfg,key=LANE_KEY[laneOf(task)]){
 let targetUrl;
 // Like the Atelier: the work happens in a background tab of the window; the owner keeps the studio in view.
 if(task.kind==='flow_video'&&tab.url){
  const url=new URL(tab.url),match=url.pathname.match(/^(.*\/project\/[^/]+)\/edit\//);
  if(match&&['flow.google.com','labs.google'].includes(url.hostname)){targetUrl=url.origin+match[1];await chrome.tabs.update(tab.id,{url:targetUrl});}
 }
 await ready(tab.id,task,targetUrl);
 if(task.payload.flow_route){
  if(task.payload.flow_route.client!==cfg.client)throw Error('Ce compte Flow appartient à une autre passerelle.');
  await chrome.scripting.executeScript({target:{tabId:tab.id},files:['flow-session.js']});
  const identity=await chrome.tabs.sendMessage(tab.id,{type:'frucht-flow-verify',target:task.payload.flow_route});
  if(!identity?.ok)throw Error('Compte Flow différent ou connexion expirée. Reconnectez le compte enregistré ; aucun envoi effectué.');
 }
 const inject=()=>chrome.scripting.executeScript({target:{tabId:tab.id},files:['composer.js','response.js','media.js','flow-controls.js','flow-session.js','research.js','chat-session.js','engine-video.js','claude-model.js','runner.js']});
 await inject();
 let previous;
 try{previous=await chrome.tabs.sendMessage(tab.id,{type:'frucht-status'});}catch{}
 if(previous?.state==='running'&&previous.task!==task.id){
  const old=await call('/api/bridge/status?client='+encodeURIComponent(cfg.client)+'&task='+encodeURIComponent(previous.task));
  if(old.task_status==='done'||(['cancelled','failed'].includes(old.task_status)&&previous.submitted!==true)){
   await chrome.tabs.reload(tab.id);await ready(tab.id,task);await inject();
  }else throw Error('Une génération précédente reste à vérifier dans cet onglet ; aucun nouveau prompt envoyé.');
 }
 const attachments=await loadAttachments(task.payload.attachments);
 const active={task,key,tabId:tab.id,windowId:tab.windowId,client:cfg.client,startedAt:Date.now(),recoveryAttempts:0,submissionIntent:false,expectedJob:task.kind==='chat_text'?task.job:undefined,expectedTask:task.kind==='chat_text'?task.id:undefined};
 const data=await chrome.storage.local.get('scenarioTabs');const tabs=data.scenarioTabs||{};
 if(FruchtRecovery.isScenario(task)){tabs[task.job]={...active,pending:true};await chrome.storage.local.set({scenarioTabs:tabs});}
 await saveActive(active,{status:'En cours : '+task.slot});
 const executionTask=executionTaskFor(task);
 const response=await chrome.tabs.sendMessage(tab.id,{type:'frucht-run',task:executionTask,attachments});
 if(!response?.accepted)throw Error(response?.error||'Le connecteur de l’onglet ne répond pas.');
 // The content script now works independently. No multi-minute message channel.
}
async function prepareNewFlowProject(task,tab,cfg,key=LANE_KEY.video){
 await saveActive({task,key,tabId:tab.id,windowId:tab.windowId,client:cfg.client,startedAt:Date.now(),submissionIntent:false,preparingProject:true},{status:'Ouverture automatique : nouveau projet Flow…'});
 const prepared=await FruchtFlowSession.prepareProject(task,tab,chrome,delay);
 const url=FruchtFlowSession.project(prepared.url);
 await call('/api/bridge/flow-project',{task:task.id,client:cfg.client,url});
 task.payload.flow_route.url=url;delete task.payload.flow_route.new_project;
 return prepared;
}
// « Se connecter » (Mes comptes): the site opens in a tab of the FruchtDrama window (an open one is reused),
// then the extension watches it. As soon as the owner is signed in, the card turns green, the tab it opened
// closes and the studio is back on screen. Nothing is typed: the owner signs in by hand.
async function openLogin(site){
 const hosts=FruchtSites.list[site].hosts,tabs=await chrome.tabs.query({});
 let tab=tabs.find(t=>{try{return hosts.includes(new URL(t.url||t.pendingUrl).hostname);}catch{return false;}}),opened=false;
 if(tab){tab=await FruchtWorkspace.adopt(chrome,tab);await chrome.tabs.update(tab.id,{active:true});}
 else{tab=await FruchtWorkspace.createTab(chrome,{url:FruchtSites.list[site].url,active:true});opened=true;}
 await chrome.windows.update(tab.windowId,{focused:true}).catch(()=>{});
 const {pendingLogins={}}=await chrome.storage.local.get('pendingLogins');
 pendingLogins[site]={tabId:tab.id,opened,at:Date.now()};await chrome.storage.local.set({pendingLogins});
}
// « Ajouter un compte » (no account left with credits): Google's own add-account page opens in the window.
// The owner signs in by hand; once Google sends the tab on to Flow, the accounts are detected again by themselves.
const ADD_GOOGLE='https://accounts.google.com/AddSession?continue='+encodeURIComponent('https://flow.google.com/');
async function addGoogle(){
 const tab=await FruchtWorkspace.createTab(chrome,{url:ADD_GOOGLE,active:true});
 await chrome.windows.update(tab.windowId,{focused:true}).catch(()=>{});
 await chrome.storage.local.set({pendingGoogle:{tabId:tab.id,at:Date.now()}});
}
async function watchGoogle(onlyTab){
 const {pendingGoogle:w,client}=await chrome.storage.local.get(['pendingGoogle','client']);
 if(!w||!client||(onlyTab!==undefined&&w.tabId!==onlyTab))return;
 let tab;try{tab=await chrome.tabs.get(w.tabId);}catch{tab=null;}
 if(!tab||Date.now()-w.at>30*60*1000){await chrome.storage.local.remove('pendingGoogle');return;}
 let host='';try{host=new URL(tab.url||'').hostname;}catch{}
 if(!['flow.google.com','labs.google'].includes(host))return;  // still on Google's sign-in pages
 await chrome.storage.local.remove('pendingGoogle');
 await FruchtWorkspace.close(chrome,[tab.id]);
 let text;try{const accounts=await FruchtFlowScan.scan(chrome,FruchtWorkspace);const b=await call('/api/bridge/flow-scan',{client,accounts});text='Compte ajouté. '+b.message;}catch(e){text='Compte ajouté ; détection interrompue : '+e.message;}
 await call('/api/bridge/notice',{client,action:'scan_flow',ok:!/interrompue/.test(text),text});
}
async function watchLogins(onlyTab){
 const {pendingLogins={},client}=await chrome.storage.local.get(['pendingLogins','client']);
 if(!client||!Object.keys(pendingLogins).length)return;
 let changed=false;
 for(const [site,w] of Object.entries(pendingLogins)){
  if(onlyTab!==undefined&&w.tabId!==onlyTab)continue;
  if(Date.now()-w.at>20*60*1000){delete pendingLogins[site];changed=true;continue;}
  let tab;try{tab=await chrome.tabs.get(w.tabId);}catch{tab=null;}
  if(!tab){delete pendingLogins[site];changed=true;continue;}  // closed by the owner: the next Revérifier tells
  let state;
  try{
   await chrome.scripting.executeScript({target:{tabId:tab.id},files:['composer.js','sites.js']});
   const [r]=await chrome.scripting.executeScript({target:{tabId:tab.id},func:n=>globalThis.FruchtSites.probe(n,document),args:[site]});
   state=r?.result;
  }catch{continue;}  // page still loading or on the provider's sign-in domain
  if(!state?.connected)continue;
  delete pendingLogins[site];changed=true;
  await call('/api/bridge/sites',{client,sites:{[site]:state},partial:true});
  await call('/api/bridge/notice',{client,action:'login',ok:true,text:FruchtSites.label(site)+' connecté'+(state.email?' : '+state.email:'')+'.'}).catch(()=>{});
  if(w.opened)await FruchtWorkspace.close(chrome,[tab.id]);
  else{const studio=await FruchtWorkspace.studioTab(chrome,tab.windowId);if(studio)await chrome.tabs.update(studio.id,{active:true});}
 }
 if(changed)await chrome.storage.local.set({pendingLogins});
}
chrome.tabs?.onUpdated?.addListener((id,info)=>{if(info.status==='complete')setTimeout(()=>{watchLogins(id).catch(recordBackgroundError);watchGoogle(id).catch(recordBackgroundError);},2500);});
// Owner requests from "Mes comptes": open a site in the FruchtDrama window, or re-check every site.
async function handleRequests(cfg,light=false){
 // light: a task is running; only the owner's clicks that show a tab (Se connecter, Régler maintenant, Ajouter) are done now.
 const requests=await call('/api/bridge/requests?client='+encodeURIComponent(cfg.client)+(light?'&light=1':''));
 for(const r of requests||[]){
  if(r.type==='open'&&FruchtSites.list[r.site])await openLogin(r.site);
  if(r.type==='add_google')await addGoogle();
  if(r.type==='check'){const sites=await FruchtSites.check(chrome,FruchtWorkspace);await call('/api/bridge/sites',{client:cfg.client,sites});}
  // « Préparer mes comptes »: read only, background tabs; a check asked while the window is closed waits for it.
  if(r.type==='readiness'&&globalThis.FruchtReadiness){
   if(r.background&&!await FruchtWorkspace.isOpen(chrome))continue;
   let report;try{report=await FruchtReadiness.run(chrome,FruchtWorkspace,r);}catch(e){report={id:r.id,sites:{},profiles:{}};recordBackgroundError(e);}
   await call('/api/bridge/readiness',{client:cfg.client,...report});
  }
  if(r.type==='show'&&globalThis.FruchtReadiness)await FruchtReadiness.show(chrome,FruchtWorkspace,r);
  // Former gateway-tab buttons, now clicked in the studio's Mes comptes page.
  if(r.type==='scan_flow'){
   if(r.background&&!await FruchtWorkspace.isOpen(chrome))continue;
   let text;try{const accounts=await FruchtFlowScan.scan(chrome,FruchtWorkspace);const b=await call('/api/bridge/flow-scan',{client:cfg.client,accounts});text=b.message;}catch(e){text='Détection interrompue : '+e.message;}
   await call('/api/bridge/notice',{client:cfg.client,action:'scan_flow',ok:!/interrompue/.test(text),text});
   // « Vérifier » in Mes comptes › Google Flow: the accounts found are then each checked (next pass).
   if(r.then_check)await call('/api/bridge/readiness-request',{client:cfg.client,background:false});
  }
  if(['register_flow','tidy','recover'].includes(r.type)){
   let result;try{result=r.type==='register_flow'?await registerFlow(true):r.type==='tidy'?await tidyChats(true):await recover(r.job,true);}catch(e){result={ok:false,error:e.message};}
   await call('/api/bridge/notice',{client:cfg.client,action:r.type,ok:!!result?.ok,text:result?.message||result?.error||'Terminé.'});
  }
 }
}
// Hidden key (Atelier-like): pair once with the local studio, never ask the owner to copy a code.
async function autoPair(){
 const cfg=await chrome.storage.local.get(['client','token']);if(cfg.client&&cfg.token)return false;
 const r=await fetch(BASE+'/api/bridge/auto-pair',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({label:'Fenêtre FruchtDrama'})});
 const b=await r.json();if(!r.ok)throw Error(b.error||'Appairage automatique impossible');
 await chrome.storage.local.set({client:b.client,token:b.token,role:'all',ai_provider:'both',label:'Fenêtre FruchtDrama',enabled:true,auto_paired:true,status:b.enabled?'Appairé automatiquement au studio local.':'Appairé ; activez ce navigateur dans Mes comptes › Navigateur (un autre navigateur est déjà actif).'});
 return true;
}
// Shared pass: sign-in watches, studio start, pairing; owner requests (Mes comptes) run alone, as before:
// both lanes idle and no task followed. Then each lane works on its own (one slow lane never blocks the other).
let preparing=false;
async function prepare(){
 await watchLogins().catch(recordBackgroundError);
 await watchGoogle().catch(recordBackgroundError);
 // Studio stopped (computer restarted): the extension starts it, then the next pass works normally.
 if(globalThis.FruchtStudio&&!(await FruchtStudio.ensure(chrome,fetch,{wait:false})).ok)return false;
 let cfg=await chrome.storage.local.get(null);
 if(!cfg.client||!cfg.token){try{if(await autoPair())cfg=await chrome.storage.local.get(null);}catch(e){recordBackgroundError(e);}}
 if(!cfg.client||!cfg.token)return false;
 if(cfg.enabled&&!busy.chat&&!busy.video&&!busy.video2&&!Object.values(LANE_KEY).some(k=>cfg[k])){
  busy.chat=busy.video=busy.video2=true;
  try{await handleRequests(cfg);}catch(e){recordBackgroundError(e);}finally{busy.chat=busy.video=busy.video2=false;}
 }else if(cfg.enabled){try{await handleRequests(cfg,true);}catch(e){recordBackgroundError(e);}}
 return true;
}
async function poll(){
 if(preparing||(busy.chat&&busy.video))return;
 preparing=true;let ok=false;
 try{ok=await prepare();}finally{preparing=false;}
 // The second clip lane looks after the first one: it sees whether a clip really works there now.
 if(ok)await Promise.all([runLane('chat'),runLane('video').then(()=>runLane('video2'))]);
 if(ok)await soon();
}
// The 30 s alarm alone made every board wait up to 30 s to be seen, then up to 30 s more before the next one left
// (06/11/2026: boards measured at 59, 90, 120, 151 s). While a task is followed or queued work may exist, look again
// after FAST_POLL; each pass calls the studio, which keeps the service worker awake. The alarm stays as a safety net.
const FAST_POLL=3000;let fastTimer=null,lastSoon=0;
async function soon(){
 if(fastTimer||Date.now()-lastSoon<FAST_POLL/2)return;lastSoon=Date.now();
 const cfg=await chrome.storage.local.get(Object.values(LANE_KEY).concat(['enabled']));
 if(!cfg.enabled&&!Object.values(LANE_KEY).some(k=>cfg[k]))return;
 fastTimer=setTimeout(()=>{fastTimer=null;triggerPoll();},FAST_POLL);fastTimer?.unref?.();  // unref: node tests only
}
// Google numbers the signed-in accounts /u/0, /u/1… in sign-in order: adding or removing one shifts them (real case
// 06/11/2026: /u/3 became another account, its project answered 404 and clip 1 failed three times). The account is
// found again by its address, the studio is told the new number, and nothing is sent before.
async function readFlowIdentity(id){
 for(let i=0;i<30;i++){await delay(500);const t=await chrome.tabs.get(id);if(t.status==='complete')break;}
 for(let k=0;k<4;k++){
  await delay(1500);
  try{const [r]=await chrome.scripting.executeScript({target:{tabId:id},files:['flow-session.js']}).then(()=>chrome.scripting.executeScript({target:{tabId:id},func:()=>({email:globalThis.FruchtFlowSession.identity(document),href:location.href})}));if(r?.result?.email||/\/404/.test(r?.result?.href||''))return r.result;}catch{}
 }
 return {};
}
async function ensureFlowSlot(task,tab,cfg){
 const target=task.payload.flow_route,want=String(target.email||'').toLowerCase();if(!want)return tab;
 let seen=await readFlowIdentity(tab.id);
 if(seen.email===want&&!/\/404/.test(seen.href||''))return tab;
 for(let n=0;n<12;n++){
  await chrome.tabs.update(tab.id,{url:'https://flow.google.com/u/'+n+'/'});
  seen=await readFlowIdentity(tab.id);
  if(seen.email!==want)continue;
  const url=target.url.replace(/\/u\/\d+\//,'/u/'+n+'/');
  await call('/api/bridge/flow-slot',{task:task.id,client:cfg.client,slot:n});
  target.url=url;await chrome.tabs.update(tab.id,{url});return tab;
 }
 throw Error('Compte Flow '+want+' introuvable dans ce Chrome (déconnecté ?). Reconnecte-le dans Mes comptes. Aucun crédit dépensé.');
}
async function tabForTask(task,cfg,key){
 let tab;
 if(task.kind==='flow_video'){
  if(task.payload.flow_route){
   tab=await FruchtFlowSession.tabFor(task,chrome);
   tab=await ensureFlowSlot(task,tab,cfg);
   if(task.payload.flow_route.new_project){
    tab=await prepareNewFlowProject(task,tab,cfg,key);
   }
  }
  else{
   const tabs=await chrome.tabs.query({url:['https://labs.google/*','https://flow.google.com/*']});
   tab=await FruchtWorkspace.adopt(chrome,tabs.find(t=>t.url?.includes('/project/'))||tabs[0]);
  }
  if(!tab)throw Error('Ouvrez un projet Flow, réglez vidéo 9:16, huit secondes et x1.');
 }else if(task.kind==='engine_video'){
  tab=await FruchtEngines.tabFor(task,chrome);
 }else if(FruchtChats.isAI(task)){
  tab=await FruchtChats.tabFor(task,cfg,chrome);
 }else{
  const url='https://www.tiktok.com/search?q='+encodeURIComponent(task.payload.query);
  const saved=cfg.researchTab;let previous;
  if(saved)try{previous=await chrome.tabs.get(saved);}catch{}
  if(previous&&/^https:\/\/(www\.)?tiktok\.com\//.test(previous.url||''))tab=await FruchtWorkspace.adopt(chrome,await chrome.tabs.update(previous.id,{url,active:false}));
  else tab=await FruchtWorkspace.createTab(chrome,{url,active:false});
  await chrome.storage.local.set({researchTab:tab.id});
 }
 return tab;
}
// One lane: follow its saved task, otherwise claim the next task of this lane only (lane=chat|video).
async function runLane(lane){
 if(busy[lane])return;busy[lane]=true;const key=LANE_KEY[lane];let claimed=null;let cfg;
 try{
  cfg=await chrome.storage.local.get(null);
  if(!cfg.client||!cfg.token)return;
  if(lane==='video2'){
   // Second clip lane: never a balance reading or a recovery here (they could touch the first lane's tab).
   if(laneOf(cfg.activeTask?.task)==='video')return;
   if(cfg.activeVideoTask2){await checkActive(cfg.activeVideoTask2);return;}
   // Only while the first lane works on a clip: then the studio may give a clip of another account.
   if(!cfg.enabled||cfg.role==='creation'||!cfg.activeVideoTask)return;
  }else if(lane==='video'){
   // A clip saved by 0.1.88 or older sits in activeTask: the chat lane follows it; no other clip meanwhile.
   if(laneOf(cfg.activeTask?.task)==='video')return;
   if(cfg.activeVideoTask){await checkActive(cfg.activeVideoTask);return;}
   if(!cfg.enabled)return;
   if(!cfg.activeVideoTask2&&globalThis.FruchtCredits&&await FruchtCredits.check(cfg,chrome,call))return;
   if(!cfg.activeVideoTask2&&cfg.role!=='creation'&&Date.now()-(cfg.lastVideoRecovery||0)>30000){
    await chrome.storage.local.set({lastVideoRecovery:Date.now()});
    if(await recoverExistingVideo(cfg))return;
   }
  }else{
   if(cfg.activeTask){await checkActive(cfg.activeTask);return;}
   if(globalThis.FruchtChats&&!await FruchtChats.closeCompleted(chrome))return;
   // A browser/worker restart can lose the active pointer, but not its binding.
   const bound=Object.values(cfg.scenarioTabs||{}).find(a=>a.pending&&a.client===cfg.client&&Date.now()-a.startedAt<20*60*1000);
   if(bound&&cfg.enabled){await chrome.storage.local.set({activeTask:bound});await checkActive(bound);return;}
   if(!cfg.enabled)return;
   if(globalThis.FruchtChats&&cfg.role!=='flow'&&Date.now()-(cfg.lastResearchReadingRecovery||0)>120000){
    await chrome.storage.local.set({lastResearchReadingRecovery:Date.now()});
    await call('/api/bridge/retry-research',{client:cfg.client});
   }
   if(cfg.role!=='flow'&&Date.now()-(cfg.lastMediaRecovery||0)>120000){
    await chrome.storage.local.set({lastMediaRecovery:Date.now()});
    if(await recoverExistingMedia(cfg))return;
   }
  }
  claimed=await call('/api/bridge/task?client='+encodeURIComponent(cfg.client)+'&lane='+(lane==='chat'?'chat':'video'));if(!claimed)return;
  // The task is followed under this lane's key, whatever its kind (an older studio may ignore lane).
  // A tab closed under the task before anything was sent (real case 06/11/2026 13:10 « No tab with id ») : open a
  // fresh one and try once more, instead of stopping the episode. Never after a submission.
  for(let attempt=0;;attempt++){
   try{await begin(claimed,await tabForTask(claimed,cfg,key),cfg,key);break;}
   catch(e){
    const saved=(await chrome.storage.local.get(key))[key];
    if(attempt>0||!/No tab with id|Tab .* not found|No tab with given id/i.test(e.message)||saved?.submitted||saved?.submissionIntent===true)throw e;
    await chrome.storage.local.remove(['flowTab']);
   }
  }
 }catch(e){
  const active=cfg?.[key]||(await chrome.storage.local.get(key))[key];
  const task=claimed||active?.task;
  if(/fetch|network|Failed to fetch|Studio inaccessible/i.test(e.message)&&active){
   await chrome.storage.local.set({status:'Studio momentanément inaccessible. Réponse conservée, nouvel essai automatique.'});return;
  }
  if(task&&cfg?.client)try{await call('/api/bridge/result',{task:task.id,client:cfg.client,result:{ok:false,error:e.message,...(e.flowBlocked?{flow_blocked:e.flowBlocked}:{}),...(e.notReady?{not_ready:e.notReady}:{}),...(task.kind==='flow_video'&&((claimed&&!active)||(active?.submissionIntent===false&&!active.submitted))?{generation_submitted:false}:{})}});}catch{}
  if(active){const data=await chrome.storage.local.get('scenarioTabs');const tabs=data.scenarioTabs||{};if(tabs[active.task.job])tabs[active.task.job].pending=false;await chrome.storage.local.set({scenarioTabs:tabs});}
  await chrome.storage.local.remove(key);
  await chrome.storage.local.set({status:'À vérifier : '+e.message});
 }finally{busy[lane]=false;}
}
async function recoverExistingMedia(cfg){
 const candidates=await call('/api/bridge/recoverable-media?client='+encodeURIComponent(cfg.client));
 if(!candidates.length)return false;
 const tabs=await chrome.tabs.query({url:'https://chatgpt.com/*'});
 for(const old of candidates)for(const tab of tabs){
  let result;
  try{
   await chrome.scripting.executeScript({target:{tabId:tab.id},files:['media.js','chat-session.js']});
   result=await chrome.tabs.sendMessage(tab.id,{type:'frucht-media-probe',prompt:old.payload.prompt});
  }catch{continue;}
  if(!result?.matched)continue;
  if(!result.ok){await chrome.storage.local.set({status:'Image de la production retrouvée : '+result.error});return false;}
  const task=await call('/api/bridge/recover-media',{client:cfg.client,previous_task:old.id});
  const active={task,tabId:tab.id,client:cfg.client,startedAt:Date.now(),pendingResult:result};
  await finish(active,result);return true;
 }
 return false;
}
async function recoverExistingVideo(cfg){
 const candidates=await call('/api/bridge/recoverable-videos?client='+encodeURIComponent(cfg.client));
 if(!candidates.length)return false;
 const tabs=await chrome.tabs.query({url:['https://flow.google.com/*','https://labs.google/*']});
 for(const old of candidates)for(const tab of tabs){
  let result;
  try{
   await chrome.scripting.executeScript({target:{tabId:tab.id},files:['media.js','flow-controls.js','flow-download.js','chat-session.js']});
   result=await chrome.tabs.sendMessage(tab.id,{type:'frucht-video-probe',prompt:old.payload.prompt});
  }catch{continue;}
  if(!result?.matched)continue;
  if(!result.ok&&!result.canDownload){await chrome.storage.local.set({status:'Clip retrouvé : '+result.error});continue;}
  const task=await call('/api/bridge/recover-video',{client:cfg.client,previous_task:old.id});
  const active={task,key:LANE_KEY.video,tabId:tab.id,client:cfg.client,startedAt:Date.now()};
  if(result.ok)await finish(active,result);else await requestFlowDownload(active);
  return true;
 }
 return false;
}
async function requestFlowDownload(active){
 if(!chrome.downloads?.search)throw Error('Rechargez l’extension pour autoriser le suivi des téléchargements Flow.');
 active.download={requestedAt:new Date().toISOString()};
 await saveActive(active,{status:'Récupération automatique du clip original 720p…'});
 await call('/api/bridge/progress',{task:active.task.id,client:active.client,message:'Téléchargement automatique du clip original 720p ; aucune nouvelle génération.'});
 const response=await chrome.tabs.sendMessage(active.tabId,{type:'frucht-flow-download',task:active.task.id,prompt:active.task.payload.prompt});
 if(!response?.accepted)throw Error(response?.error||'Commande de téléchargement indisponible.');
}
async function pollFlowDownload(active){
 const request=active.download;
 const items=await chrome.downloads.search(request.id!==undefined?{id:request.id}:{startedAfter:request.requestedAt,orderBy:['-startTime'],limit:12});
 const item=request.id!==undefined?items[0]:FruchtDownloads.choose(items,request);
 // Chrome may finish while the service worker sleeps. Inspect that result
 // before declaring a timeout; Flow can take minutes to prepare its download.
 if((!item||item.state!=='complete')&&Date.now()-Date.parse(request.requestedAt)>FruchtDownloads.timeoutMs)throw Error('Le téléchargement Flow n’a pas abouti après cinq minutes. Aucune nouvelle génération lancée.');
 if(!item){await chrome.storage.local.set({status:'Téléchargement Flow en attente…'});return;}
 if(request.id===undefined){request.id=item.id;await saveActive(active);}
 if(item.danger&&!['safe','deepScannedSafe','allowlistedByPolicy'].includes(item.danger))throw Error('Chrome demande une vérification du téléchargement. Aucune protection contournée.');
 if(item.state==='interrupted'){
  if(item.canResume&&/^NETWORK_/.test(item.error||'')&&!request.resumed){request.resumed=true;await saveActive(active);await chrome.downloads.resume(item.id);return;}
  throw Error('Téléchargement Flow interrompu : '+(item.error||'raison non disponible'));
 }
 if(item.state!=='complete')return;
 if(item.exists===false)throw Error('Le clip téléchargé est introuvable.');
 const imported=await call('/api/bridge/import-download',{task:active.task.id,client:active.client,download_id:item.id,filename:item.filename,size:item.fileSize>=0?item.fileSize:item.bytesReceived});
 await finish(active,{ok:true,file:imported.file});
}
// owned: called from the poll loop, which already holds both lane flags (studio-page buttons).
// recover and tidy work on chat tabs: they wait for the chat lane only.
async function recover(job,owned=false){
 if(!owned){if(busy.chat)throw Error('Le connecteur est occupé. Réessayez dans quelques secondes.');busy.chat=true;}
 let task,cfg;
 try{
  cfg=await chrome.storage.local.get(null);if(!cfg.client||!cfg.token)throw Error('Appairez d’abord l’extension.');
  if(cfg.activeTask)throw Error('Une tâche est déjà suivie. Attendez sa fin avant de récupérer une autre réponse.');
  const tab=await FruchtWorkspace.latest(chrome,/^https:\/\/(chatgpt\.com|claude\.ai)\//);
  if(!tab)throw Error('Ouvrez d’abord, dans la fenêtre FruchtDrama, l’onglet qui contient la réponse terminée.');
  task=await call('/api/bridge/recover',{client:cfg.client,job});
  await begin(task,tab,cfg);return {ok:true,message:'Récupération lancée dans cet onglet. Aucun nouveau prompt envoyé.'};
 }catch(e){
  if(task)try{await call('/api/bridge/result',{task:task.id,client:cfg.client,result:{ok:false,error:e.message}});}catch{}
  throw e;
 }finally{if(!owned)busy.chat=false;}
}
async function recordBackgroundError(error){try{await chrome.storage.local.set({status:'Connecteur : '+(error?.message||String(error))});}catch{}}
async function tidyChats(owned=false){
 if(!owned){if(busy.chat)throw Error('La passerelle est occupée. Réessayez dans quelques secondes.');busy.chat=true;}
 try{
  const cfg=await chrome.storage.local.get(null);
  if(!cfg.client||!cfg.token)throw Error('Appairez d’abord la passerelle.');
  if(cfg.activeTask)throw Error('Attendez la fin de la tâche suivie avant de ranger les onglets.');
  const data=await call('/api/state');
  const result=await FruchtChats.tidy(cfg,data.tasks,chrome);
  await chrome.storage.local.set({status:result.message});return result;
 }finally{if(!owned)busy.chat=false;}
}
// Project URLs with or without an account prefix: /project/<id>, /u/1/project/<id>, /fx/tools/flow/project/<id>.
const FLOW_PROJECT=/^https:\/\/(flow\.google\.com|labs\.google)\/(?:[^?#]*\/)?project\//;
async function registerFlow(owned=false){
 const cfg=await chrome.storage.local.get(null);
 if(!cfg.client||!cfg.token)throw Error('Appairez d’abord la passerelle au studio.');
 // The Flow tab is the video lane's: nothing followed in either lane, no pass in progress.
 if(cfg.activeTask||cfg.activeVideoTask||cfg.activeVideoTask2||((busy.chat||busy.video||busy.video2)&&!owned))throw Error('Attendez la fin de la tâche en cours avant de mémoriser ce compte.');
 if(cfg.role==='creation')throw Error('Ce navigateur est réservé à votre IA ; utilisez la passerelle Flow.');
 const tab=await FruchtWorkspace.latest(chrome,FLOW_PROJECT);
 if(!FruchtFlowSession.project(tab?.url))throw Error('Ouvrez, dans la fenêtre FruchtDrama, le projet Flow du compte à mémoriser, puis cliquez ici.');
 const base=FruchtFlowSession.project(tab.url);
 if(tab.url!==base){await chrome.tabs.update(tab.id,{url:base});await ready(tab.id,{kind:'flow_video',payload:{}},base);}
 await chrome.scripting.executeScript({target:{tabId:tab.id},files:['flow-session.js']});
 const account=await chrome.tabs.sendMessage(tab.id,{type:'frucht-flow-session'});
 if(!account)throw Error('Compte Google non identifiable. Vérifiez la connexion dans Flow.');
 await call('/api/bridge/register-flow',{client:cfg.client,...account});
 return {ok:true,message:'Compte Flow mémorisé. Ouverture et passage automatiques activés.'};
}
function triggerPoll(){poll().catch(recordBackgroundError);}
function createAlarm(){try{Promise.resolve(chrome.alarms.create('studio-poll',{periodInMinutes:.5})).catch(recordBackgroundError);}catch(e){recordBackgroundError(e);}}
chrome.runtime.onInstalled.addListener(createAlarm);
chrome.runtime.onStartup.addListener(createAlarm);
chrome.runtime.onStartup.addListener(()=>FruchtStudio.ensure(chrome,fetch,{wait:false}).catch(recordBackgroundError));
chrome.runtime.onStartup.addListener(()=>FruchtWorkspace.reset(chrome).catch(recordBackgroundError));
// P5-1: the icon opens the FruchtDrama window; everything happens inside it.
// Like the Atelier: the window opens with the sites already signed in (ChatGPT, Grok, Flow), then the
// sessions are re-checked and every Flow account's real credits are read again.
async function openWorkspace(){
 const studio=await FruchtStudio.ensure(chrome,fetch);
 if(!studio.ok){await chrome.windows.create({url:FruchtStudio.offPage(chrome,studio.error),focused:true,type:'normal'});return;}
 const fresh=(await FruchtWorkspace.windowId(chrome))===null;
 await FruchtWorkspace.open(chrome);
 if(!fresh)return;
 const tabs=await chrome.tabs.query({});
 for(const url of ['https://chatgpt.com/','https://grok.com/imagine','https://flow.google.com/']){
  const host=new URL(url).hostname;if(!tabs.some(t=>{try{return new URL(t.url||t.pendingUrl).hostname===host;}catch{return false;}}))await FruchtWorkspace.createTab(chrome,{url,active:false});
 }
 const cfg=await chrome.storage.local.get(null);if(!cfg.client||!cfg.token||!cfg.enabled)return;
 try{const sites=await FruchtSites.check(chrome,FruchtWorkspace);await call('/api/bridge/sites',{client:cfg.client,sites});const accounts=await FruchtFlowScan.scan(chrome,FruchtWorkspace);const b=await call('/api/bridge/flow-scan',{client:cfg.client,accounts});await call('/api/bridge/notice',{client:cfg.client,action:'scan_flow',ok:true,text:b.message});}catch(e){recordBackgroundError(e);}
 // « Préparer mes comptes » at each opening of the window: every account read in the background (next pass).
 try{await call('/api/bridge/readiness-request',{client:cfg.client});triggerPoll();}catch(e){recordBackgroundError(e);}
}
chrome.action?.onClicked?.addListener(()=>openWorkspace().catch(recordBackgroundError));
chrome.windows?.onRemoved?.addListener(id=>FruchtWorkspace.closed(chrome,id).catch(recordBackgroundError));
chrome.alarms.onAlarm.addListener(a=>{if(a.name==='studio-poll')triggerPoll();});
chrome.downloads?.onCreated?.addListener(()=>triggerPoll());
chrome.downloads?.onChanged?.addListener(change=>{if(change.state||change.error||change.filename)triggerPoll();});
chrome.runtime.onMessage.addListener((m,s,reply)=>{
 if(m.type==='start-studio'){FruchtStudio.ensure(chrome,fetch).then(reply).catch(e=>reply({ok:false,error:e.message}));return true;}
 if(m.type==='tidy-chats'){
  tidyChats().then(reply).catch(e=>reply({ok:false,error:e.message}));return true;
 }
 if(m.type==='register-flow'){
  registerFlow().then(reply).catch(e=>reply({ok:false,error:e.message}));return true;
 }
 if(m.type==='submission-intent'){
  // The tab and task say which lane is about to send.
  chrome.storage.local.get(Object.values(LANE_KEY)).then(async cfg=>{
   const key=Object.values(LANE_KEY).find(k=>FruchtRecovery.sameReply(cfg[k],m.task,s.tab?.id));
   if(!key){reply({ok:false});return;}
   await chrome.storage.local.set({[key]:{...cfg[key],submissionIntent:true}});reply({ok:true});
  }).catch(e=>{try{reply({ok:false,error:e.message});}catch{}});return true;
 }
 if(m.type==='poll'){triggerPoll();return false;}
 if(m.type==='recover'){recover(m.job).then(value=>{try{reply(value);}catch{}}).catch(e=>{try{reply({ok:false,error:e.message});}catch{}});return true;}
 if(m.type==='result-ready'){
  chrome.storage.local.get(Object.values(LANE_KEY)).then(cfg=>{if(Object.values(LANE_KEY).some(k=>FruchtRecovery.sameReply(cfg[k],m.task,s.tab?.id)))triggerPoll();}).catch(recordBackgroundError);return false;
 }
 return false;
});
