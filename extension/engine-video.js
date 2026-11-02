// Grok Imagine and LMArena video connectors (P5-09/P5-10). Loaded both in the service worker
// (hosts, tab routing) and in the provider tab (DOM automation). DOM only: no private endpoint,
// no cookie export, no CAPTCHA handling, no credential entry.
globalThis.FruchtEngines={
 sites:{
  grok:{label:'Grok Imagine',hosts:['grok.com','www.grok.com'],home:'https://grok.com/imagine',
   login:/\b(?:sign in|log in|sign up|create account)\b|se connecter|s.inscrire|anmelden|registrieren/i,
   loginSelector:'a[href*="sign-in"],a[href*="/login"],button[data-testid="login-button"]',
   videoMode:/^(?:video|vidéo|make video|créer une vidéo|video erstellen)$/i,
   send:/^(?:submit|send|generate|create|make video|envoyer|générer|créer|senden|generieren|erstellen)$/i,
   quota:/rate limit|too many requests|limit reached|reached your (?:daily |video )?limit|upgrade to (?:supergrok|premium)|out of (?:free )?generations|limite atteinte|limite de (?:génération|vidéos)|Limit erreicht/i,
   refusal:/content moderated|moderated|violat\w* (?:our|the) (?:policy|policies|guidelines)|can.t generate (?:this|that)|unable to generate|contenu modéré|ne peut pas générer|Inhalt moderiert/i},
  arena:{label:'LMArena vidéo',hosts:['lmarena.ai','www.lmarena.ai'],home:'https://lmarena.ai/?chat-modality=video',
   login:/\b(?:sign in|log in)\b to (?:continue|generate|use video)|login required|se connecter pour|anmelden, um/i,
   loginSelector:'',
   videoMode:/^(?:video|vidéo)$/i,
   send:/^(?:send|submit|generate|run|envoyer|générer|senden|generieren)$/i,
   quota:/rate limit|too many requests|daily limit|limit reached|try again (?:later|in)|you.ve reached|limite atteinte|réessayez plus tard|Limit erreicht/i,
   refusal:/content (?:policy|filter|moderation)|flagged|violat\w* (?:our|the) (?:policy|policies|terms)|unsafe|cannot generate|contenu (?:refusé|signalé)|Inhaltsrichtlinie/i}
 },
 site(engine){const s=this.sites[engine];if(!s)throw Error('Moteur vidéo inconnu : '+engine);return s;},
 hosts(engine){return this.site(engine).hosts;},
 owns(engine,url){try{return this.site(engine).hosts.includes(new URL(url).hostname);}catch{return false;}},
 // Service worker: reuse this engine's tab inside the FruchtDrama window, or open its home page there.
 async tabFor(task,chrome){
  const engine=task.payload.engine,tabs=await chrome.tabs.query({});
  const own=tabs.find(t=>this.owns(engine,t.url||''));
  if(own){const tab=await globalThis.FruchtWorkspace.adopt(chrome,own);return chrome.tabs.update(tab.id,{active:true});}
  return globalThis.FruchtWorkspace.createTab(chrome,{url:this.site(engine).home,active:true});
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
 fileInput(doc){return [...doc.querySelectorAll('input[type="file"]')].find(i=>!i.disabled&&(!i.accept||/image|png|jpe?g|webp|\*/i.test(i.accept)))||null;},
 videoModeButton(doc,engine){
  const b=this.buttons(doc).find(x=>this.site(engine).videoMode.test(this.label(x)));
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
 newVideo(doc,old){
  return [...doc.querySelectorAll('video')].find(v=>{const src=v.currentSrc||v.src||v.querySelector?.('source')?.src;return src&&!old.has(src)&&v.readyState>=1&&!(v.duration<2);})||null;
 },
 async run(task,attachments,h){
  const engine=task.payload.engine,site=this.site(engine),doc=h.document;
  h.blocked();
  if(this.loggedOut(doc,engine))throw h.fail('login',site.label+' : connexion requise. Connectez-vous vous-même dans l’onglet de la fenêtre FruchtDrama, puis Reprendre.');
  const expected=String(task.payload.account?.email||'').toLowerCase();
  const shown=this.account(doc);
  if(expected&&shown&&shown!==expected)throw h.fail('login',site.label+' : le compte connecté ('+shown+') n’est pas le compte attendu ('+expected+'). Changez de compte dans l’onglet ; aucun envoi effectué.');
  const mode=this.videoModeButton(doc,engine);if(mode){mode.click();await h.sleep(800);}
  if(attachments?.length){
   const input=this.fileInput(doc);
   if(!input)throw h.fail('interface',site.label+' : champ d’image introuvable. Aucun envoi effectué.');
   const dt=new h.DataTransfer();
   for(const a of attachments){const bin=h.atob(a.data),bytes=Uint8Array.from(bin,c=>c.charCodeAt(0));dt.items.add(new h.File([bytes],a.name,{type:a.mime||'image/png'}));}
   input.files=dt.files;input.dispatchEvent(new h.Event('change',{bubbles:true}));await h.sleep(3000);
  }
  const editor=this.editor(doc);if(!editor)throw h.fail('interface',site.label+' : zone de texte introuvable. Aucun envoi effectué.');
  h.fill(editor,task.payload.prompt);await h.sleep(700);
  let send=null;for(let i=0;i<40&&!send;i++){h.blocked();send=this.sendButton(doc,engine);if(!send)await h.sleep(700);}
  if(!send)throw h.fail('interface',site.label+' : bouton de génération inactif ou introuvable. Aucun envoi effectué.');
  if(task.payload.dry_run===true)return {ok:false,dry_run:true,generation_submitted:false,error:'Essai à blanc réussi : '+site.label+' prêt (mode vidéo, image, prompt). Rien n’a été envoyé.'};
  const before=doc.body?.innerText||'',old=new Set([...doc.querySelectorAll('video')].map(v=>v.currentSrc||v.src).filter(Boolean));
  if(!(await h.intent()))throw h.fail('interface','Envoi suspendu : association de la tâche perdue. Aucun prompt envoyé.');
  send.click();h.submitted();await h.sleep(2500);
  const start=h.now();
  while(h.now()-start<600000){
   h.blocked();
   const video=this.newVideo(doc,old);if(video){await h.sleep(1500);return await h.videoPayload(video);}
   const kind=this.problem(this.fresh(doc.body?.innerText||'',before),engine);
   if(kind==='quota')throw h.fail('quota',site.label+' : limite du compte atteinte. Changez de compte ou attendez le renouvellement.',{retryAfter:h.retryAfter(doc.body?.innerText||'')});
   if(kind==='refusal')throw h.fail('refusal',site.label+' : génération refusée par la modération.');
   await h.sleep(2000);
  }
  throw h.fail('timeout',site.label+' : vidéo non détectée après 10 minutes. Vérifiez l’onglet avant toute nouvelle tentative.');
 }
};
