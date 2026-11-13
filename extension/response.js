globalThis.FruchtResponse={
 parse(text,expectedScenes,expectedJob,expectedTask,kind){
  const value=String(text||'').trim().slice(0,2000000);
  if(expectedTask&&!value.includes(expectedTask))return null;
  const starts=[],objects=[];
  let quoted=false,escaped=false;
  for(let i=0;i<value.length;i++){
   const c=value[i];
   if(quoted){
    if(c==='\n'||c==='\r'){quoted=false;escaped=false;}
    else if(escaped)escaped=false;
    else if(c==='\\')escaped=true;
    else if(c==='"')quoted=false;
    continue;
   }
   if(c==='{')starts.push(i);
   else if(c==='"'&&starts.length)quoted=true;
   else if(c==='}'&&starts.length)objects.push([starts.pop(),i+1]);
  }
  for(let i=objects.length-1;i>=0;i--)try{
   const [start,end]=objects[i];
   if(expectedTask&&value.lastIndexOf(expectedTask,end-expectedTask.length)<start)continue;
   const parsed=JSON.parse(value.slice(start,end));
   if(kind==='flow_rewrite'){
    const scene=parsed?.scene_rewrite;
    if(parsed?.production_id===expectedJob&&parsed?.generation_task_id===expectedTask&&scene
       &&typeof scene.image_prompt==='string'&&typeof scene.video_prompt==='string')return parsed;
    continue;
   }
   if(kind==='quality_review'){
    if(parsed?.production_id!==expectedJob||parsed?.generation_task_id!==expectedTask)continue;
    const q=parsed.quality_review;
    if(!q||!Array.isArray(q.scenes)||q.scenes.length!==expectedScenes||!q.scenes.every((x,i)=>x.index===i))continue;
    if(![...q.scenes,q.continuity].every(x=>x&&['pass','issue','uncertain'].includes(x.status)&&typeof x.detail==='string'&&x.detail.trim()))continue;
    return parsed;
   }
   if(kind==='board_review'){
    // Board check before the clips: one verdict per board, bound to this exact task.
    if(parsed?.production_id!==expectedJob||parsed?.generation_task_id!==expectedTask)continue;
    const b=parsed.board_review?.boards;
    if(!Array.isArray(b)||b.length!==expectedScenes||!b.every((x,i)=>x&&x.index===i&&['pass','issue'].includes(x.status)&&typeof x.detail==='string'&&x.detail.trim()))continue;
    return parsed;
   }
   if(kind==='montage_review'){
    // « Vérifier et remonter »: one verdict on the montage with its fixes, bound to this exact task.
    if(parsed?.production_id!==expectedJob||parsed?.generation_task_id!==expectedTask)continue;
    if(!['ok','corriger'].includes(parsed.verdict)||(parsed.corrections!==undefined&&!Array.isArray(parsed.corrections)))continue;
    return parsed;
   }
   if(kind==='cover_review'){
    // Cover check of the full loop: one verdict, bound to this exact task.
    if(parsed?.production_id!==expectedJob||parsed?.generation_task_id!==expectedTask)continue;
    if(typeof parsed.ok!=='boolean')continue;
    return parsed;
   }
   if(kind==='meta'){
    if(parsed?.production_id!==expectedJob||parsed?.generation_task_id!==expectedTask)continue;
    if(typeof parsed.title!=='string'||typeof parsed.description!=='string')continue;
    return parsed;
   }
   if(kind==='ideas'||kind==='sheet'){
    // Story start (ten stories, decision sheet): only the reply bound to this exact task.
    if(parsed?.production_id!==expectedJob||parsed?.generation_task_id!==expectedTask)continue;
    if(kind==='ideas'&&!(Array.isArray(parsed.ideas)&&parsed.ideas.length>=6&&parsed.ideas.every(x=>x&&typeof x.title==='string'&&typeof x.pitch==='string')))continue;
    if(kind==='sheet'&&!(typeof parsed.logline==='string'&&Array.isArray(parsed.titles)&&Array.isArray(parsed.hooks)&&Array.isArray(parsed.cast)))continue;
    return parsed;
   }
   if(!parsed||typeof parsed.title!=='string'||!Array.isArray(parsed.characters)||!parsed.characters.length||!Array.isArray(parsed.scenes)||!parsed.scenes.length)continue;
   if(expectedScenes&&parsed.scenes.length!==expectedScenes)continue;
   if(expectedJob&&parsed.production_id!==expectedJob)continue;
   if(expectedTask&&parsed.generation_task_id!==expectedTask)continue;
   if(!parsed.scenes.every(s=>Array.isArray(s.dialogue)&&s.dialogue.length&&s.dialogue.every(l=>typeof l.speaker==='string'&&typeof l.text==='string')))continue;
   return parsed;
  }catch{}
  return null;
 },
 candidates(doc){
  const selectors=['[data-message-author-role="assistant"]','[data-turn="assistant"]','[data-testid="assistant-message"]','.font-claude-response'];
  let roots=[];
  for(const selector of selectors){roots=[...doc.querySelectorAll(selector)];if(roots.length)break;}
  if(!roots.length)roots=[...doc.querySelectorAll('article')].filter(e=>!e.matches('[data-turn="user"]'));
  if(roots.length)return roots.reverse().flatMap(root=>[...root.querySelectorAll('pre,code')].map(n=>n.innerText||n.textContent||'').reverse().concat(root.innerText||root.textContent||''));
  // Last resort: code blocks, excluding user turns and the composer.
  return [...doc.querySelectorAll('pre')].filter(n=>!n.closest('[data-message-author-role="user"],[data-turn="user"],[contenteditable="true"],form')).reverse().map(n=>n.innerText||n.textContent||'');
 },
 extract(doc,n,job,task,kind,texts=this.candidates(doc)){
  const seen=new Set();
  const tryText=text=>{
   if(!text||seen.has(text))return null;
   seen.add(text);
   const parsed=this.parse(text,n,job,task,kind);
   return parsed?JSON.stringify(parsed):null;
  };
  for(const text of texts){const parsed=tryText(text);if(parsed)return parsed;}
  // A provider layout change can remove all known assistant wrappers. Read main
  // only for a bound production, and accept ONLY its exact production_id.
  const main=job?doc.querySelector?.('main,[role="main"]'):null;
  const found=main&&(tryText(main.textContent)||tryText(main.innerText));
  if(found)return found;
  return job&&task&&doc.body?(tryText(doc.body.textContent)||tryText(doc.body.innerText)):null;
 }
};

// A read-only status probe also works when an older collector is still running.
try{if(globalThis.fruchtScenarioProbe)chrome.runtime.onMessage.removeListener(globalThis.fruchtScenarioProbe);}catch{}
globalThis.fruchtScenarioProbe=(m,s,reply)=>{
 if(m.type!=='frucht-scenario-probe')return false;
 const texts=FruchtResponse.candidates(document);
 const text=FruchtResponse.extract(document,m.scenes,m.job,m.task,m.response_kind,texts);
 const any=text?JSON.parse(text):null;
 reply({text,diagnostic:{candidates:texts.length,lengths:texts.map(t=>t.length).slice(0,5),hasJob:texts.some(t=>t.includes(m.job)),hasTask:texts.some(t=>t.includes(m.task)),parsedScenes:any?.scenes?.length||0,parsedJob:any?.production_id||null,parsedTask:any?.generation_task_id||null}});return false;
};
try{chrome.runtime.onMessage.addListener(globalThis.fruchtScenarioProbe);}catch{}
