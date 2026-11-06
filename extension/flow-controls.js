globalThis.FruchtFlow={
 creditBlocked(doc){
  // Real labels seen: "Avertissement de crédits insuffisants" (03/11/2026), "Warnung: Nicht genügend Guthaben", "Insufficient credits".
  const pattern=/(?:nicht genügend guthaben|insufficient credits|not enough credits|crédits insuffisants)/i;
  return [...doc.querySelectorAll('button,[role="button"],[role="alert"]')].some(el=>this.visible(doc,el)&&[el.getAttribute('aria-label'),el.innerText].filter(Boolean).some(label=>label.trim().length<70&&pattern.test(label.trim())));
 },
 activate(doc,element){
  if(!element||element.disabled||element.getAttribute('aria-disabled')==='true')return;
  element.focus?.({preventScroll:true});
  const view=doc.defaultView;
  if(view?.MouseEvent){
   if(view.PointerEvent)element.dispatchEvent(new view.PointerEvent('pointerdown',{bubbles:true,pointerType:'mouse',isPrimary:true,button:0,buttons:1}));
   element.dispatchEvent(new view.MouseEvent('mousedown',{bubbles:true,button:0,buttons:1}));
   if(view.PointerEvent)element.dispatchEvent(new view.PointerEvent('pointerup',{bubbles:true,pointerType:'mouse',isPrimary:true,button:0,buttons:0}));
   element.dispatchEvent(new view.MouseEvent('mouseup',{bubbles:true,button:0,buttons:0}));
   element.dispatchEvent(new view.MouseEvent('click',{bubbles:true,cancelable:true,button:0,buttons:0,detail:1,view}));return;
  }
  element.click();
 },
 visible(doc,el){
  if(!el||el.hidden||el.getAttribute('aria-hidden')==='true'||!el.getClientRects().length)return false;
  const style=doc.defaultView?.getComputedStyle?.(el);
  return !style||(style.visibility!=='hidden'&&style.display!=='none');
 },
 sourceKey(img){
  const source=img?.currentSrc||img?.src||'';
  return /googleusercontent\.com\//i.test(source)?source.replace(/=(?:w|s)\d+.*$/,''):source;
 },
 referenceKey(doc,name){
  if(!name)return '';
  const keys=[...doc.querySelectorAll('[role="group"],[role="option"],button,[role="button"],[aria-label],[title]')].filter(el=>this.visible(doc,el)&&[el.getAttribute('aria-label'),el.getAttribute('title'),el.innerText].some(v=>v?.trim()===name)).map(el=>this.sourceKey(el.querySelector?.('img'))).filter(Boolean);
  return new Set(keys).size===1?keys[0]:'';
 },
 frameMatches(doc,key){
  const frame=this.startThumbnail(doc)?.querySelector('img');
  return !!key&&this.sourceKey(frame)===key;
 },
 closeAccountPanel(doc){
  const text=doc.body?.innerText||'';
  if(!/Google Flow-Guthabenpunkte|Google Flow credits/i.test(text)||!/Von allen Konten abmelden|Sign out of all accounts|Déconnexion de tous les comptes/i.test(text))return;
  this.control(doc,/^(?:Schließen|Close|Fermer)$/i)?.click();
 },
 cost(text){
  const patterns=[/Für\s+die\s+Generierung\s+werden\s+(\d+)\s+Guthabenpunkte\s+verwendet/gi,/(?:will use|utilisera|coûtera|costs?|verbraucht|benötigt|kostet)\s*:?\s*(\d+)\s*(?:AI\s*)?(?:credits?|crédits?|Guthabenpunkte)/gi];
  const values=patterns.flatMap(p=>[...String(text).matchAll(p)].map(m=>Number(m[1])));
  return values.length&&values.every(n=>n===values[0])?values[0]:null;
 },
 count(label){const m=String(label).replace(/(\d\s*s)(x[1-4]\b)/gi,'$1 $2').match(/\b([1-4])\s*-\s*mal\b|\bx\s*([1-4])\b/i);return m?Number(m[1]||m[2]):null;},
 settingsButton(doc){return [...doc.querySelectorAll('button,[role="button"]')].find(b=>this.visible(doc,b)&&(/^(?:Déclencheur des paramètres|Settings trigger|Einstellungen öffnen|Zu den Einstellungen|Paramètres de génération|Generation settings)$/i.test(b.getAttribute('aria-label')||'')||(/720p|1080p|Sek\./i.test(b.innerText||'')&&this.count(b.innerText)!==null)));},
 outputCount(doc,settings){
  const labelCount=this.count(settings?.innerText||'');if(labelCount!==null)return labelCount;
  const selected=[...doc.querySelectorAll('[role="radio"][aria-checked="true"],input[type="radio"]:checked')].filter(b=>this.visible(doc,b)).map(b=>this.count(b.innerText||b.getAttribute('aria-label')||b.value||'')).filter(n=>n!==null);
  return selected.length===1?selected[0]:null;
 },
 labelMatches(el,pattern){
  return [el.getAttribute('aria-label'),el.innerText].filter(Boolean).some(v=>[v,...v.split('\n')].some(line=>pattern.test(line.replace(/^(?:videocam|movie|image|crop_portrait|crop_landscape|crop_9_16|crop_16_9)\s+/i,'').trim())));
 },
 modelPattern(model){
  if(model==='gemini_omni_flash')return /\b(?:Gemini\s+)?Omni(?:\s+1\.1)?\s*[-–]?\s*Flash(?:\s+1\.1)?\b/i;
  if(model==='veo_3_1_lite')return /\bVeo\s*3\.1\s*[-–]?\s*Lite\b/i;
  if(model==='veo_3_1_fast')return /\bVeo\s*3\.1\s*[-–]?\s*Fast\b/i;
  if(model==='veo_3_1_quality')return /\bVeo\s*3\.1\s*[-–]?\s*(?:Quality|Qualität|Qualité)\b/i;
  throw Error('Modèle Flow non pris en charge ; aucun envoi effectué.');
 },
 modelControl(doc){
  const pattern=/\b(?:Veo|Gemini|Omni)\b/i;
  const find=selector=>[...doc.querySelectorAll(selector)].filter(b=>this.visible(doc,b)&&pattern.test((b.innerText||b.getAttribute('aria-label')||'').trim()));
  const boxes=find('[role="combobox"]');if(boxes.length===1)return boxes[0];if(boxes.length>1)return null;
  const buttons=find('button,[role="button"]');return buttons.length===1?buttons[0]:null;
 },
 currentSetting(doc,pattern,parse){
  const header=this.settingsButton(doc),value=parse(header?.innerText||'');if(value!==null)return value;
  const selected=[...doc.querySelectorAll('[aria-checked="true"],[aria-selected="true"]')].filter(b=>this.visible(doc,b)&&pattern.test(b.innerText||b.getAttribute('aria-label')||'')).map(b=>parse(b.innerText||b.getAttribute('aria-label')||'')).filter(x=>x!==null);
  return selected.length===1?selected[0]:null;
 },
 resolution(text){const values=[...String(text).matchAll(/\b(360|720|1080|2160)p\b/gi)].map(x=>x[1]+'p');return values.length&&new Set(values).size===1?values[0]:null;},
 seconds(text){const values=[...String(text).replace(/(\d\s*s)(x[1-4]\b)/gi,'$1 $2').matchAll(/\b(4|6|8|10)\s*(?:s(?:ec(?:onds?|ondes?)?)?\.?|Sek(?:unden)?\.?)\b/gi)].map(x=>Number(x[1]));return values.length&&new Set(values).size===1?values[0]:null;},
 async chooseSetting(doc,pause,desired,kind){
  const parse=kind==='resolution'?t=>this.resolution(t):t=>this.seconds(t);
  const pattern=kind==='resolution'?/^(?:360|720|1080|2160)p$/i:/^(?:4|6|8|10)\s*(?:s(?:ec(?:onds?|ondes?)?)?\.?|Sek(?:unden)?\.?)$/i;
  if(this.currentSetting(doc,pattern,parse)===desired)return;
  const options=()=>[...doc.querySelectorAll('[role="radio"],[role="option"],[role="menuitem"],button')].filter(b=>this.visible(doc,b)&&!b.disabled&&this.labelMatches(b,pattern)&&parse(b.innerText||b.getAttribute('aria-label')||'')===desired);
  let matches=options();
  if(matches.length!==1){
   const controls=[...doc.querySelectorAll('[role="combobox"]')].filter(b=>this.visible(doc,b)&&pattern.test((b.innerText||b.getAttribute('aria-label')||'').trim()));
   if(controls.length===1){controls[0].click();await pause(400);matches=options();}
  }
  if(matches.length!==1)throw Error('Flow : réglage '+kind+' non reconnu ; aucun envoi effectué.');
  this.activate(doc,matches[0]);await pause(400);
  if(this.currentSetting(doc,pattern,parse)!==desired)throw Error('Flow : réglage '+kind+' non confirmé ; aucun envoi effectué.');
 },
 aspectPattern(aspect){return aspect==='16:9'?/^16:9$/:/^9:16$/;},
 verifyModel(doc,model,resolution,seconds,aspect='9:16'){
  const portrait=[...doc.querySelectorAll('[role="radio"]')].filter(b=>this.visible(doc,b)&&this.labelMatches(b,this.aspectPattern(aspect))&&b.getAttribute('aria-checked')==='true');
  if(portrait.length!==1)throw Error('Flow : format '+(aspect==='16:9'?'horizontal':'vertical')+' non confirmé ; aucun envoi effectué.');
  const control=this.modelControl(doc);
  if(!control||!this.modelPattern(model).test(control.innerText||control.getAttribute('aria-label')||''))throw Error('Flow : modèle demandé non confirmé ; aucun envoi effectué.');
  if(this.currentSetting(doc,/^(?:360|720|1080|2160)p$/i,t=>this.resolution(t))!==resolution)throw Error('Flow : résolution demandée non confirmée ; aucun envoi effectué.');
  if(this.currentSetting(doc,/^(?:4|6|8|10)\s*(?:s(?:ec(?:onds?|ondes?)?)?\.?|Sek(?:unden)?\.?)$/i,t=>this.seconds(t))!==seconds)throw Error('Flow : durée demandée non confirmée ; aucun envoi effectué.');
 },
 async prepareFrames(doc,pause,cost,model,resolution,seconds,aspect='9:16'){
  if(/Einstellungen für KI-Agenten|AI agent settings|Paramètres (?:de l.agent|des agents IA)/i.test(doc.body?.innerText||'')){
   const back=this.control(doc,/^(?:Zurück|Back|Retour)$/i);if(back){back.click();await pause(400);}
  }
  const agent=this.control(doc,/^(?:Agentenmodus|Agent mode|Mode agent|Agent)$/i);
  if(agent&&(agent.getAttribute('aria-pressed')==='true'||agent.getAttribute('aria-checked')==='true')){this.activate(doc,agent);await pause(700);}
  await this.configure(doc,pause,cost,model,resolution,seconds,aspect);
  const frames=[...doc.querySelectorAll('[role="radio"]')].filter(b=>this.visible(doc,b)&&this.labelMatches(b,/^(?:Frames|Cadres|Images clés|Images)$/i));
  if(frames.length!==1)throw Error('Flow : mode Images / Frames absent ou ambigu. Aucun import ni génération effectué.');
  if(frames[0].getAttribute('aria-checked')!=='true'){this.activate(doc,frames[0]);await pause(500);}
  if(frames[0].getAttribute('aria-checked')!=='true')throw Error('Flow : mode Images / Frames non confirmé. Aucun import ni génération effectué.');
  const settings=this.settingsButton(doc);
  if(settings){settings.click();await pause(350);}
 },
 async configure(doc,pause,cost,model,resolution='720p',seconds=8,aspect='9:16'){
  const settings=this.settingsButton(doc);if(!settings)throw Error('Paramètres Flow indisponibles ; aucun envoi effectué.');
  // A panel left open by an earlier try in this tab doubled every option (06/11/2026: « Réglage Flow vidéo / 9:16 / x1
  // non reconnu » on every account): only the most recent settings panel counts.
  const radios=()=>{const all=[...doc.querySelectorAll('[role="radio"]')].filter(b=>this.visible(doc,b));const panes=[...new Set(all.map(b=>b.closest?.('.cdk-overlay-pane,[role="dialog"],[role="menu"]')).filter(Boolean))];return panes.length>1?all.filter(b=>b.closest('.cdk-overlay-pane,[role="dialog"],[role="menu"]')===panes[panes.length-1]):all;};
  if(!radios().some(b=>this.labelMatches(b,/^(?:16:9|9:16)$/))){settings.click();await pause(500);}
  for(const pattern of [/^(?:Vidéo|Video|Vídeo)$/i,this.aspectPattern(aspect),/^(?:x\s*1|1\s*-\s*mal)$/i]){
   const options=radios().filter(b=>this.labelMatches(b,pattern));
   if(options.length!==1)throw Error('Réglage Flow vidéo / 9:16 / x1 non reconnu ; aucun envoi effectué. Vu : '+options.length+' × '+pattern.source.slice(0,24)+' parmi '+radios().map(b=>(b.innerText||b.getAttribute('aria-label')||'').replace(/\s+/g,' ').trim().slice(0,14)).join(' | ').slice(0,300));
   if(options[0].getAttribute('aria-checked')!=='true'){this.activate(doc,options[0]);await pause(350);}
  }
  if(model){
   const pattern=this.modelPattern(model);let current=this.modelControl(doc);
   if(!current)throw Error('Flow : sélecteur de modèle ambigu ou absent ; aucun envoi effectué.');
   if(!pattern.test(current.innerText||current.getAttribute('aria-label')||'')){
    current.click();await pause(400);
    const options=[...doc.querySelectorAll('[role="option"],[role="menuitem"]')].filter(b=>this.visible(doc,b)&&!b.disabled&&pattern.test(b.innerText||b.getAttribute('aria-label')||'')&&!/360p|Lower Priority|priorité réduite|niedrigere Priorität/i.test(b.innerText||''));
    if(options.length!==1)throw Error('Flow : modèle demandé indisponible ou ambigu ; aucun envoi effectué.');
    this.activate(doc,options[0]);await pause(500);
   }
   for(const pattern of [/^(?:Vidéo|Video|Vídeo)$/i,this.aspectPattern(aspect),/^(?:x\s*1|1\s*-\s*mal)$/i]){
    const options=radios().filter(b=>this.labelMatches(b,pattern));
    if(options.length!==1)throw Error('Flow : réglages perdus après sélection du modèle ; aucun envoi effectué.');
    if(options[0].getAttribute('aria-checked')!=='true'){this.activate(doc,options[0]);await pause(350);}
   }
   await this.chooseSetting(doc,pause,resolution,'resolution');
   await this.chooseSetting(doc,pause,seconds,'seconds');
   this.verifyModel(doc,model,resolution,seconds,aspect);
  }else if(this.cost(doc.body?.innerText||'')!==cost&&cost===10){
   const selectors=[...doc.querySelectorAll('[role="combobox"],button,[role="button"]')].filter(b=>this.visible(doc,b)&&/^Veo\b/i.test((b.innerText||b.getAttribute('aria-label')||'').trim()));
   if(selectors.length===1){
    selectors[0].click();await pause(400);
    const lite=[...doc.querySelectorAll('[role="option"],[role="menuitem"]')].filter(b=>this.visible(doc,b)&&/\bVeo\s*3\.1\s*[-–]?\s*Lite\b/i.test(b.innerText||b.getAttribute('aria-label')||''));
    if(lite.length===1){lite[0].click();await pause(400);}
   }
  }
  // Leave the menu visible for the existing cost/count verification.
 },
 uploadConsent(doc){
  const dialogs=[...doc.querySelectorAll('[role="dialog"]')].filter(d=>this.visible(doc,d)&&/Rechte zur Nutzung dieses Bildes|Rights to use this image|Droits d.utilisation de cette image/i.test(d.innerText||d.textContent||''));
  if(dialogs.length!==1)return false;
  const buttons=[...dialogs[0].querySelectorAll('button')].filter(b=>this.visible(doc,b)&&!b.disabled&&/^(?:Ich stimme zu|I agree|J.accepte)$/i.test((b.innerText||b.getAttribute('aria-label')||'').trim()));
  if(buttons.length!==1)return false;
  buttons[0].click();return true;
 },
 fileInput(doc){return [...doc.querySelectorAll('input[type="file"]')].find(i=>!i.disabled&&(!i.accept||/image|png|jpe?g|webp|avif|\*/i.test(i.accept)))||null;},
 control(doc,pattern,includeDisabled=false){return [...doc.querySelectorAll('button,[role="button"],label')].find(b=>{
  if(!this.visible(doc,b)||(!includeDisabled&&(b.disabled||b.getAttribute('aria-disabled')==='true')))return false;
  const labels=[b.getAttribute('aria-label'),b.getAttribute('title'),b.innerText,b.textContent].filter(Boolean);
  return labels.some(label=>[label,...label.split('\n')].some(s=>pattern.test(s.replace(/^(?:upload_file|file_upload|drive_folder_upload|add_photo_alternate|upload)\s+/i,'').replace(/\s+/g,' ').trim())));
 });},
 startThumbnail(doc){
  const end=this.control(doc,/^(?:Ende|End|Fin)$/i);
  if(!end?.getBoundingClientRect)return null;
  const er=end.getBoundingClientRect();
  const candidates=[...doc.querySelectorAll('button,[role="button"]')].filter(b=>{
   if(b===end||b.disabled||!b.getClientRects().length||b.getAttribute('aria-disabled')==='true'||!b.querySelector('img'))return false;
   const r=b.getBoundingClientRect();
   return r.width>=24&&r.width<=120&&r.height>=24&&r.height<=120&&r.right<=er.left&&er.left-r.right<160&&Math.abs(r.top-er.top)<40;
  });
  return candidates.length===1?candidates[0]:null;
 },
 sendButton(doc,editor){
  if(!['flow.google.com','labs.google'].includes(doc.location?.hostname)||!editor)return null;
  const er=editor.getBoundingClientRect();
  const candidates=[...doc.querySelectorAll('button')].filter(b=>{
   if(!b.getClientRects().length||b.disabled||b.getAttribute('aria-disabled')==='true')return false;
   const labels=[b.innerText,b.getAttribute('aria-label'),b.getAttribute('title')].filter(Boolean);
   const icon=labels.some(s=>/^(?:arrow_forward|arrow_upward|send|Generierung starten|Start generation|Generate|Générer|Lancer la génération)$/i.test(s.trim()));
   if(!icon)return false;
   const r=b.getBoundingClientRect();
   return r.width>8&&r.height>8&&r.width<100&&r.height<100&&r.left>=er.left&&r.right<=er.right+100&&r.top>=er.top&&r.top<=er.bottom+100;
  });
  return candidates.length===1?candidates[0]:null;
 },
 // Flow writes why a generation failed on the page (owner 06/11/2026: « lis aussi le message d'erreur dans Flow »):
 // a NEW line with a failure wording, absent before the click, ends the wait at once with Flow's own words.
 generationError(doc,before){
  const lines=String(doc.body?.innerText||'').split('\n').map(x=>x.trim()).filter(x=>x&&x.length<400&&!(before&&before.has(x)));
  return lines.find(x=>/impossible de générer|n.a pas pu|non conforme|a échoué|échec de (?:la )?génération|activité inhabituelle|pourrait enfreindre|enfreint|règles|policy|violat|couldn.t generate|could not generate|generation failed|failed to generate|unusual activity|try again|réessaie|réessayez|something went wrong|une erreur s.est produite/i.test(x))||null;
 },
 openNewVideo(doc,oldImages,oldElements){
  const images=[...doc.images].filter(img=>img.complete&&/^(?:Miniaturansicht des erstellten Videos|Generated video thumbnail|Miniature de la vidéo générée)$/i.test(img.alt||'')&&!oldImages.has(img.currentSrc||img.src)&&!oldElements.has(img)&&img.getClientRects().length);
  if(images.length!==1)return false;
  images[0].click();return true;
 },
 previewMatches(doc,name){
  return [...(doc.images||[])].some(img=>{
   if(!img.complete||img.naturalWidth<1||!img.getClientRects().length)return false;
   const labels=[img.alt,img.getAttribute('aria-label'),img.getAttribute('title')].filter(Boolean);
   return labels.some(label=>/^(?:Vorschau für|Preview (?:for|of)|Aperçu (?:de|pour))/i.test(label)&&label.includes(name));
  });
 },
 async confirmImport(doc,pause,onProgress=()=>{},expectedName,selection={}){
  const pattern=/^(?:Zum Prompt hinzufügen|Add to prompt|Ajouter au prompt|Ajouter à l’invite|Ajouter à l'invite)$/i;
  let selected=!expectedName||selection.existingReference===true;
  let selectedSource=selection.referenceSource||'';
  // 0.1.93 (owner: « pas 10 min d'attente ») : 90 s (180 passes) without any visible change at the import is a failure
  // before any generation was sent: the clip goes at once to the next engine. The 5 min bound stays for slow uploads.
  let lastSeen=null,lastChange=0;
  for(let n=0;n<600;n++){
   const seen=this.importSignature(doc,expectedName,selected);
   if(seen!==lastSeen){lastSeen=seen;lastChange=n;}
   else if(n-lastChange>=180)throw Error('Flow : image toujours en traitement, rien ne progresse depuis 90 s. Aucun envoi de génération effectué.');
   if(this.uploadConsent(doc))await pause(400);
   if(expectedName&&this.frameMatches(doc,this.referenceKey(doc,expectedName)))return;
   if(n%20===0)onProgress('Import Flow : traitement de l’image en cours ('+Math.round(n/2)+' s, limite 5 min). Ne relancez pas la production.');
   if(n===0&&expectedName)onProgress('Diagnostic import Flow : '+JSON.stringify({reference:!!this.referenceKey(doc,expectedName),frame:!!this.startThumbnail(doc),same:this.frameMatches(doc,this.referenceKey(doc,expectedName)),named:[...doc.querySelectorAll('[aria-label],[title]')].filter(el=>[el.getAttribute('aria-label'),el.getAttribute('title')].some(v=>v?.includes(expectedName))).map(el=>({tag:el.tagName,label:el.getAttribute('aria-label')||el.getAttribute('title'),image:!!el.querySelector?.('img')})).slice(0,4)}));

   if(!selected){
    const asset=this.existingReference(doc,expectedName);
    if(!asset){await pause(500);continue;}
    selectedSource=this.sourceKey(asset.querySelector?.('img'));asset.click();selected=true;await pause(250);
   }
   if(expectedName&&!this.control(doc,pattern,true)&&this.frameMatches(doc,selectedSource))return;
   // Flow shows the frame from a signed CDN address, never the picker's: the addresses cannot match (06/11/2026,
   // clips stuck 5 min with the board already placed). An empty Début that now holds an image, picker closed and no
   // « Ajouter au prompt » left, is the board just chosen.
   if(selection.existingReference&&selection.startWasEmpty&&!this.control(doc,pattern,true)&&this.startThumbnail(doc)?.querySelector('img')&&this.startThumbnail(doc).getAttribute('aria-busy')!=='true'&&![...doc.querySelectorAll('[role="option"]')].some(el=>this.visible(doc,el)))return;
   if(expectedName&&!this.previewMatches(doc,expectedName)){await pause(500);continue;}
   const button=this.control(doc,pattern);
   if(button){
    button.click();
    for(let k=0;k<30;k++){
     await pause(500);
     if(!this.control(doc,pattern,true))return;
    }
    throw Error('Flow : confirmation de l’image non terminée après « Zum Prompt hinzufügen ». Aucun envoi de génération effectué.');
   }
   await pause(500);
  }
  const pending=this.control(doc,pattern,true);
  throw Error(pending?'Flow : image toujours en traitement après 5 minutes ; bouton « Zum Prompt hinzufügen » désactivé. Aucun envoi de génération effectué.':'Flow : bouton « Zum Prompt hinzufügen » absent après 5 minutes. Aucun envoi de génération effectué.');
 },
 // What the import shows now (picker, reference, Début, confirmation, % uploaded): any change is progress.
 importSignature(doc,name,selected){
  const pattern=/^(?:Zum Prompt hinzufügen|Add to prompt|Ajouter au prompt|Ajouter à l’invite|Ajouter à l'invite)$/i;
  const percent=(String(doc.body?.innerText||'').match(/\d{1,3}\s?%/g)||[]).join(',');
  let reference=false,frame=false,preview=false,confirm=null;
  try{reference=!!(name&&this.referenceKey(doc,name));}catch{}
  try{frame=!!this.startThumbnail(doc)?.querySelector?.('img');}catch{}
  try{preview=!!(name&&this.previewMatches(doc,name));}catch{}
  try{const c=this.control(doc,pattern,true);confirm=c?(c.disabled||c.getAttribute?.('aria-disabled')==='true'?'off':'on'):null;}catch{}
  return JSON.stringify([selected,reference,frame,preview,confirm,percent]);
 },
 existingReference(doc,name){
  if(!name)return null;
  const candidates=[...doc.querySelectorAll('[role="option"]')].filter(el=>{
   if(!this.visible(doc,el)||el.getAttribute('aria-disabled')==='true'||el.getAttribute('aria-busy')==='true')return false;
   const labels=[el.getAttribute('aria-label'),el.getAttribute('title'),el.innerText].filter(Boolean).map(x=>x.trim());
   if(labels.some(x=>/Wird hochgeladen|Uploading|Téléversement/i.test(x)))return false;
   return labels.some(label=>[label,...label.split('\n')].some(line=>line.trim()===name));
  });
  return candidates.length===1?candidates[0]:null;
 },
 async openImport(doc,pause,name){
  if(name){
   if(this.frameMatches(doc,this.referenceKey(doc,name)))return {alreadyAttached:true};
   const escaped=name.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
   const gallery=this.control(doc,new RegExp('^'+escaped+'$'));
   const key=this.sourceKey(gallery?.querySelector?.('img'));
   if(this.frameMatches(doc,key))return {alreadyAttached:true};
  }
  let startWasEmpty=null;
  const selectExisting=()=>{const asset=this.existingReference(doc,name);if(!asset)return null;const referenceSource=this.sourceKey(asset.querySelector?.('img'));asset.click();return {existingReference:true,referenceSource,startWasEmpty};};
  let reuse=selectExisting();if(reuse)return reuse;
  let input=this.fileInput(doc);if(input&&!name)return input;
  const uploadPattern=/^(?:\+\s*)?(?:Hochladen|Datei(?:en)? hochladen|Bild(?:er)? hochladen|Medien hochladen|Medien hoch(?:\.{3}|…)|Upload|Upload image|Upload file|Importer|Importer une image|Importer l[’']élément multimédia|Téléverser)$/i;
  // An already open picker must not be closed again by clicking Start underneath it.
  let upload=this.control(doc,uploadPattern);
  const start=upload?null:(this.control(doc,/^(?:\+\s*)?(?:Start|Startframe(?: hinzufügen)?|Start frame|Add start frame|Début|Ajouter une image de début)$/i)||this.startThumbnail(doc));
  const hadThumbnail=!!start?.querySelector?.('img');
  startWasEmpty=!!start&&!hadThumbnail;
  if(start)this.activate(doc,start);
  let uploadClicked=false,emptyStartClicked=false;
  for(let n=0;n<160;n++){
   if(this.uploadConsent(doc)){await pause(400);}
   reuse=selectExisting();if(reuse)return reuse;
   input=this.fileInput(doc);if(input)return input;
   upload=this.control(doc,uploadPattern);
   if(upload&&!uploadClicked){upload.click();uploadClicked=true;}
   if(!upload&&!emptyStartClicked&&(hadThumbnail||n>=16)){
    const options=[...doc.querySelectorAll('[role="option"]')].some(el=>this.visible(doc,el));
    const picker=/Bild für Frame auswählen|Select image for frame|Choisir une image pour|Sélectionner une image/i.test(doc.body?.innerText||'');
    const empty=this.control(doc,/^(?:Start|Start frame|Début)$/i);
    if(!options&&!picker&&empty&&!empty.querySelector?.('img')){this.activate(doc,empty);emptyStartClicked=true;}
   }
   await pause(250);
  }
  const buttons=[...doc.querySelectorAll('button,[role="button"]')].filter(b=>b.getClientRects().length).map(b=>(b.getAttribute('aria-label')||b.innerText||'').trim()).filter(Boolean).slice(-18);
  throw Error('Flow : '+(start?'clic sur Start effectué':'bouton Start non reconnu')+', mais ni fichier existant sélectionnable ni champ d’import détecté après 40 secondes. '+(buttons.length?'Boutons visibles : '+buttons.join(' / '):'Une capture du sélecteur permettra d’identifier le blocage.'));
 }
};

// A provider may show its image-rights notice only after the input changes.
// Reattaching the adapter to an actively followed Flow import handles that notice.
if(typeof document!=='undefined'&&['flow.google.com','labs.google'].includes(document.location?.hostname)&&globalThis.fruchtRunState?.state==='running')FruchtFlow.uploadConsent(document);
