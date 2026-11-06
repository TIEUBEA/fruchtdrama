// 0.1.97 (owner 06/11/2026): « dès qu'une étape prend plus de temps qu'elle est censée prendre, reporte directement
// l'erreur au niveau du studio, bien en évidence » ; en pause ou arrêté, jamais l'impression que ça tourne ;
// « N clips en échec » avec « Refaire » par clip.
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm');
const src=fs.readFileSync(path.join(__dirname,'../web/atelier.js'),'utf8');
const cut=(a,b)=>{const i=src.indexOf(a),k=src.indexOf(b,i);assert.ok(i>=0&&k>i,a);return src.slice(i,k);};
const code=cut('const stallTitle','// "En cours" in the menu')+cut('function stopBanner','function alertsNotice(j)');
const ctx=vm.createContext({esc:s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]),
 statusLabels:{waiting_credit:'Crédits insuffisants',waiting_quota:'Limite atteinte, reprise automatique'},isActive:()=>false,nextAction:()=>'suite'});
vm.runInContext(code+';globalThis.t={stopBanner,failedClipsNotice,liveLine};',ctx);
const {stopBanner,failedClipsNotice,liveLine}=ctx.t;

// Bloqué: the step, how long, the reason, « Relancer cette étape ».
const stalled={status:'running',events:[{text:'Tâche préparée : script'}],stall:{step:'le scénario',minutes:12,reason:'Aucune nouvelle de ChatGPT depuis 12 min.',hint:'Regarde l’onglet.',retry:true,paid:false}};
const b=stopBanner(stalled);
assert.match(b,/stop-banner blocked/);assert.match(b,/Bloqué : le scénario depuis 12 min/);assert.match(b,/Aucune nouvelle de ChatGPT/);
assert.match(b,/data-retry-step="0">Relancer cette étape/);
assert.match(liveLine(stalled),/^Bloqué : le scénario depuis 12 min — Aucune nouvelle/,'Studio card and side menu say it too');
assert.match(stopBanner({...stalled,stall:{...stalled.stall,paid:true}}),/data-retry-step="1"/,'a clip maybe paid asks for a confirmation');

// En pause / Arrêté: big banner, reason, Reprendre; never « Fabrication ».
const paused=stopBanner({status:'paused',events:[{text:'Pause demandée.'}]});
assert.match(paused,/stop-banner paused/);assert.match(paused,/En pause — rien ne tourne/);assert.match(paused,/Pause demandée\./);assert.match(paused,/data-command="resume">Reprendre/);
assert.equal(liveLine({status:'paused',events:[]}),'En pause — rien ne tourne');
const stopped={status:'attention',events:[{text:'x'}],alerts:[{level:'action',text:'Clip 2 : Flow (refusé) puis Grok (contenu modéré) — clip à refaire. Les autres clips continuent.'},{level:'action',command:'allow_grok',text:'Utiliser Grok'}]};
const a=stopBanner(stopped);
assert.match(a,/Arrêté — action requise/);assert.match(a,/Clip 2 : Flow \(refusé\) puis Grok/);assert.doesNotMatch(a,/Utiliser Grok/,'the old « Utiliser Grok » is gone');
assert.match(liveLine(stopped),/^Arrêté — action requise : Clip 2/);
assert.match(stopBanner({status:'waiting_credit',events:[{text:'Plus aucun compte Flow avec 12 crédits.'}]}),/En attente — rien ne tourne : Crédits insuffisants/);
assert.equal(stopBanner({status:'running',events:[]}),'','nothing while it really runs');
assert.equal(stopBanner({status:'done',events:[]}),'');

// N clips en échec, each with Refaire.
const f=failedClipsNotice({failed_clips:[{index:0,text:'Clip 1 : Flow (refusé) puis Grok (délai) — clip à refaire. Les autres clips continuent.'},{index:3,text:'Clip 4 : Flow (x) puis Grok (y) — clip à refaire.'}]});
assert.match(f,/2 clips en échec/);assert.match(f,/data-redo="clip:0"/);assert.match(f,/data-redo="clip:3"/);assert.match(f,/Le montage attend tous les clips/);
assert.equal(failedClipsNotice({}),'');
console.log('Bandeaux 0.1.97 : Bloqué (étape, durée, raison, Relancer), En pause / Arrêté (raison, Reprendre), clips en échec avec Refaire vérifiés.');
