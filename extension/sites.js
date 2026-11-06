// Atelier-like "Mes comptes": the studio uses the accounts already open in this Chrome and detects,
// site by site, whether the owner is signed in. Read-only checks; nothing is typed or sent.
globalThis.FruchtSites={
 list:{
  chatgpt:{url:'https://chatgpt.com/',hosts:['chatgpt.com']},
  flow:{url:'https://flow.google.com/',hosts:['flow.google.com','labs.google']},
  tiktok:{url:'https://www.tiktok.com/',hosts:['www.tiktok.com','tiktok.com']},
  grok:{url:'https://grok.com/imagine',hosts:['grok.com']},
  arena:{url:'https://arena.ai/video',hosts:['arena.ai','lmarena.ai']},
  vidogrid:{url:'https://vidogrid.ai/app/video-gen/grok',hosts:['vidogrid.ai','www.vidogrid.ai']},
  claude:{url:'https://claude.ai/new',hosts:['claude.ai']}
 },
 label(name){return {chatgpt:'ChatGPT',flow:'Google Flow',tiktok:'TikTok',grok:'Grok',arena:'LMArena',vidogrid:'Vidogrid',claude:'Claude'}[name]||name;},
 // Runs inside the site's tab.
 probe(name,doc){
  const visible=e=>{const r=e.getBoundingClientRect?.();return !!r&&r.width>4&&r.height>4;};
  const labels=[...doc.querySelectorAll('button,a,[role="button"]')].filter(visible).map(b=>[b.getAttribute('aria-label'),b.innerText].filter(Boolean).join(' ').replace(/\s+/g,' ').trim());
  const signIn=labels.some(l=>/^(log in|sign in|se connecter|connexion|anmelden|einloggen)(?: \1)?$/i.test(l));
  const email=(()=>{const t=[...doc.querySelectorAll('[aria-label*="@"],img[alt*="@"]')].map(e=>e.getAttribute('aria-label')||e.getAttribute('alt')).join(' ');return (t.match(/[^\s@()<>"']+@[^\s@()<>"']+\.[a-z]{2,}/i)||[])[0]?.toLowerCase()||null;})();
  const editor=!!doc.querySelector('textarea:not([disabled]),[contenteditable="true"]');
  const challenge=!!globalThis.FruchtComposer?.challenge(doc);
  const host=location.hostname;
  let connected;
  if(challenge)connected=false;
  else if(name==='flow')connected=!!email;
  else if(name==='claude')connected=editor&&!/\/login/.test(location.pathname);
  else if(name==='arena')connected=!signIn||editor;
  // Vidogrid (fruit-france vidogrid_verifier.py): signed in when the app shows its credits or the free trial; /auth/login otherwise.
  else if(name==='vidogrid')connected=!/\/auth\/login/.test(location.pathname)&&/Credits remaining|FREE TRIAL|Credits &/i.test(doc.body?.innerText||'');
  else connected=!signIn&&(name==='tiktok'||editor);
  return {connected,email,challenge,host};
 },
 // Service worker: check every site inside the FruchtDrama window, closing only the tabs it opened.
 async check(chrome,ws,wait=ms=>new Promise(r=>setTimeout(r,ms))){
  const out={},tabs=await chrome.tabs.query({});
  for(const [name,site] of Object.entries(this.list)){
   let tab=tabs.find(t=>{try{return site.hosts.includes(new URL(t.url).hostname);}catch{return false;}}),opened=false;
   try{
    if(!tab){tab=await ws.createTab(chrome,{url:site.url,active:false});opened=true;await wait(9000);}
    // A page still loading looks signed out (no editor yet): read it again a few times before saying so.
    for(let k=0;k<4;k++){
     const [r]=await chrome.scripting.executeScript({target:{tabId:tab.id},files:['composer.js','sites.js']}).then(()=>chrome.scripting.executeScript({target:{tabId:tab.id},func:n=>globalThis.FruchtSites.probe(n,document),args:[name]}));
     out[name]=r?.result||{connected:false};
     if(out[name].connected||out[name].challenge||k===3)break;
     await wait(4000);
    }
   }catch(e){out[name]={connected:false,error:String(e.message||e).slice(0,160)};}
   finally{if(opened&&tab)try{await ws.close(chrome,[tab.id]);}catch{}}
  }
  return out;
 }
};
