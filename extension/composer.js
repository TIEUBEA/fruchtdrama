// Small, testable DOM helpers. No content, credentials or cookies are collected.
globalThis.FruchtComposer = {
 challenge(doc){
  const text=doc.body?.innerText||'';
  if(/verify you are human|vérifiez que vous êtes humain|bestätigen sie,? dass sie ein mensch sind|unusual activity|activité inhabituelle|ungewöhnliche aktivität/i.test(text))return true;
  return [...doc.querySelectorAll('iframe')].some(frame=>{
   const label=[frame.getAttribute('title'),frame.getAttribute('src')].filter(Boolean).join(' ');
   if(!/captcha|challenge/i.test(label)||!this.visible(frame))return false;
   const r=frame.getBoundingClientRect();
   return r.width>100&&r.height>70;
  });
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
