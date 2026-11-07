// The extension starts the local studio itself (Atelier-like: open Chrome, click the icon, it works).
// The studio is a program on this computer (montage, transcription); Chrome reaches it through the
// native host registered once by Installer.cmd / installer.sh, wherever the FruchtDrama folder is.
globalThis.FruchtStudio={
 HOST:'com.fruchtdrama.studio',
 URL:'http://127.0.0.1:8840/',
 INSTALL:'Le studio FruchtDrama n’est pas installé sur cet ordinateur : ouvrez le dossier FruchtDrama et lancez une fois Installer.cmd (Windows) ou installer.sh (Linux), puis cliquez Réessayer.',
 async alive(fetchFn){
  const ctl=new AbortController();const timer=setTimeout(()=>ctl.abort(),2000);
  try{const r=await fetchFn(this.URL,{signal:ctl.signal,cache:'no-store'});return r.ok;}catch{return false;}finally{clearTimeout(timer);}
 },
 // wait=false (30 s loop): ask once and return; the next pass finds it running. wait=true (icon click): up to ~20 s.
 async ensure(chrome,fetchFn,{wait=true,sleep=ms=>new Promise(r=>setTimeout(r,ms)),now=Date.now}={}){
  if(await this.alive(fetchFn))return {ok:true};
  const {studioStartAt}=await chrome.storage.local.get('studioStartAt');
  if(!wait&&now()-(studioStartAt||0)<60000)return {ok:false,error:'Démarrage du studio déjà demandé.'};
  await chrome.storage.local.set({studioStartAt:now()});
  let reply;
  try{reply=await chrome.runtime.sendNativeMessage(this.HOST,{cmd:'start'});}
  catch(e){return {ok:false,missing:true,error:/not found|introuvable|forbidden|interdit/i.test(e?.message||'')?this.INSTALL:'Démarrage impossible : '+(e?.message||e)};}
  if(!reply?.ok)return {ok:false,error:reply?.error||'Le studio n’a pas répondu.'};
  if(!wait)return {ok:true,starting:true};
  for(let i=0;i<40;i++){if(await this.alive(fetchFn))return {ok:true,started:true};await sleep(500);}
  return {ok:false,error:'Le studio met trop de temps à démarrer. Consultez data/server-errors.log dans le dossier FruchtDrama.'};
 },
 offPage(chrome,error){return chrome.runtime.getURL('studio-off.html')+'#'+encodeURIComponent(error||'');}
};
