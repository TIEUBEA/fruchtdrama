// Grok Imagine, LMArena and Vidogrid video connectors (P5-09/P5-10, Vidogrid 0.1.93). Loaded both in the service worker
// (hosts, tab routing) and in the provider tab (DOM automation). DOM only: no private endpoint,
// no cookie export, no CAPTCHA handling, no credential entry.
globalThis.FruchtEngines={
 sites:{
  // Real pages 06/11/2026: a grok.com tab may sit on a chat or an old /imagine/post page (no composer file field):
  // each clip starts from a freshly loaded /imagine, like Vidogrid.
  grok:{label:'Grok Imagine',hosts:['grok.com','www.grok.com'],home:'https://grok.com/imagine',fresh:true,
   login:/\b(?:sign in|log in|sign up|create account)\b|se connecter|s.inscrire|anmelden|registrieren/i,
   loginSelector:'a[href*="sign-in"],a[href*="/login"],button[data-testid="login-button"]',
   videoMode:/^(?:video|vidéo|make video|créer une vidéo|video erstellen)$/i,
   send:/^(?:submit|send|generate|create|make video|envoyer|générer|créer|senden|generieren|erstellen)$/i,
   // « You've hit your weekly limit · Resets November 7 » (real toast, 06/11/2026); before sending, the composer
   // already shows a button « 100% credits used » (data-credit-notice).
   quota:/rate limit|too many requests|limit reached|(?:reached|hit) your (?:daily |weekly |monthly |video )?limit|100% credits used|upgrade to (?:supergrok|premium)|out of (?:free )?generations|limite atteinte|limite de (?:génération|vidéos)|Limit erreicht/i,
   refusal:/content moderated|moderated|violat\w* (?:our|the) (?:policy|policies|guidelines)|can.t generate (?:this|that)|unable to generate|contenu modéré|ne peut pas générer|Inhalt moderiert/i,
   timeout:4*60000},
  // Real check 02/11/2026: lmarena.ai now redirects to arena.ai/video.
  // Real page 06/11/2026: battle mode (2 anonymous models), « Video » is a menu (not a toggle), « Send message »
  // button, hidden <input type=file> for the image; a reused tab sits on /c/<conversation>: fresh page each clip.
  arena:{label:'LMArena vidéo',hosts:['arena.ai','www.arena.ai','lmarena.ai','www.lmarena.ai'],home:'https://arena.ai/video',fresh:true,
   login:/\b(?:sign in|log in)\b to (?:continue|generate|use video)|login required|se connecter pour|anmelden, um/i,
   loginSelector:'',
   videoMode:/^(?:video|vidéo)$/i,
   send:/^(?:send(?: message)?|submit|generate|run|envoyer|générer|senden|generieren)$/i,
   quota:/rate limit|too many requests|daily limit|limit reached|try again (?:later|in)|you.ve reached|limite atteinte|réessayez plus tard|Limit erreicht/i,
   refusal:/content (?:policy|filter|moderation)|flagged|violat\w* (?:our|the) (?:policy|policies|terms)|unsafe|cannot generate|contenu (?:refusé|signalé)|Inhaltsrichtlinie/i,
   timeout:7*60000},
  // vidogrid.ai, « Grok Imagine Video 1.5 Lite » (parcours réel : fruit-france/outils/vidogrid/vidogrid_clip.py, V57).
  // Signed in by the owner (« Continue with Google », never a password). One try: a failed generation goes to the next engine.
  vidogrid:{label:'Vidogrid',hosts:['vidogrid.ai','www.vidogrid.ai'],home:'https://vidogrid.ai/app/video-gen/grok',fresh:true,
   model:'Grok Imagine Video 1.5 Lite',
   send:/^GENERATE WITH GROK/i,
   failed:/Generation failed|REQUEST ERROR/i,
   quota:/not enough credits|insufficient credits|out of credits|limit reached|crédits insuffisants/i,
   refusal:/moderat|content polic|violat\w* (?:our|the) (?:policy|policies|terms)|unsafe|flagged/i,
   timeout:7*60000}
 },
 site(engine){const s=this.sites[engine];if(!s)throw Error('Moteur vidéo inconnu : '+engine);return s;},
 hosts(engine){return this.site(engine).hosts;},
 owns(engine,url){try{return this.site(engine).hosts.includes(new URL(url).hostname);}catch{return false;}},
 // Service worker: reuse this engine's tab inside the FruchtDrama window, or open its home page there.
 async tabFor(task,chrome){
  const engine=task.payload.engine,tabs=await chrome.tabs.query({});
  const own=tabs.find(t=>this.owns(engine,t.url||''));
  // Vidogrid keeps the last image and options in its form: each clip starts from a freshly loaded page.
  if(own&&this.site(engine).fresh)return globalThis.FruchtWorkspace.adopt(chrome,await chrome.tabs.update(own.id,{url:this.site(engine).home,active:false}));
  if(own)return globalThis.FruchtWorkspace.adopt(chrome,own);
  return globalThis.FruchtWorkspace.createTab(chrome,{url:this.site(engine).home,active:false});
 },
 label(el){return [el.getAttribute?.('aria-label'),el.getAttribute?.('title'),el.innerText,el.textContent].filter(Boolean).join(' ').replace(/\s+/g,' ').trim();},
 visible(el){if(!el||el.hidden||el.getAttribute?.('aria-hidden')==='true')return false;const r=el.getBoundingClientRect?.();return !!r&&r.width>4&&r.height>4;},
 buttons(doc){return [...doc.querySelectorAll('button,[role="button"],[role="tab"],[role="radio"]')].filter(b=>this.visible(b));},
 loggedOut(doc,engine){
  const site=this.site(engine);
  if(site.loginSelector&&[...doc.querySelectorAll(site.loginSelector)].some(e=>this.visible(e)))return true;
  return this.buttons(doc).some(b=>site.login.test(this.label(b)))&&!this.editor(doc);
 },
 // Signed-in identity when the page shows it (menu, avatar alt); null when unreadable.
 account(doc){
  const text=[...doc.querySelectorAll('[data-testid*="account"],[aria-label*="ccount"],[aria-label*="ompte"],img[alt*="@"]')].map(e=>this.label(e)+' '+(e.getAttribute?.('alt')||'')).join(' ');
  return text.match(/[^\s@<>()"']+@[^\s@<>()"']+\.[a-z]{2,}/i)?.[0]?.toLowerCase()||null;
 },
 editor(doc){
  const groups=['textarea:not([readonly]):not([disabled])','[contenteditable="true"][role="textbox"],[contenteditable="true"].ProseMirror','[contenteditable="true"]'];
  for(const q of groups){const e=[...doc.querySelectorAll(q)].find(x=>this.visible(x));if(e)return e;}
  return null;
 },
 // The composer's own field first: Grok /imagine has 3 hidden file fields, the first two belong to template cards
 // (« Text Edit », « Precise Edit ») and start another tool (real page 06/11/2026).
 fileInput(doc,editor){
  const ok=[...doc.querySelectorAll('input[type="file"]')].filter(i=>!i.disabled&&(!i.accept||/image|png|jpe?g|webp|\*/i.test(i.accept)));
  const form=editor?.closest?.('form');
  return (form&&ok.find(i=>form.contains(i)))||ok.find(i=>i.name==='files')||ok[ok.length-1]||null;
 },
 videoModeButton(doc,engine){
  // A menu trigger (Arena « Video ▾ », aria-haspopup) shows the current mode: clicking it only opens the menu.
  const b=this.buttons(doc).find(x=>this.site(engine).videoMode.test(this.label(x))&&!x.getAttribute('aria-haspopup'));
  if(!b)return null;
  const on=b.getAttribute('aria-pressed')==='true'||b.getAttribute('aria-selected')==='true'||b.getAttribute('aria-checked')==='true'||b.getAttribute('data-state')==='active'||b.getAttribute('data-state')==='on';
  return on?null:b;
 },
 sendButton(doc,engine){
  const site=this.site(engine);
  return this.buttons(doc).find(b=>!b.disabled&&b.getAttribute('aria-disabled')!=='true'&&site.send.test(this.label(b))&&!/buy|acheter|upgrade|subscribe|abonn|kaufen|premium/i.test(this.label(b)))||null;
 },
 // Messages that appear AFTER our submission only (the page may already show old ones).
 fresh(now,before){return now.length>before.length?now.slice(before.length):now.replace(before,'');},
 problem(text,engine){const s=this.site(engine);if(s.quota.test(text))return 'quota';if(s.refusal.test(text))return 'refusal';return null;},
 // Arena (preload="none") and Grok in a background tab keep readyState 0: an https .mp4 address is enough there.
 // Arena's own promo clip (/videos/cta/) is never ours.
 newVideo(doc,old){
  return [...doc.querySelectorAll('video')].find(v=>{const src=v.currentSrc||v.src||v.querySelector?.('source')?.src;if(!src||old.has(src)||/\/videos\/cta\//.test(src))return false;
   return (v.readyState>=1&&!(v.duration<2))||/^https:\/\/[^#?]+\.mp4(?:[?#]|$)/i.test(src);})||null;
 },
 // Grok shows its credit gauge in the composer; « 100% credits used » means the next video is refused.
 spent(doc){return [...doc.querySelectorAll('[data-credit-notice],button[aria-label]')].some(b=>/100\s*% credits used/i.test(b.getAttribute?.('aria-label')||''));},
 // « Resets November 7 » / « Resets Nov 7 »: seconds until that day (local midnight); null when unreadable.
 resetIn(text,now=new Date()){
  const m=String(text||'').match(/resets?\s+(?:on\s+)?(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})/i);if(!m)return null;
  const at=new Date(now.getFullYear(),'janfebmaraprmayjunjulaugsepoctnovdec'.indexOf(m[1].toLowerCase())/3,Number(m[2]));
  if(at<=now)at.setFullYear(at.getFullYear()+1);
  return Math.max(60,Math.round((at-now)/1000));
 },
 // Deepest visible element whose own text is exactly this label (Playwright get_by_text(exact=True) in the reference).
 exact(doc,label){
  const want=String(label).trim();
  return [...doc.querySelectorAll('button,[role="button"],[role="option"],[role="radio"],[role="tab"],label,div,span,p')].filter(e=>this.visible(e)&&String(e.innerText||e.textContent||'').trim()===want).pop()||null;
 },
 async runVidogrid(task,attachments,h){
  const site=this.site('vidogrid'),doc=h.document,text=()=>String(doc.body?.innerText||'');
  const none=' Aucun envoi effectué.';
  h.blocked();
  if(/\/auth\/login/.test(doc.location?.pathname||'')||!/Credits remaining|FREE TRIAL|Credits &|GENERATE WITH GROK/i.test(text()))
   throw h.fail('login','Vidogrid : connexion requise. Clique toi-même « Continue with Google » dans l’onglet de la fenêtre FruchtDrama (aucun mot de passe), puis Reprendre.'+none);
  this.exact(doc,'Don\'t show again')?.click();
  const model=this.exact(doc,site.model);if(model){model.click();await h.sleep(800);}
  else if(!text().includes('1.5 Lite'))throw h.fail('interface','Vidogrid : modèle « '+site.model+' » introuvable.'+none);
  if(attachments?.length){
   const slot=this.exact(doc,'0/1');
   if(!slot&&!text().includes('1/1'))throw h.fail('interface','Vidogrid : case d’image (0/1) introuvable.'+none);
   if(slot){
    (slot.previousElementSibling||slot).click();await h.sleep(1500);
    let input=null;for(let i=0;i<10&&!input;i++){input=this.fileInput(doc);if(!input)await h.sleep(500);}
    if(input){
     const dt=new h.DataTransfer();
     for(const a of attachments){const bin=h.atob(a.data),bytes=Uint8Array.from(bin,c=>c.charCodeAt(0));dt.items.add(new h.File([bytes],a.name,{type:a.mime||'image/png'}));}
     input.files=dt.files;input.dispatchEvent(new h.Event('change',{bubbles:true}));
    }else{
     // « Select Files » makes its own file field: the service worker gave this page the board (no file dialog).
     const pick=this.buttons(doc).find(b=>/^Select Files$/i.test(String(b.innerText||b.textContent||'').trim()));
     if(!pick)throw h.fail('interface','Vidogrid : bouton « Select Files » introuvable.'+none);
     pick.click();
    }
    // Import: 90 s without the image counted (1/1) is a failure before anything was sent (owner: no 10 min wait).
    let done=false;for(let i=0;i<90&&!done;i++){h.blocked();done=text().includes('1/1');if(!done)await h.sleep(1000);}
    if(!done)throw h.fail('interface','Vidogrid : image non importée après 90 s.'+none);
    this.exact(doc,'Done')?.click();await h.sleep(800);
   }
  }
  const editor=this.editor(doc);if(!editor)throw h.fail('interface','Vidogrid : zone de texte introuvable.'+none);
  h.fill(editor,('Start exactly from @image1 (first frame, same characters, same faces, same place). '+task.payload.prompt).slice(0,4990));await h.sleep(700);
  for(const label of [task.payload.aspect==='16:9'?'16:9':'9:16','720p','10s']){
   const option=this.exact(doc,label);if(!option)throw h.fail('interface','Vidogrid : réglage « '+label+' » introuvable.'+none);
   option.click();await h.sleep(400);
  }
  const box=[...doc.querySelectorAll('input[type="checkbox"],[role="checkbox"]')].find(b=>this.visible(b));
  if(box&&!(box.checked===true||box.getAttribute('aria-checked')==='true')){box.click();await h.sleep(300);}
  if(attachments?.length&&!text().includes('1/1'))throw h.fail('interface','Vidogrid : image non jointe au formulaire.'+none);
  const send=this.buttons(doc).find(b=>site.send.test(this.label(b))&&!b.disabled&&b.getAttribute('aria-disabled')!=='true');
  if(!send)throw h.fail('interface','Vidogrid : bouton « Generate with Grok » inactif ou introuvable.'+none);
  if(site.quota.test(text()))throw h.fail('quota','Vidogrid : crédits insuffisants sur ce compte.'+none);
  if(task.payload.dry_run===true)return {ok:false,dry_run:true,generation_submitted:false,error:'Essai à blanc réussi : Vidogrid prêt (Grok Lite, image, 9:16, 720p, 10 s, prompt). Rien n’a été envoyé.'};
  const old=new Set([...doc.querySelectorAll('video')].map(v=>v.currentSrc||v.src).filter(Boolean));
  if(!(await h.intent()))throw h.fail('interface','Envoi suspendu : association de la tâche perdue. Aucun prompt envoyé.');
  send.click();h.submitted();await h.sleep(5000);
  const start=h.now();
  while(h.now()-start<site.timeout){
   h.blocked();
   const all=text(),at=all.indexOf('OUTPUT'),output=at>=0?all.slice(at,at+600):all;
   if(site.failed.test(output)){
    const status=(output.match(/STATUS \d+/)||[''])[0];
    throw h.fail(site.refusal.test(output)?'refusal':'other','Vidogrid : génération échouée'+(status?' ('+status+')':'')+'. Rien à attendre de plus.');
   }
   const video=[...doc.querySelectorAll('video')].find(v=>{const src=v.currentSrc||v.src;return src&&/^https?:/.test(src)&&!src.includes('/showcase/')&&!old.has(src);});
   if(video){
    await h.sleep(1500);
    // The page may refuse to read a video from another address: the service worker then downloads it.
    try{return await h.videoPayload(video);}catch(e){return {ok:true,url:video.currentSrc||video.src,mime:'video/mp4'};}
   }
   await h.sleep(5000);
  }
  throw h.fail('timeout','Vidogrid : vidéo non détectée après '+Math.round(site.timeout/60000)+' minutes.');
 },
 async run(task,attachments,h){
  const engine=task.payload.engine,site=this.site(engine),doc=h.document;
  if(engine==='vidogrid')return this.runVidogrid(task,attachments,h);
  h.blocked();
  if(this.loggedOut(doc,engine))throw h.fail('login',site.label+' : connexion requise. Connectez-vous vous-même dans l’onglet de la fenêtre FruchtDrama, puis Reprendre.');
  const expected=String(task.payload.account?.email||'').toLowerCase();
  const shown=this.account(doc);
  if(expected&&shown&&shown!==expected)throw h.fail('login',site.label+' : le compte connecté ('+shown+') n’est pas le compte attendu ('+expected+'). Changez de compte dans l’onglet ; aucun envoi effectué.');
  const mode=this.videoModeButton(doc,engine);if(mode){mode.click();await h.sleep(800);}
  if(engine==='grok'&&this.spent(doc))throw h.fail('quota',site.label+' : limite du compte atteinte (« 100% credits used »). Aucun envoi effectué ; le clip passe au moteur suivant.');
  if(attachments?.length){
   // The page may still be building its composer: wait a little for the field.
   let input=null;for(let i=0;i<20&&!input;i++){input=this.fileInput(doc,this.editor(doc));if(!input)await h.sleep(500);}
   if(!input)throw h.fail('interface',site.label+' : champ d’image introuvable. Aucun envoi effectué.');
   const dt=new h.DataTransfer();
   for(const a of attachments){const bin=h.atob(a.data),bytes=Uint8Array.from(bin,c=>c.charCodeAt(0));dt.items.add(new h.File([bytes],a.name,{type:a.mime||'image/png'}));}
   input.files=dt.files;input.dispatchEvent(new h.Event('change',{bubbles:true}));await h.sleep(3000);
   // Grok: the board becomes the first frame (« Remove image » appears once it is uploaded).
   if(engine==='grok'){let up=false;for(let i=0;i<30&&!up;i++){up=this.buttons(doc).some(b=>/^Remove image$/i.test(b.getAttribute('aria-label')||''));if(!up)await h.sleep(1000);}
    if(!up)throw h.fail('interface',site.label+' : image non importée après 30 s. Aucun envoi effectué.');}
  }
  const editor=this.editor(doc);if(!editor)throw h.fail('interface',site.label+' : zone de texte introuvable. Aucun envoi effectué.');
  h.fill(editor,task.payload.prompt);await h.sleep(700);
  let send=null;for(let i=0;i<40&&!send;i++){h.blocked();send=this.sendButton(doc,engine);if(!send)await h.sleep(700);}
  if(!send)throw h.fail('interface',site.label+' : bouton de génération inactif ou introuvable. Aucun envoi effectué.');
  if(engine==='grok'&&this.spent(doc))throw h.fail('quota',site.label+' : limite du compte atteinte (« 100% credits used »). Aucun envoi effectué ; le clip passe au moteur suivant.');
  if(task.payload.dry_run===true)return {ok:false,dry_run:true,generation_submitted:false,error:'Essai à blanc réussi : '+site.label+' prêt (mode vidéo, image, prompt). Rien n’a été envoyé.'};
  const before=doc.body?.innerText||'',old=new Set([...doc.querySelectorAll('video')].map(v=>v.currentSrc||v.src).filter(Boolean));
  if(!(await h.intent()))throw h.fail('interface','Envoi suspendu : association de la tâche perdue. Aucun prompt envoyé.');
  send.click();h.submitted();await h.sleep(2500);
  const start=h.now();
  while(h.now()-start<(site.timeout||600000)){
   h.blocked();
   const video=this.newVideo(doc,old);if(video){await h.sleep(1500);return await h.videoPayload(video);}
   const kind=this.problem(this.fresh(doc.body?.innerText||'',before),engine);
   if(kind==='quota')throw h.fail('quota',site.label+' : limite du compte atteinte. Changez de compte ou attendez le renouvellement.',{retryAfter:h.retryAfter(doc.body?.innerText||'')||this.resetIn(doc.body?.innerText||'')});
   if(kind==='refusal')throw h.fail('refusal',site.label+' : génération refusée par la modération.');
   await h.sleep(2000);
  }
  throw h.fail('timeout',site.label+' : vidéo non détectée après '+Math.round((site.timeout||600000)/60000)+' minutes. Le clip passe au moteur suivant ; vérifiez l’onglet si besoin.');
 }
};
