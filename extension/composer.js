// Small, testable DOM helpers. No content, credentials or cookies are collected.
globalThis.FruchtComposer = {
 challenge(doc){
  const text=doc.body?.innerText||'';
  // Cloudflare interstitial seen on chatgpt.com in a real check (02/11/2026).
  if(/^(?:just a moment|un instant|einen moment|nur einen moment)/i.test(String(doc.title||'').trim())||/checking (?:if the site connection is secure|your browser)|verifying you are human/i.test(text))return true;
  if(/verify you are human|vérifiez que vous êtes humain|bestätigen sie,? dass sie ein mensch sind|unusual activity|activité inhabituelle|ungewöhnliche aktivität/i.test(text))return true;
  return [...doc.querySelectorAll('iframe')].some(frame=>{
   const label=[frame.getAttribute('title'),frame.getAttribute('src')].filter(Boolean).join(' ');
   if(!/captcha|challenge/i.test(label)||!this.visible(frame))return false;
   const r=frame.getBoundingClientRect();
   return r.width>100&&r.height>70;
  });
 },
 // Signed-out ChatGPT/Claude still shows an editor (anonymous chat): never send there (real check 02/11/2026).
 loggedOut(doc){
  const labels=[...doc.querySelectorAll('button,a')].filter(b=>this.visible(b)).map(b=>[b.getAttribute('aria-label'),b.innerText].filter(Boolean).join(' ').replace(/\s+/g,' ').trim());
  // Labels are often doubled ("Log in Log in"): text + aria-label.
  return labels.some(l=>/^(log in|sign in|se connecter|connexion|anmelden|einloggen)(?: \1)?$/i.test(l))
   &&labels.some(l=>/^(?:sign up(?: for free)?|s.inscrire(?: gratuitement)?|registrieren|kostenlos registrieren)/i.test(l));
 },
 // Assistant replies, oldest first. Used to read only replies that appear after our prompt.
 assistants(doc){
  for(const selector of ['[data-message-author-role="assistant"]','[data-turn="assistant"]','[data-testid="assistant-message"]','.font-claude-response']){
   const found=[...doc.querySelectorAll(selector)];if(found.length)return found;
  }
  return [];
 },
 // Content-policy refusal in a NEW short reply (P2-03). Long replies are never read as refusals.
 refusal(doc,before){
  const fresh=this.assistants(doc).filter(e=>!before?.has(e));
  const last=fresh[fresh.length-1];if(!last)return null;
  const text=String(last.innerText||last.textContent||'').trim();
  if(!text||text.length>600)return null;
  const patterns=[
   /\bI(?:'|’)?m (?:not able|unable) to (?:help|create|generate|make|produce)|\bI (?:can(?:'|’)?t|cannot|am unable to) (?:help|create|generate|make|produce|assist)/i,
   /violat\w* (?:our|the|my) (?:content|usage|image) (?:polic|guideline)|against (?:our|the|my) (?:content )?(?:policies|guidelines)|content polic(?:y|ies)/i,
   /je ne peux pas (?:créer|générer|produire|réaliser|dessiner|t.aider|vous aider)|(?:enfrei\w*|contrevien\w*) (?:à )?(?:nos|les|mes) (?:règles|politiques|conditions)|politique de contenu/i,
   /ich kann (?:dir |Ihnen )?(?:dabei |das |dieses Bild |so ein Bild )?(?:nicht|kein\w*) (?:helfen|erstellen|generieren|zeichnen)|versto(?:ß|ss)\w* gegen (?:unsere|die|meine) (?:Inhalts)?richtlinien|Inhaltsrichtlinien/i
  ];
  return patterns.some(p=>p.test(text))?text:null;
 },
 // Renewal delay announced by the provider, in seconds (P2-04): "resets in 22 hours and 16 minutes".
 retryAfter(text,now=new Date()){
  const value=String(text||'');
  const units=[[/(\d+)\s*(?:hours?|heures?|h\b|Stunden?|Std\.?)/i,3600],[/(\d+)\s*(?:minutes?|min\b|Minuten?)/i,60],[/(\d+)\s*(?:days?|jours?|Tagen?|Tage)/i,86400]];
  // Every anchor is tried: an unrelated "Try again" earlier on the page must not hide the real delay.
  for(const m of value.matchAll(/(?:resets?|renouvel|réinitialis|zurückgesetzt|again|plus tard|erneut|more images|d.autres images|weitere Bilder)/gi)){
   const zone=value.slice(Math.max(0,m.index-60),m.index+160);let total=0;
   for(const [re,unit] of units){const n=zone.match(re);if(n)total+=Number(n[1])*unit;}
   if(total>0)return total;
  }
  // Or an hour (« try again after 3:47 PM », « réessayez après 15 h 47 », « um 15:47 Uhr »): seconds until then, local time.
  for(const m of value.matchAll(/(?:after|at|après|à|vers|um|ab|nach)\s+(\d{1,2})\s*(?::|h|\.)\s*(\d{2})\s*(a\.?m\.?|p\.?m\.?)?/gi)){
   let h=Number(m[1]);const min=Number(m[2]),half=(m[3]||'').toLowerCase()[0];
   if(half==='p'&&h<12)h+=12;if(half==='a'&&h===12)h=0;if(h>23||min>59)continue;
   const at=new Date(now.getTime());at.setHours(h,min,0,0);if(at<=now)at.setDate(at.getDate()+1);
   return Math.round((at-now)/1000);
  }
  return null;
 },
 visible(el) {
  if(!el || el.hidden || el.getAttribute('aria-hidden')==='true') return false;
  const r=el.getBoundingClientRect();
  return r.width>8 && r.height>8 && el.getClientRects().length>0;
 },
 editor(doc) {
  const groups=[
   '#prompt-textarea[contenteditable="true"],#prompt-textarea [contenteditable="true"]',
   '[contenteditable="true"].ProseMirror,[contenteditable="true"][role="textbox"]',
   'textarea:not([readonly]):not([disabled])'
  ];
  for(const selector of groups){const found=[...doc.querySelectorAll(selector)].find(e=>this.visible(e));if(found)return found;}
  return null;
 },
 button(doc,editor) {
  const form=editor?.closest('form');
  const available=scope=>[...scope.querySelectorAll('button')].filter(b=>this.visible(b)&&!b.disabled&&b.getAttribute('aria-disabled')!=='true');
  const scopes=form?[form,doc]:[doc];
  for(const scope of scopes){
   const buttons=available(scope);
   const known=buttons.find(b=>b.id==='composer-submit-button'||b.dataset.testid==='send-button');
   if(known)return known;
   const labelled=buttons.find(b=>{
    const label=[b.getAttribute('aria-label'),b.getAttribute('title'),b.innerText].filter(Boolean).join(' ').trim();
    return /(?:^|\s)(?:send|senden|absenden|envoyer|generate|generieren|générer|erstellen|submit|run)(?:\s|$)/i.test(label)
     && !/stop|arrêter|anhalten|abbrechen|buy|acheter|upgrade|abonn|subscribe|purchase/i.test(label);
   });
   if(labelled)return labelled;
   if(scope===form){const submit=buttons.find(b=>b.getAttribute('type')==='submit');if(submit)return submit;}
  }
  return null;
 },
 async openImport(doc,sleep){
  const find=()=>[...doc.querySelectorAll('input[type="file"]')].find(i=>!i.disabled&&(!i.accept||/image|png|jpe?g|webp|\*/i.test(i.accept)));
  let input=find();if(input)return input;
  const label=b=>[b.getAttribute('aria-label'),b.getAttribute('title'),b.innerText].filter(Boolean).join(' ').trim();
  const buttons=()=>[...doc.querySelectorAll('button,[role="button"],[role="menuitem"]')].filter(b=>this.visible(b)&&!b.disabled&&b.getAttribute('aria-disabled')!=='true');
  const tip=buttons().find(b=>/^(?:Tooltip schließen|Close tooltip|Fermer l.infobulle)$/i.test(label(b)));
  if(tip){tip.click();await sleep(200);}
  const add=buttons().find(b=>/^(?:Dateien und mehr hinzufügen|Add files and more|Add photos and files|Ajouter des fichiers et plus|Ajouter des photos et des fichiers|Ajouter des fichiers et bien plus)/i.test(label(b)));
  if(add){add.click();await sleep(500);input=find();if(input)return input;}
  const upload=buttons().find(b=>/^(?:Fotos und Dateien hinzufügen|Add photos and files|Upload from computer|Vom Computer hochladen|Ajouter des photos et des fichiers|Ajouter des fichiers|Téléverser depuis l.ordinateur|Importer depuis l.ordinateur)/i.test(label(b)));
  if(upload){
   // Suppress only the native picker while the site's menu mounts its own input.
   // The existing local references are assigned via DataTransfer by the runner.
   const preventPicker=e=>{if(e.target?.matches?.('input[type="file"]'))e.preventDefault();};
   doc.addEventListener('click',preventPicker,true);
   try{upload.click();await sleep(500);}finally{doc.removeEventListener('click',preventPicker,true);}
  }
  for(let i=0;i<15;i++){input=find();if(input)return input;await sleep(400);}
  throw Error('ChatGPT : champ de pièce jointe indisponible après ouverture du menu. Aucun prompt envoyé. Commandes : '+buttons().map(label).slice(-12).join(' / '));
 },
 diagnostic(doc,editor) {
  return {
   host:doc.location?.hostname,
   editor:editor?{tag:editor.tagName,id:editor.id,editable:editor.getAttribute('contenteditable'),length:(editor.value||editor.innerText||'').length}:null,
   buttons:[...doc.querySelectorAll('button')].filter(b=>this.visible(b)).slice(-24).map(b=>({label:(b.getAttribute('aria-label')||b.getAttribute('title')||b.innerText||'').slice(0,90),id:b.id,testid:b.dataset.testid,disabled:!!b.disabled||b.getAttribute('aria-disabled')==='true'}))
  };
 }
};
