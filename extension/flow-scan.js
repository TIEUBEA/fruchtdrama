// "Détecter mes comptes" (owner request 03/11/2026, 25+ Google accounts): visit flow.google.com/u/0,
// /u/1, ... in one background tab of the FruchtDrama window and read, for each Google account already
// signed in to this Chrome profile, its address, its real Flow credits and one of its projects.
// Read-only: no click except opening and closing the account panel; nothing is bought or created.
globalThis.FruchtFlowScan={
 MAX:30,
 // Runs inside the Flow tab.
 async read(doc,wait){
  const email=globalThis.FruchtFlowSession.identity(doc);
  if(!email)return {email:null};
  const project=[...doc.querySelectorAll('a[href*="/project/"]')].map(a=>globalThis.FruchtFlowSession.project(a.href)).find(Boolean)||null;
  const visible=el=>el.getClientRects().length&&!el.hidden;
  let balance=null;
  for(let i=0;i<8&&balance===null;i++){
   const panel=[...doc.querySelectorAll('[role="dialog"]')].find(d=>visible(d)&&String(d.innerText||'').toLowerCase().includes(email));
   if(panel){balance=globalThis.FruchtCredits.parse(panel)?.balance??null;if(balance===null){const m=String(panel.innerText||'').match(/([0-9][0-9\s., ]*)\s*crédits?|([0-9][0-9\s., ]*)\s*credits?|([0-9][0-9\s., ]*)\s*Guthaben/i);if(m)balance=Number((m[1]||m[2]||m[3]).replace(/[^0-9]/g,''));}
    if(balance!==null){const close=[...panel.querySelectorAll('button')].find(b=>/schließen|close|fermer/i.test(b.getAttribute('aria-label')||''));close?.click();break;}}
   else{const b=[...doc.querySelectorAll('button,[role="button"]')].find(x=>visible(x)&&/^(?:Kontodetails|Account details|Détails du compte)$/i.test(x.getAttribute('aria-label')||x.innerText||''))||[...doc.querySelectorAll('button,[role="button"]')].find(x=>visible(x)&&/Google/i.test(x.getAttribute('aria-label')||'')&&(x.getAttribute('aria-label')||'').toLowerCase().includes(email));b?.click();}
   await wait(700);
  }
  return {email,balance,project};
 },
 // Service worker.
 async scan(chrome,ws,wait=ms=>new Promise(r=>setTimeout(r,ms))){
  const tab=await ws.createTab(chrome,{url:'https://flow.google.com/u/0/',active:false}),found=[],seen=new Set();let misses=0;
  try{
   for(let n=0;n<this.MAX&&misses<2;n++){
    await chrome.tabs.update(tab.id,{url:'https://flow.google.com/u/'+n+'/'});
    for(let i=0;i<30;i++){await wait(500);const t=await chrome.tabs.get(tab.id);if(t.status==='complete'&&(t.url||'').includes('flow.google.com'))break;}
    await wait(3500);
    const [r]=await chrome.scripting.executeScript({target:{tabId:tab.id},files:['flow-session.js','flow-credits.js','flow-scan.js']}).then(()=>chrome.scripting.executeScript({target:{tabId:tab.id},func:async()=>globalThis.FruchtFlowScan.read(document,ms=>new Promise(r=>setTimeout(r,ms)))}));
    const account=r?.result||{};
    const at=(await chrome.tabs.get(tab.id)).url||'';
    // Past the last account Google sends /u/N back to /u/0: the same address again ends the scan.
    if(!account.email||seen.has(account.email)||!at.includes('/u/'+n+'/')&&n>0){misses++;continue;}
    seen.add(account.email);misses=0;found.push({slot:n,...account});
   }
  }finally{try{await chrome.tabs.remove(tab.id);}catch{}}
  return found;
 }
};
