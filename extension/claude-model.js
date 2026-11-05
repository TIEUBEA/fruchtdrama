// Claude model and effort chosen in the studio, selected in claude.ai before the prompt is sent.
// Tolerant by design: menus are found by their visible text, never by one fragile CSS class.
// When something cannot be found, nothing is blocked: the tab keeps its current model and a note is returned.
globalThis.FruchtClaudeModel = {
 MODELS:{
  'opus-5.5':{family:/\bopus\b/i,version:/5[.,]5/,label:'Opus 5.5'},
  'fable-5.1':{family:/\bfable\b/i,version:/5[.,]1/,label:'Fable 5.1'},
  'sonnet-5.5':{family:/\bsonnet\b/i,version:/5[.,]5/,label:'Sonnet 5.5'}
 },
 // "Extra high" must not be read as "high": high and medium only match at the start of the label.
 EFFORTS:{
  high:{match:/^(?:high|élevé|elevé|eleve|hoch)\b/i,label:'Élevé'},
  extra:{match:/\b(?:extra|max|maximum|maximal)\b/i,label:'Extra'},
  medium:{match:/^(?:medium|moyen|mittel)\b/i,label:'Moyen'}
 },
 ANY_MODEL:/\b(?:opus|sonnet|fable|haiku)\b/i,
 FORBIDDEN:/upgrade|mettre à niveau|passer à|abonn|subscribe|purchase|acheter|buy|get (?:pro|max)|essai gratuit|free trial/i,
 label(el){
  return [el.getAttribute?.('aria-label'),el.innerText||el.textContent].filter(Boolean).join(' ').replace(/\s+/g,' ').trim();
 },
 firstLine(el){return String(el.innerText||el.textContent||el.getAttribute?.('aria-label')||'').split('\n').map(x=>x.trim()).filter(Boolean)[0]||'';},
 visible(el){
  if(!el||el.hidden||el.getAttribute?.('aria-hidden')==='true')return false;
  const r=el.getBoundingClientRect?.();
  return !!r&&r.width>4&&r.height>4&&el.getClientRects().length>0;
 },
 enabled(el){return !el.disabled&&el.getAttribute?.('aria-disabled')!=='true'&&el.getAttribute?.('data-disabled')!==''&&el.getAttribute?.('data-disabled')!=='true';},
 controls(doc){
  return [...doc.querySelectorAll('button,[role="button"],[role="menuitem"],[role="menuitemradio"],[role="option"]')].filter(el=>this.visible(el));
 },
 isItem(el){return ['menuitem','menuitemradio','option'].includes(el.getAttribute?.('role'));},
 checked(el){return el.getAttribute?.('aria-checked')==='true'||el.getAttribute?.('aria-selected')==='true'||el.getAttribute?.('data-state')==='checked';},
 // The model button of the composer: known test id first, then any button naming a Claude model.
 trigger(doc){
  const all=this.controls(doc).filter(el=>!this.isItem(el));
  return all.find(el=>el.getAttribute?.('data-testid')==='model-selector-dropdown')
   ||all.find(el=>el.getAttribute?.('aria-haspopup')&&this.ANY_MODEL.test(this.label(el)))
   ||all.find(el=>this.ANY_MODEL.test(this.label(el))&&this.label(el).length<60)
   ||null;
 },
 items(doc){return this.controls(doc).filter(el=>this.isItem(el)&&this.enabled(el)&&!this.FORBIDDEN.test(this.label(el)));},
 // Best menu entry for a model: family and version, else the family alone (a newer version of the same model).
 modelItem(doc,want){
  const items=this.items(doc).filter(el=>want.family.test(this.firstLine(el)||this.label(el)));
  return items.find(el=>want.version.test(this.firstLine(el)))||items[0]||null;
 },
 effortItem(doc,want){return this.items(doc).find(el=>want.match.test(this.firstLine(el)))||null;},
 async waitFor(find,sleep,tries=8){for(let i=0;i<tries;i++){const v=find();if(v)return v;await sleep(250);}return null;},
 close(doc){
  try{const E=doc.defaultView?.KeyboardEvent||globalThis.KeyboardEvent;const target=doc.activeElement||doc.body;if(E&&target?.dispatchEvent)target.dispatchEvent(new E('keydown',{key:'Escape',code:'Escape',bubbles:true}));}catch{}
 },
 async select(doc,sleep,model,effort){
  const result={model:'missing',effort:'missing',notes:[]};
  const wantModel=this.MODELS[model],wantEffort=this.EFFORTS[effort];
  try{
   let trigger=this.trigger(doc);
   if(wantModel&&trigger&&wantModel.family.test(this.label(trigger))&&wantModel.version.test(this.label(trigger)))result.model='already';
   if(wantModel&&trigger&&result.model!=='already'){
    trigger.click();await sleep(400);
    let item=await this.waitFor(()=>this.modelItem(doc,wantModel),sleep);
    if(!item){
     // Some accounts list the other models under « More models ».
     const more=this.items(doc).find(el=>/more models|plus de modèles|autres modèles|weitere modelle/i.test(this.label(el)));
     if(more){more.click();await sleep(400);item=await this.waitFor(()=>this.modelItem(doc,wantModel),sleep);}
    }
    if(item){item.click();await sleep(500);result.model='selected';}
    else this.close(doc);
   }
   if(wantEffort){
    // Effort: in the open menu, in the model menu, or behind an « Effort » entry.
    let item=this.effortItem(doc,wantEffort);
    if(!item){trigger=this.trigger(doc);if(trigger){trigger.click();await sleep(400);item=await this.waitFor(()=>this.effortItem(doc,wantEffort),sleep,4);}}
    if(!item){
     // Only an entry titled « Effort » is opened: a thinking switch is never toggled by mistake.
     const entry=this.controls(doc).find(el=>this.enabled(el)&&/^(?:effort|niveau d.effort|denkaufwand)\b/i.test(this.firstLine(el))&&!/switch|checkbox/.test(el.getAttribute?.('role')||''));
     if(entry){entry.click();await sleep(400);item=await this.waitFor(()=>this.effortItem(doc,wantEffort),sleep,4);}
    }
    if(item){if(this.checked(item))result.effort='already';else{item.click();await sleep(400);result.effort='selected';}}
    this.close(doc);
   }
  }catch(e){result.error=String(e?.message||e).slice(0,160);this.close(doc);}
  if(wantModel&&result.model==='missing')result.notes.push('Modèle Claude non sélectionnable automatiquement : modèle de l’onglet conservé (choix demandé : '+wantModel.label+').');
  if(wantEffort&&result.effort==='missing')result.notes.push('Effort Claude non sélectionnable automatiquement : réglage de l’onglet conservé (choix demandé : '+wantEffort.label+').');
  return result;
 }
};
