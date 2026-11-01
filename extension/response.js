globalThis.FruchtResponse={
 parse(text,expectedScenes,expectedJob,expectedTask,kind){
  const value=String(text||'').trim().slice(0,2000000);
  // UI text can include the user's example JSON and the generated JSON. Scan
  // balanced objects instead of joining the first opening and last closing brace.
  const objects=[];
  // A malformed example in the prompt must not consume the valid reply after it.
  // Scan each possible object start independently, newest first.
  for(let start=value.lastIndexOf('{');start>=0;start=value.lastIndexOf('{',start-1)){
   let depth=0,quoted=false,escaped=false;
   for(let i=start;i<value.length;i++){
    const c=value[i];
    if(quoted){if(escaped)escaped=false;else if(c==='\\')escaped=true;else if(c==='"')quoted=false;continue;}
    if(c==='"'){quoted=true;continue;}
    if(c==='{')depth++;
    else if(c==='}'&&--depth===0){objects.unshift(value.slice(start,i+1));break;}
   }
   if(start===0)break;
  }
  for(const object of objects.reverse())try{const parsed=JSON.parse(object);
   if(kind==='quality_review'){
    if(parsed?.production_id!==expectedJob||parsed?.generation_task_id!==expectedTask)continue;
    const q=parsed.quality_review;
    if(!q||!Array.isArray(q.scenes)||q.scenes.length!==expectedScenes||!q.scenes.every((x,i)=>x.index===i))continue;
    if(![...q.scenes,q.continuity].every(x=>x&&['pass','issue','uncertain'].includes(x.status)&&typeof x.detail==='string'&&x.detail.trim()))continue;
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
 extract(doc,n,job,task,kind){
  const texts=this.candidates(doc);
  // A provider layout change can remove all known assistant wrappers. Read main
  // only for a bound production, and accept ONLY its exact production_id.
  if(job){const main=doc.querySelector?.('main,[role="main"]');if(main)texts.push(main.innerText||main.textContent||'',main.textContent||'');}
  if(job&&task&&doc.body)texts.push(doc.body.innerText||'',doc.body.textContent||'');
  for(const text of texts){const parsed=this.parse(text,n,job,task,kind);if(parsed)return JSON.stringify(parsed);}return null;
 }
};

// A read-only status probe also works when an older collector is still running.
try{if(globalThis.fruchtScenarioProbe)chrome.runtime.onMessage.removeListener(globalThis.fruchtScenarioProbe);}catch{}
globalThis.fruchtScenarioProbe=(m,s,reply)=>{
 if(m.type!=='frucht-scenario-probe')return false;
 const texts=FruchtResponse.candidates(document),main=document.querySelector('main,[role="main"]');
 if(main)texts.push(main.innerText||main.textContent||'',main.textContent||'');
 if(m.job&&m.task&&document.body)texts.push(document.body.innerText||'',document.body.textContent||'');
 const text=FruchtResponse.extract(document,m.scenes,m.job,m.task,m.response_kind);
 const combined=texts.join('\n');
 const any=text?JSON.parse(text):texts.map(t=>FruchtResponse.parse(t)).find(Boolean);
 reply({text,diagnostic:{candidates:texts.length,lengths:texts.map(t=>t.length).slice(0,5),hasJob:combined.includes(m.job),hasTask:combined.includes(m.task),parsedScenes:any?.scenes?.length||0,parsedJob:any?.production_id||null,parsedTask:any?.generation_task_id||null}});return false;
};
try{chrome.runtime.onMessage.addListener(globalThis.fruchtScenarioProbe);}catch{}
