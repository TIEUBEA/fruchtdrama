globalThis.FruchtFlowDownload={
 requests:globalThis.FruchtFlowDownload?.requests||{},
 async execute(doc,prompt,task,pause){
  if(!FruchtMedia.flowMatches(doc,prompt))throw Error('Téléchargement suspendu : le prompt affiché ne correspond pas à la scène.');
  if(this.requests[task])return {accepted:true};
  const download=FruchtFlow.control(doc,/^(?:Medien herunterladen|Download media|Télécharger le média|Télécharger le contenu multimédia)$/i);
  if(!download)throw Error('Bouton de téléchargement du clip non disponible.');
  this.requests[task]=true;
  try{
   download.click();
   for(let n=0;n<40;n++){
    await pause(250);
    if(!FruchtMedia.flowMatches(doc,prompt))throw Error('La scène affichée a changé pendant le téléchargement.');
    const items=[...doc.querySelectorAll('[role="menuitem"]')].filter(el=>el.getClientRects().length&&!el.disabled&&el.getAttribute('aria-disabled')!=='true');
    const original=items.find(el=>/^720p\s*(?:Originalgröße|Original size|Taille d[’']origine|Taille originale)$/i.test((el.innerText||el.getAttribute('aria-label')||'').replace(/\s+/g,' ').trim()));
    if(original){original.click();return {accepted:true};}
   }
   throw Error('Option 720p originale non détectée ; aucune option payante sélectionnée.');
  }catch(e){delete this.requests[task];throw e;}
 }
};
try{if(globalThis.fruchtDownloadHandler)chrome.runtime.onMessage.removeListener(globalThis.fruchtDownloadHandler);}catch{}
globalThis.fruchtDownloadHandler=(m,s,reply)=>{
 if(m.type!=='frucht-flow-download')return false;
 FruchtFlowDownload.execute(document,m.prompt,m.task,ms=>new Promise(r=>setTimeout(r,ms))).then(value=>safeMediaReply(reply,value)).catch(e=>safeMediaReply(reply,{accepted:false,error:e.message}));
 return true;
};
chrome.runtime.onMessage.addListener(globalThis.fruchtDownloadHandler);
