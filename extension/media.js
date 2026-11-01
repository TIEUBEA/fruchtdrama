// Recover only a displayed image associated with the exact generation prompt.
globalThis.FruchtMedia={
 normalize(value){return String(value||'').replace(/\s+/g,' ').trim();},
 nodeMatches(node,prompt){
  const expected=this.normalize(prompt);
  return expected.length>=40&&[node?.innerText,node?.textContent].some(t=>this.normalize(t).includes(expected));
 },
 promptNodes(doc,prompt){
  const users=[...doc.querySelectorAll('[data-message-author-role="user"],[data-turn="user"]')];
  if(users.length)return users;
  // New ChatGPT image pages omit user-turn wrappers. Require a block containing
  // exactly this request, rather than using the entire conversation as a turn.
  const expected=this.normalize(prompt),suffix=' Generate the image now, not a written tutorial.';
  const nodes=[...doc.querySelectorAll('main *,[role="main"] *')].filter(n=>[n.innerText,n.textContent].some(t=>{const v=this.normalize(t);return v===expected||v===expected+suffix;}));
  return nodes.filter(n=>!nodes.some(child=>child!==n&&n.contains?.(child)));
 },
 matches(doc,prompt){
  const expected=this.normalize(prompt);if(expected.length<40)return false;
  const userNodes=[...doc.querySelectorAll('[data-message-author-role="user"],[data-turn="user"]')];
  if(userNodes.length)return userNodes.some(n=>this.nodeMatches(n,prompt));
  const main=doc.querySelector('main,[role="main"]');return !!main&&this.nodeMatches(main,prompt);
 },
 image(doc,prompt){
  let target=null,next=null;
  if(prompt){
   const users=this.promptNodes(doc,prompt);
   const index=users.findLastIndex(n=>this.nodeMatches(n,prompt));
   if(index<0)return null;
   target=users[index];next=users[index+1]||null;
   if(typeof target.compareDocumentPosition!=='function')return null;
  }
  return [...doc.images].filter(i=>{
   if(!i.complete||i.naturalWidth<512||i.naturalHeight<512||/avatar|profile/i.test(i.alt||'')||i.closest('form')||i.closest('[role="dialog"]'))return false;
   if(target&&(!(target.compareDocumentPosition(i)&4)||(next&&!(i.compareDocumentPosition(next)&4))))return false;
   const user=i.closest('[data-message-author-role="user"],[data-turn="user"]');
   if(user)return false;
   if(!user&&i.closest('[data-message-author-role="assistant"],[data-turn="assistant"]'))return true;
   // Generated-image cards can be siblings of the assistant text, not children.
   // An explicit generated-image control is required; attached user previews
   // have attachment controls and must never be treated as generated output.
   const button=i.closest('button,[role="button"]');
   if(!button?.getAttribute)return false;
   const label=button.getAttribute('aria-label')||button.getAttribute('title')||(!user?i.alt:'')||'';
   return /^(?:Generiertes Bild|Generated image|Image générée|Image créée)(?:\s+\d+)?$/i.test(label.trim());
  }).at(-1)||null;
 },
 localNetworkRetry(doc,prompt){
  const path=doc.location?.pathname||'';
  if(doc.location?.hostname!=='chatgpt.com'||!/^\/c\/local-chatgpt(?:%3A|:)/i.test(path)||!this.matches(doc,prompt)||this.image(doc,prompt))return null;
  const alerts=[...doc.querySelectorAll('[role="alert"]')];
  if(!alerts.some(a=>/^(?:Network error|Netzwerkfehler|Erreur réseau)(?:\s*(?:Erneut versuchen|Try again|Réessayer))?$/i.test((a.innerText||a.textContent||'').trim())))return null;
  if([...doc.querySelectorAll('button')].some(b=>/^(?:Stoppen|Stop generating|Arrêter|Anhalten)$/i.test(b.getAttribute('aria-label')||b.innerText||'')))return null;
  return alerts.flatMap(a=>[...a.querySelectorAll('button')]).find(b=>!b.disabled&&/^(?:Erneut versuchen|Try again|Réessayer)$/i.test((b.getAttribute('aria-label')||b.innerText||'').trim()))||null;
 },
 async encode(blob,limit=16*1024*1024){
  if(blob.size>limit)throw Error('Média supérieur à la taille autorisée.');
  const bytes=new Uint8Array(await blob.arrayBuffer());let text='';
  for(let i=0;i<bytes.length;i+=16384)text+=String.fromCharCode(...bytes.subarray(i,i+16384));
  return {ok:true,base64:btoa(text),mime:blob.type||'image/png'};
 },
 flowMatches(doc,prompt){
  return ['flow.google.com','labs.google'].includes(doc.location?.hostname)&&/\/project\/[^/]+\/edit\//.test(doc.location?.pathname||'')&&this.normalize(prompt).length>=100&&this.normalize(doc.body?.innerText).includes(this.normalize(prompt));
 },
 async videoPayload(video){
  const src=video.currentSrc||video.src;
  const url=new URL(src,location.href);
  if(!['https:','blob:'].includes(url.protocol))throw Error('Source vidéo non prise en charge.');
  const response=await fetch(src,{credentials:'include',signal:AbortSignal.timeout(30000)});
  if(!response.ok)throw Error('Lecture du clip affiché refusée.');
  let blob=await response.blob();
  if(!/^video\/(mp4|webm)(?:;|$)/i.test(blob.type)){
   const head=new Uint8Array(await blob.slice(0,12).arrayBuffer());
   const mp4=head.length>=8&&String.fromCharCode(...head.slice(4,8))==='ftyp';
   const webm=head[0]===0x1a&&head[1]===0x45&&head[2]===0xdf&&head[3]===0xa3;
   if(!mp4&&!webm)throw Error('Le média affiché n’est pas un fichier vidéo MP4 ou WebM lisible.');
   blob=new Blob([blob],{type:mp4?'video/mp4':'video/webm'});
  }
  return this.encode(blob,100*1024*1024);
 },
 async payload(img){
  const src=img.currentSrc||img.src;if(!src)throw Error('Image sans source affichée.');
  const url=new URL(src,location.href);
  if(!['https:','blob:','data:'].includes(url.protocol))throw Error('Format de source d’image non reconnu.');
  if(url.protocol==='data:'&&!/^data:image\/(png|jpeg|webp);base64,/i.test(src))throw Error('Format d’image intégré non reconnu.');
  try{
   const response=await fetch(src,{credentials:'include',signal:AbortSignal.timeout(20000)});
   if(response.ok){const blob=await response.blob();if(/^image\/(png|jpeg|webp)/i.test(blob.type))return await this.encode(blob);}
  }catch{}
  // Loaded same-origin/blob images can be serialized locally without a new
  // generation. A tainted cross-origin canvas is never bypassed.
  try{
   if(img.naturalWidth*img.naturalHeight>17000000)throw Error('Image trop grande.');
   const canvas=document.createElement('canvas');canvas.width=img.naturalWidth;canvas.height=img.naturalHeight;
   canvas.getContext('2d').drawImage(img,0,0);
   const blob=await new Promise((resolve,reject)=>canvas.toBlob(b=>b?resolve(b):reject(Error('Conversion impossible.')),'image/png'));
   return await this.encode(blob);
  }catch{throw Error('Image affichée mais lecture protégée par le navigateur ('+url.protocol+' '+(url.protocol==='https:'?url.hostname:'source temporaire')+'). Aucune nouvelle image générée.');}
 }
};
function safeMediaReply(reply,value){try{reply(value);}catch{}}
{
try{if(globalThis.fruchtMediaHandler)chrome.runtime.onMessage.removeListener(globalThis.fruchtMediaHandler);}catch{}
globalThis.fruchtMediaHandler=(m,s,reply)=>{
 if(m.type==='frucht-video-probe'){
  if(!FruchtMedia.flowMatches(document,m.prompt)){safeMediaReply(reply,{ok:false,matched:false});return false;}
  const canDownload=!!globalThis.FruchtFlow?.control(document,/^(?:Medien herunterladen|Download media|Télécharger le média|Télécharger le contenu multimédia)$/i);
  const video=[...document.querySelectorAll('video')].find(v=>(v.currentSrc||v.src)&&v.readyState>=1&&v.getClientRects().length);
  if(!video){safeMediaReply(reply,{ok:false,matched:true,canDownload,error:'Aperçu vidéo non accessible ; téléchargement original disponible.'});return false;}
  FruchtMedia.videoPayload(video).then(result=>safeMediaReply(reply,{...result,matched:true})).catch(e=>safeMediaReply(reply,{ok:false,matched:true,canDownload,error:e.message}));return true;
 }
 if(m.type==='frucht-retry-local-network'){const button=FruchtMedia.localNetworkRetry(document,m.prompt);if(!button){reply({retried:false});return false;}button.click();reply({retried:true});return false;}
 if(m.type!=='frucht-media-probe')return false;
 if(!FruchtMedia.matches(document,m.prompt)){reply({ok:false,matched:false});return false;}
 const image=FruchtMedia.image(document,m.prompt);if(!image){reply({ok:false,matched:true,localNetworkError:!!FruchtMedia.localNetworkRetry(document,m.prompt),error:'Image de la demande actuelle pas encore chargée.'});return false;}
 FruchtMedia.payload(image).then(result=>safeMediaReply(reply,{...result,matched:true})).catch(e=>safeMediaReply(reply,{ok:false,matched:true,error:e.message}));return true;
};chrome.runtime.onMessage.addListener(globalThis.fruchtMediaHandler);
}
