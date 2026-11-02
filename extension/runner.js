async function notifyResult(task){
 try{await chrome.runtime.sendMessage({type:'result-ready',task});}catch{}
}
// A typed failure (P2-01): the studio decides between waiting, rewording, retrying or asking a human.
function fail(kind,message,extra={}){return Object.assign(Error(message),{kind},extra);}
function requireLiveExtension(){
 try{if(chrome.runtime.id)return;}catch{}
 throw Error('Extension reloaded: refresh this tab before resuming.');
}
// DOM-only adapters. No private endpoints, cookie export, or CAPTCHA handling.
{
try{if(globalThis.fruchtRunnerHandler)chrome.runtime.onMessage.removeListener(globalThis.fruchtRunnerHandler);}catch{}
globalThis.fruchtRunnerHandler=(m,s,reply)=>{
 if(m.type==='frucht-status'){reply(globalThis.fruchtRunState||{state:'absent'});return false;}
 if(m.type!=='frucht-run')return false;
 if(globalThis.fruchtRunState?.state==='running'){reply({accepted:false,error:'Une tâche est déjà en cours dans cet onglet.'});return false;}
 globalThis.fruchtRunState={state:'running',task:m.task.id};
 run(m.task,m.attachments).then(result=>{if(['flow_video','engine_video'].includes(m.task.kind))result.generation_submitted=globalThis.fruchtRunState.submitted===true;globalThis.fruchtRunState={...globalThis.fruchtRunState,state:'completed',task:m.task.id,result};return notifyResult(m.task.id);}).catch(e=>{globalThis.fruchtRunState={...globalThis.fruchtRunState,state:'completed',task:m.task.id,result:{ok:false,error:e.message,...(e.kind?{error_kind:e.kind}:{}),...(e.retryAfter?{retry_after:e.retryAfter}:{}),...(['flow_video','engine_video'].includes(m.task.kind)?{generation_submitted:globalThis.fruchtRunState.submitted===true,...(e.flowBlocked?{flow_blocked:e.flowBlocked}:{})}:{})}};return notifyResult(m.task.id);});
 reply({accepted:true,task:m.task.id});return false;
};chrome.runtime.onMessage.addListener(globalThis.fruchtRunnerHandler);
}
async function collectScenario(task){
 const n=task.payload.scene_count;let previous='',stable=0,maximumLength=0;const start=Date.now();
 while(Date.now()-start<(task.kind==='chat_collect'?20000:240000)){
  requireLiveExtension();const candidate=globalThis.FruchtResponse.extract(document,n,task.payload.expected_job,task.payload.expected_task,task.payload.response_kind);
  if(candidate){maximumLength=Math.max(maximumLength,candidate.length);stable=candidate===previous?stable+1:0;previous=candidate;if(stable>=2)return {ok:true,text:candidate};}
  else{stable=0;previous='';}
  await new Promise(r=>setTimeout(r,1500));
 }
 const candidates=globalThis.FruchtResponse.candidates(document);
 return {ok:false,recoverable:true,error:'Réponse JSON complète non détectée. La réponse peut être terminée mais sa structure reste à vérifier. Aucun nouveau prompt n’a été envoyé par la récupération. Diagnostic : '+JSON.stringify({candidateCount:candidates.length,maximumLength,expectedScenes:n,observedLengths:candidates.map(x=>x.length).slice(0,5)})};
}
async function run(task,attachments){
 const sleep=ms=>new Promise(r=>setTimeout(r,ms));
 const visible=el=>!!el&&el.getClientRects().length>0;
 const text=()=>document.body.innerText;
 const blocked=()=>{requireLiveExtension();const t=text();if(globalThis.FruchtComposer.challenge(document))throw fail('challenge','Contrôle du fournisseur : intervention manuelle nécessaire.');if(location.hostname==='accounts.google.com')throw fail('login','Connexion requise. Connectez-vous vous-même.')};
 const findEditor=()=>globalThis.FruchtComposer.editor(document);
 const fill=(el,value)=>{el.focus();if(el.tagName==='TEXTAREA'||el.tagName==='INPUT'){const setter=Object.getOwnPropertyDescriptor(el.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype,'value').set;setter.call(el,value);el.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:value}))}else{const selection=window.getSelection(),range=document.createRange();range.selectNodeContents(el);selection.removeAllRanges();selection.addRange(range);if(!document.execCommand('insertText',false,value)){el.textContent=value;el.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:value}))}}el.dispatchEvent(new Event('change',{bubbles:true}))};
 const waitFor=async(fn,timeout=30000)=>{const start=Date.now();while(Date.now()-start<timeout){blocked();const v=fn();if(v)return v;await sleep(1000)}throw fail('interface','Interface non reconnue ou délai dépassé. Utilisez le prompt et l’import manuel dans le studio.')};
 const count=s=>{if(!s)return null;const v=s.trim().replace(/\s/g,'').replace(',','.');const m=v.match(/^(\d+(?:\.\d+)?)\s*([kmb])?$/i);return m?Number(m[1])*({k:1e3,m:1e6,b:1e9}[m[2]?.toLowerCase()]||1):null};
 await sleep(1500);blocked();
 if(task.kind==='chat_collect')return collectScenario(task);
 // P5-09/P5-10: Grok Imagine and LMArena video.
 if(task.kind==='engine_video')return globalThis.FruchtEngines.run(task,attachments,{document,sleep,fill,blocked,fail,DataTransfer,File,Event,atob,now:()=>Date.now(),
  intent:async()=>(await chrome.runtime.sendMessage({type:'submission-intent',task:task.id}))?.ok===true,
  submitted:()=>{globalThis.fruchtRunState.submitted=true;},
  videoPayload:v=>globalThis.FruchtMedia.videoPayload(v),
  retryAfter:t=>globalThis.FruchtComposer.retryAfter?.(t)||null});
 if(task.kind==='tiktok_search'){
  await waitFor(()=>document.querySelector('a[href*="/video/"]'),45000);
  return {ok:true,candidates:globalThis.FruchtResearch.extract(document)};
 }
 const isFlow=task.kind==='flow_video';
 const checkFlowAccount=()=>{
  if(!isFlow)return;
  if(task.payload.flow_route&&!globalThis.FruchtFlowSession?.verify(document,task.payload.flow_route))throw Error('Compte Flow différent ou session expirée ; aucun envoi effectué.');
  if(globalThis.FruchtFlow.creditBlocked(document)){const error=Error('Crédits Flow insuffisants signalés par le fournisseur ; aucun envoi effectué.');error.flowBlocked='credits';error.kind='credits';throw error;}
 };
 if(isFlow){globalThis.FruchtFlow.closeAccountPanel(document);await sleep(250);if(task.payload.flow_route||task.payload.model)await globalThis.FruchtFlow.prepareFrames(document,sleep,task.payload.cost,task.payload.model,task.payload.resolution,task.payload.seconds);}
 let editor=await waitFor(findEditor,45000);
 checkFlowAccount();
 if(attachments?.length){
  const input=isFlow?await globalThis.FruchtFlow.openImport(document,sleep,attachments[0].name):await globalThis.FruchtComposer.openImport(document,sleep);
  if(!input)throw Error('Image import control unavailable.');
  if(!input.existingReference&&!input.alreadyAttached){
   const dt=new DataTransfer();
   for(const a of attachments){const bin=atob(a.data),bytes=Uint8Array.from(bin,c=>c.charCodeAt(0));dt.items.add(new File([bytes],a.name,{type:a.mime||'image/png'}));}
   input.files=dt.files;input.dispatchEvent(new Event('change',{bubbles:true}));
  }
  if(isFlow&&!input.alreadyAttached)await globalThis.FruchtFlow.confirmImport(document,sleep,message=>{requireLiveExtension();globalThis.fruchtRunState.progress=message;},attachments[0].name,input);
  else if(!isFlow)await sleep(3500);
  editor=findEditor()||editor;
 }

 if(isFlow){
  // A visible cost must match. Never click when the cost is unknown.
  if(task.payload.flow_route||task.payload.model)await globalThis.FruchtFlow.configure(document,sleep,task.payload.cost,task.payload.model,task.payload.resolution,task.payload.seconds);
  const settings=globalThis.FruchtFlow.settingsButton(document);
  let cost=globalThis.FruchtFlow.cost(text()),openedSettings=false;
  if((cost===null||globalThis.FruchtFlow.outputCount(document,settings)===null)&&settings){settings.click();openedSettings=true;await sleep(700);cost=globalThis.FruchtFlow.cost(text());}
  if(globalThis.FruchtFlow.outputCount(document,settings)!==1)throw Error('Flow : choisissez x1 (un résultat) dans les paramètres. Aucun envoi effectué.');
  if(cost===null)throw Error('Flow : coût de génération non lisible. Vérifiez le modèle, x1 et le coût, puis générez et importez le clip manuellement. Aucun envoi effectué.');
  if(task.payload.model)globalThis.FruchtFlow.verifyModel(document,task.payload.model,task.payload.resolution,task.payload.seconds);
  if(cost!==task.payload.cost||cost>task.payload.balance)throw Error('Flow : coût affiché différent du budget prévu. Aucun envoi effectué.');
  if(!settings&&/(?:x\s*2|x\s*4)\b/i.test(text()))throw Error('Flow : vérifiez que le nombre de résultats est x1. Aucun envoi effectué.');
  if(openedSettings){settings.click();await sleep(400);}
 }
 const oldAssistants=new Set(globalThis.FruchtComposer.assistants?.(document)||[]);const oldImageElements=new Set([...document.images]);const oldImages=new Set([...document.images].map(i=>i.currentSrc||i.src));const oldVideos=new Set([...document.querySelectorAll('video')].map(v=>v.currentSrc||v.src));
 const prompt=task.payload.prompt+(task.kind==='chat_image'?'\nGenerate the image now, not a written tutorial.':'');fill(editor,prompt);await sleep(700);
 const findSend=()=>isFlow?globalThis.FruchtFlow.sendButton(document,editor):globalThis.FruchtComposer.button(document,editor);
 let send=null;const buttonStart=Date.now();while(Date.now()-buttonStart<(attachments?.length?180000:25000)){blocked();checkFlowAccount();editor=findEditor()||editor;send=findSend();if(send)break;await sleep(700)}
 if(!send){const diagnostic=globalThis.FruchtComposer.diagnostic(document,editor);return {ok:false,error:'Envoi bloqué : '+(diagnostic.editor?.length?'texte présent, commande inactive ou non reconnue.':'le texte n’a pas été accepté par l’éditeur.')+' Diagnostic technique : '+JSON.stringify(diagnostic),diagnostic};}
 if(isFlow&&/buy|acheter|upgrade|abonn|subscribe|purchase/i.test(send.innerText+' '+send.getAttribute('aria-label')))throw Error('Achat interdit par le budget zéro.');
 checkFlowAccount();requireLiveExtension();
 // Dry run (P1-4): everything is configured and verified in Flow, nothing is sent or charged.
 if(isFlow&&task.payload.dry_run===true)return {ok:false,dry_run:true,generation_submitted:false,error:'Essai à blanc réussi : modèle, coût ('+task.payload.cost+' crédits), format, image et prompt prêts dans Flow. Rien n’a été envoyé ni facturé.'};
 const intent=await chrome.runtime.sendMessage({type:'submission-intent',task:task.id});if(!intent?.ok)throw Error('Envoi suspendu : association de la tâche perdue. Aucun prompt envoyé.');send.click();globalThis.fruchtRunState.submitted=true;await sleep(2500);
 if(task.kind==='chat_text'){
  return collectScenario(task);
 }
 let previewOpened=false,lastRefusal=null;const start=Date.now();while(Date.now()-start<480000){blocked();if(isFlow){if(!previewOpened)previewOpened=globalThis.FruchtFlow.openNewVideo(document,oldImages,oldImageElements);const v=[...document.querySelectorAll('video')].find(v=>(v.currentSrc||v.src)&&!oldVideos.has(v.currentSrc||v.src)&&v.readyState>=1);if(v){return await globalThis.FruchtMedia.videoPayload(v)}}else{const candidate=globalThis.FruchtMedia.image(document,task.payload.prompt);const img=candidate&&!oldImages.has(candidate.currentSrc||candidate.src)?candidate:null;if(img&&!/avatar|profile/i.test(img.alt)){await sleep(2000);return await globalThis.FruchtMedia.payload(img)}
  // A refusal is confirmed by two identical readings of a NEW reply (P2-03): no 8-minute wait.
  const refusal=globalThis.FruchtComposer.refusal?.(document,oldAssistants)||null;
  if(refusal&&refusal===lastRefusal)throw fail('refusal','ChatGPT refuse cette image (refus de contenu) : '+refusal.slice(0,240));
  lastRefusal=refusal;}
 if(/you.ve reached|you.ve hit|limit reached|quota atteint|limite atteinte|usage limit/i.test(text()))throw fail('quota','Quota du fournisseur atteint. Reprenez après renouvellement.',{retryAfter:globalThis.FruchtComposer.retryAfter?.(text())||null});await sleep(2000)}throw fail('timeout','Génération trop longue ou média non détecté. Vérifiez le projet avant toute nouvelle tentative.');
}
