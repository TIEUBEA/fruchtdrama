// Read only the visible Flow account panel. Never buy credits or change accounts.
globalThis.FruchtCredits={
 parse(scope,time=Date.now()){
  const pattern=/^([0-9][0-9\s.,\u00a0\u202f]*)\s*(?:Google Flow[- ]Guthabenpunkte|Google Flow credits|AI credits|crédits Google Flow|crédits IA)$/i;
  const values=[...scope.querySelectorAll('a,[role="link"]')].flatMap(el=>[el.innerText,el.textContent,el.getAttribute('aria-label')]).filter(Boolean).map(t=>String(t).replace(/\s+/g,' ').replace(/[\u200b\u200c\u200d]/g,'').trim().match(pattern)).filter(Boolean).map(m=>Number(m[1].replace(/[\s.,\u00a0\u202f]/g,'')));
  if(!values.length||new Set(values).size!==1||!Number.isInteger(values[0])||values[0]>100000)return null;
  const text=[scope.innerText,scope.textContent].filter(Boolean).join('\n');
  const reset=text.match(/(?:täglich um|daily (?:at|around)|(?:chaque jour|quotidiennement) à)\s*(\d{1,2}):(\d{2})/i);
  let reset_at=null,reset_label='';
  if(reset&&Number(reset[1])<24&&Number(reset[2])<60){
   const date=new Date(time);date.setHours(Number(reset[1]),Number(reset[2]),0,0);
   if(date.getTime()<=time)date.setDate(date.getDate()+1);
   reset_at=Math.floor(date.getTime()/1000)+120;reset_label=reset[0];
  }
  return {balance:values[0],reset_at,reset_label};
 },
 async read(doc,target){
  const identity=FruchtFlowSession.describe(doc);
  if(!identity)return {pending:true};
  if(identity.email!==target.email.toLowerCase()||identity.url!==FruchtFlowSession.project(target.url))return {ok:false,error:'Compte Flow différent : aucun solde modifié.'};
  const visible=el=>el.getClientRects().length&&!el.hidden;
  const panel=()=>[...doc.querySelectorAll('[role="dialog"]')].find(d=>visible(d)&&[d.innerText,d.textContent].some(t=>String(t||'').toLowerCase().includes(target.email.toLowerCase())));
  const scope=panel();
  if(!scope){
   const button=[...doc.querySelectorAll('button,[role="button"]')].find(b=>visible(b)&&/^(?:Kontodetails|Account details|Détails du compte)$/i.test(b.getAttribute('aria-label')||b.innerText||''));
   if(button&&Date.now()-(globalThis.fruchtCreditOpening||0)>5000){globalThis.fruchtCreditOpening=Date.now();button.click();}
   return {pending:true};
  }
  const parsed=this.parse(scope);if(!parsed)return {pending:true};
  if(globalThis.fruchtCreditOpening){
   const close=[...scope.querySelectorAll('button')].find(b=>/^(?:Konto-Steuerfeld schließen|Close account panel|Fermer le panneau du compte)$/i.test(b.getAttribute('aria-label')||b.innerText||''));close?.click();globalThis.fruchtCreditOpening=0;
  }
  return {ok:true,...identity,...parsed};
 },
 async check(cfg,chrome,call){
  if(cfg.role==='creation'||!cfg.enabled)return false;
  const lease=await call('/api/bridge/credit-check?client='+encodeURIComponent(cfg.client));if(!lease)return false;
  let result;
  try{
   const tabs=await chrome.tabs.query({url:['https://flow.google.com/*','https://labs.google/*']});
   let tab=tabs.find(t=>FruchtFlowSession.project(t.url)===lease.target.url);
   if(!tab)tab=await chrome.tabs.create({url:lease.target.url,active:false});
   const start=Date.now();
   while(Date.now()-start<90000){
    try{
     await chrome.scripting.executeScript({target:{tabId:tab.id},files:['flow-session.js','flow-credits.js']});
     result=await chrome.tabs.sendMessage(tab.id,{type:'frucht-credit-read',target:lease.target});
     if(result&&!result.pending)break;
    }catch{}
    await new Promise(resolve=>setTimeout(resolve,1000));
   }
   if(!result||result.pending)result={ok:false,error:'Session Flow indisponible ou connexion à renouveler ; solde inchangé.'};
  }catch(e){result={ok:false,error:'Vérification Flow interrompue : '+e.message};}
  await call('/api/bridge/credit-report',{id:lease.id,profile:lease.profile,client:cfg.client,result});
  await chrome.storage.local.set({status:result.ok?'Solde Flow vérifié : '+result.balance+' crédits.':'Crédits Flow : '+result.error});return true;
 }
};
try{if(globalThis.fruchtCreditHandler)chrome.runtime.onMessage.removeListener(globalThis.fruchtCreditHandler);}catch{}
globalThis.fruchtCreditHandler=(m,s,reply)=>{
 if(m.type!=='frucht-credit-read')return false;
 FruchtCredits.read(document,m.target).then(reply).catch(e=>reply({ok:false,error:e.message}));return true;
};
chrome.runtime.onMessage.addListener(globalThis.fruchtCreditHandler);
