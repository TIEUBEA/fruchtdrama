// « Mes comptes » simple (owner 06/11/2026: « trop d'informations, je suis perdu ; je ne sais pas comment ajouter un compte
// ni enlever ceux déjà ajoutés »). Like the Atelier, simpler: one block per service, one line per account (Prêt / À régler +
// raison / Bloqué jusqu'à HH:MM, crédits for Flow), « + Ajouter un compte », « Supprimer », « Tout supprimer ».
// Everything technical is in « Avancé », closed. No password is ever asked or kept.
const ACC_SERVICES=[['chatgpt','ChatGPT',true,'personnages, planches et miniature'],['flow','Google Flow',true,'les clips 2 à la fin (Omni 1.2 Flash, 10 s), et le clip 1 si Grok n’est pas disponible'],['grok','Grok',false,'le clip 1 seulement (10 s)'],['vidogrid','Vidogrid',false,'1 ou 2 essais quand Flow refuse une scène (Grok Lite, 10 s)'],['claude','Claude',false,'l’histoire, si tu préfères Claude']];
// 0.1.93: each clip tries the engines in this order, one try each (owner 06/11/2026: « un essai par cas »).
const ENGINE_ORDER_DEFAULT=['flow','grok','vidogrid'],ENGINE_NAMES={flow:'Flow',grok:'Grok',vidogrid:'Vidogrid'};
function engineOrder(){const o=(state.settings?.engine_chain||ENGINE_ORDER_DEFAULT).filter(e=>ENGINE_NAMES[e]);return o.length?o:ENGINE_ORDER_DEFAULT;}
function engineOrderBlock(){if(!state.settings?.clip_routing||state.settings.clip_routing==='v09_grok_first')return `<section class="panel acc-service"><h2>Moteur V09 pour chaque clip</h2><p>Clip 1 : Grok (10 s). Si Grok n’est pas disponible (pas de compte prêt, limite, connexion, refus), le clip 1 part sur Flow. Clips 2 à la fin : Flow seulement, Omni 1.2 Flash, 720p, 9:16, 10 s ; un deuxième essai adapté après un refus confirmé, puis Vidogrid une ou deux fois si Flow refuse encore la scène.</p><p class="hint">Arena n’est plus utilisé. Grok ne fait jamais les clips 2 et suivants.</p></section>`;if(state.settings?.clip_routing==='flow_grok_per_clip')return `<section class="panel acc-service"><h2>Moteurs utilisés pour chaque clip</h2><p>Flow → adaptation de la scène et deuxième essai Flow après un refus confirmé → Grok si Flow refuse encore. Chaque nouveau clip repart sur Flow.</p><p class="hint">Une panne, un manque de crédits ou un envoi incertain restent à vérifier. Arena et Vidogrid ne sont pas utilisés dans ce mode.</p></section>`;const o=engineOrder();return `<section class="panel acc-service"><h2>Ordre des moteurs pour chaque clip</h2><p class="hint">Un essai par moteur et par clip ; un moteur sans compte prêt est sauté. Si tous échouent, le prompt est adouci et Flow réessaie une fois, puis le clip t’attend.</p><div class="chips">${o.map((e,i)=>`<span class="qchip">${i+1}. ${ENGINE_NAMES[e]}${i?` <button class="link-btn" data-engine-up="${e}" title="Passer avant le moteur précédent">monter</button>`:''}</span>`).join(' › ')}</div></section>`;}
const accHH=t=>new Date(t*1000).toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'});
const accMask=e=>{e=String(e||'');const i=e.indexOf('@');return i<0?e:e.slice(0,2)+'•••'+(i>3?e[i-1]:'')+e.slice(i);};
const accReady=()=>state.readiness||{sites:{},pending:[]};
let accountsBlock=null;
let accountPickerOpen=false;
function accountOpenButton(service,label,classes='secondary'){
 const action=service==='flow'?'data-add-google="1"':`data-site-open="${service}"`;
 return `<button type="button" class="${classes}" ${action}>${esc(label)}</button>`;
}
function showAccountsBlock(list){accountsBlock={list:list||[],at:Date.now()};if(typeof render==='function')render();}
// One line per account of a service: {key, email, label, tone, text, reason, fix, del}
function accountRows(svc){const R=accReady(),pending=new Set(R.pending||[]),now=Date.now()/1000;
 if(svc==='flow'){const cost=Number(state.settings?.flow_cost||12);
  // 0.1.95 (owner 06/11/2026): most credits first, empty then blocked at the bottom; « Compte N » is the account's own
  // number (server account_usage.number_flow), so the journal's « compte 2 → compte 3 » still names the same accounts.
  return (state.profiles||[]).filter(p=>p.flow_email||p.label).map(p=>{const r=p.readiness||{},key='flow:'+p.id,known=!!(p.checked||p.balance>0||p.refill_at||p.credit_source==='read');let tone,text,reason='',rank=0;
   const client=state.clients?.[p.flow_client],offline=!!p.flow_client&&!!state.clients&&(!client||client.disabled||Date.now()-Date.parse(client.seen)>180000);
   if(offline){tone='warn';text='Profil Chrome hors ligne';reason='Ouvre son profil Chrome et clique sur l’icône FruchtDrama. Ce compte retrouvera son accès ici.';rank=2;}
   else if(pending.has(key)){tone='idle';text='Vérification…';}
   else if(r.state==='fix'&&r.reason?.includes('Autre compte Google')){tone='bad';text='Compte à retrouver';reason='Google a changé le compte ouvert à cet emplacement.';rank=2;}
   else if(r.state==='fix'){tone='bad';text='À régler';reason=r.reason||'';rank=2;}
   else if(p.blocked==='unavailable'||r.state==='no_access'){tone='bad';text='Pas d’accès à Flow';rank=2;}
   else if(!p.flow_url||p.auto_enabled===false){tone='idle';text='À détecter';reason='Ouvre le compte Google dans Chrome, puis détecte les comptes Flow.';rank=2;}
   else if(!known){tone='idle';text='Solde à vérifier';rank=1;}
   else if((p.balance||0)<cost){tone='warn';text='Vide';reason=p.refill_at?'Recharge à '+accHH(p.refill_at):'Heure de recharge pas encore connue';rank=1;}
   else if(r.state==='ready'){tone='ok';text='Prêt';}
   else{tone='idle';text=p.flow_url?'Non vérifié':'À détecter';}
   return {key,ukeys:[key],number:p.number,email:p.flow_email||p.label,tone,text,reason,rank,credits:known?(p.balance||0):null,scan:!offline&&!pending.has(key)&&(!p.flow_url||p.auto_enabled===false||r.reason?.includes('Autre compte Google'))?(p.flow_client?p.id:'all'):null,verify:!offline&&!pending.has(key)&&!!p.flow_url&&r.state!=='fix'&&p.auto_enabled!==false,fix:!offline&&r.state==='fix'&&!!p.flow_url,del:{profile:p.id}};})
   .sort((a,b)=>a.rank-b.rank||b.credits-a.credits||(a.number||99)-(b.number||99));}
 const session=(R.sites||{})[svc],seen=(state.sites||{})[svc]||{},live=session?.email||seen.email||null,key='site:'+svc;
 let emails=(state.identities||[]).filter(i=>(i.services||[]).includes(svc)).map(i=>i.email);
 const engine=svc==='grok'?(state.engine_accounts||[]).filter(a=>a.engine===svc):[];
 for(const a of engine)if(!emails.includes(a.email))emails.push(a.email);
 if(live&&!emails.includes(live))emails.push(live);
 const rows=emails.map(email=>({email}));
 // The open session first; when its address is unknown, one line for it and the saved addresses wait in reserve
 // (06/11/2026: 4 ChatGPT lines all « Connecté » while one Chrome holds one ChatGPT session).
 if((session||seen.connected)&&(!live||!rows.length))rows.unshift({email:null});
 const wall=(state.quota_status||[]).filter(q=>q.blocked&&q.service.startsWith(svc)).sort((a,b)=>a.retry_at-b.retry_at)[0];
 return rows.map(row=>{const acc=engine.find(a=>a.email===row.email),mine=!row.email||row.email===live;let tone,text,reason='';
  if(acc?.wall&&acc.wall.until>now){tone='warn';text='Bloqué (quota) jusqu’à '+accHH(acc.wall.until);}
  else if(!mine){tone='idle';text=live||seen.connected?'En réserve · changement manuel':'Compte enregistré · à connecter';}
  else if(pending.has(key)){tone='idle';text='Vérification…';}
  else if(wall){tone='warn';text='Bloqué (quota) jusqu’à '+accHH(wall.retry_at);}
  else if(['fix','no_access'].includes(session?.state)){tone='bad';text='À régler';reason=session.reason||'';}
  else if(session?.state==='ready'||(!session&&seen.connected)){tone='ok';text=session?'Prêt':'Connecté · non vérifié';}
  else{tone='bad';text='Pas connecté';}
  const ukeys=[...(acc?['engine:'+svc+':'+acc.email]:[]),...(mine?['site:'+svc]:[])];
  return {key,ukeys,email:row.email,tone,text,reason,fix:mine&&session?.state==='fix',del:row.email&&(acc||(state.identities||[]).some(i=>i.email===row.email&&(i.services||[]).includes(svc)))?{service:svc,email:row.email}:null};});}
// « Utilisé maintenant » (0.1.95, owner 06/11/2026: « je ne sais pas quel compte est utilisé ») from STATE.usage:
// in_use = tasks taken by the FruchtDrama window right now, last_used = when each account last took one.
const accUsage=()=>state.usage||{in_use:[],last_used:{}};
const accAgo=t=>{const m=Math.max(0,Math.floor((Date.now()/1000-t)/60));if(m<1)return 'à l’instant';if(m<60)return 'il y a '+m+' min';
 if(m<1440)return 'il y a '+Math.floor(m/60)+' h'+(m%60?' '+String(m%60).padStart(2,'0'):'');return 'le '+new Date(t*1000).toLocaleDateString('fr-FR')+' à '+accHH(t);};
const usageOf=svc=>accUsage().in_use.filter(u=>u.service===svc);
const rowUses=r=>accUsage().in_use.filter(u=>(r.ukeys||[]).includes(u.key));
const rowLast=r=>Math.max(0,...(r.ukeys||[]).map(k=>accUsage().last_used?.[k]||0));
// « Compte 2 (ar•••5@example.com, 38 crédits) » for Flow, the address (or « compte de cette fenêtre ») for the others.
function usageWho(u,svc){if(svc==='flow')return `<b>Compte ${u.number||'?'}</b> (${esc(accMask(u.email||''))}, ${u.credits} crédit${Math.abs(u.credits)>1?'s':''})`;
 const live=u.email||(accReady().sites||{})[svc]?.email||(state.sites||{})[svc]?.email;return live?`<b>${esc(accMask(live))}</b>`:'<b>le compte de cette fenêtre</b>';}
function usageBanner(svc,rows){const now=usageOf(svc);if(!now.length&&!rows.length)return '';  // no account: the empty line says it
 if(now.length)return `<div class="acc-now on" role="status"><span class="acc-dot" aria-hidden="true"></span><div><b class="acc-now-t">Utilisé maintenant</b>${now.map(u=>`<p>${usageWho(u,svc)} · ${esc(u.what)}${u.since?` <small>depuis ${accHH(Date.parse(u.since)/1000)}</small>`:''}</p>`).join('')}</div></div>`;
 const last=rows.map(r=>[r,rowLast(r)]).filter(([,t])=>t).sort((a,b)=>b[1]-a[1])[0];
 if(!last)return `<div class="acc-now"><span>Pas utilisé en ce moment.</span></div>`;
 const [r,t]=last,who=svc==='flow'?`compte ${r.number||'?'} (${esc(accMask(r.email))})`:r.email?esc(accMask(r.email)):'le compte de cette fenêtre';
 return `<div class="acc-now"><span>Pas utilisé en ce moment · dernier : ${who}, ${accAgo(t)}.</span></div>`;}
// Episode page (0.1.95): « IA : Flow · compte 2 (ar•••5@example.com, 38 crédits) » or « IA : ChatGPT » for each task at work.
function usageAI(u){if(u.service==='flow')return `Flow · compte ${u.number||'?'} (${accMask(u.email||'')}, ${u.credits} crédit${Math.abs(u.credits)>1?'s':''})`;
 return (ENGINE_NAMES[u.service]||u.label)+(u.email?' · '+accMask(u.email):'');}
const TRACK_OF=slot=>{slot=String(slot||'');return slot.startsWith('clip:')?3:slot.startsWith('image')||slot==='board_review'?2:slot.startsWith('character')||slot.startsWith('state:')?1:['cover','cover_review','quality_review','rewrite_meta'].includes(slot)?4:0;};
function trackAI(j,i){const rows=accUsage().in_use.filter(u=>u.job===j.id&&TRACK_OF(u.slot)===i);if(!rows.length)return '';
 return `<div class="track-ai">${rows.map(u=>`<p><span class="acc-dot" aria-hidden="true"></span><span>${esc(u.short||u.what)} · <b>IA : ${esc(usageAI(u))}</b></span></p>`).join('')}</div>`;}
// Under a received clip: the engine and the account that made it (scenes[i].engine since 0.1.93, .account since 0.1.95).
function madeBy(s,full){if(!s?.clip||!s.engine)return '';const name=ENGINE_NAMES[s.engine]||({arena:'Arena'})[s.engine]||s.engine,a=s.account||{};
 if(s.engine==='flow'){const p=(state.profiles||[]).find(x=>x.id===a.profile);const n=p?.number;return name+(n?' · compte '+n:'')+(full&&a.email?' ('+accMask(a.email)+')':'');}
 return name+(full&&a.email?' · '+accMask(a.email):'');}
// Top of Mes comptes: every account working right now, in one glance.
function usageSummary(){const all=accUsage().in_use;if(!all.length)return '';
 return `<section class="panel acc-live-sum" role="status"><h2><span class="acc-dot" aria-hidden="true"></span>En ce moment</h2><ul>${all.map(u=>`<li><span class="acc-ai">${esc(u.label)}</span>${usageWho(u,u.service)}<span class="acc-what">${esc(u.what)}</span></li>`).join('')}</ul></section>`;}
// Sidebar subtitle: the real state (real case 06/11/2026 12:46: « tout est prêt » while Flow blocked the episode).
function accountsSummary(){if(!state)return '';if((state.setup||[]).length)return 'ajoute tes comptes';
 const all=ACC_SERVICES.flatMap(([k])=>accountRows(k)),fix=all.filter(r=>r.text==='À régler'||r.text==='Pas d’accès à Flow').length;
 if(fix)return fix+' compte'+(fix>1?'s':'')+' à régler';
 const walls=(state.quota_status||[]).filter(q=>q.blocked);if(walls.length){const q=walls.sort((a,b)=>a.retry_at-b.retry_at)[0];return q.label.split(' ')[0]+' bloqué jusqu’à '+accHH(q.retry_at);}
 const flow=accountRows('flow');if(flow.length&&flow.every(r=>r.tone!=='ok'&&r.text!=='Non vérifié')){const back=(state.profiles||[]).map(p=>p.refill_at).filter(Boolean).sort((a,b)=>a-b)[0];return back?'Flow bloqué jusqu’à '+accHH(back):'Flow à régler';}
 if((state.jobs||[]).some(j=>j.status==='attention'&&['login','challenge'].includes(j.last_error?.kind)))return 'un compte à régler';
 return 'tout est prêt';}
function accountsWelcome(context){const miss=state.setup||[];if(!miss.length)return '';
 return `<section class="panel acc-welcome"><h2>Ajoute tes comptes pour commencer</h2><p>Il faut un compte prêt pour ${miss.map(m=>`<b>${esc(m.label)}</b>`).join(' et ')} avant de ${context||'créer une vidéo'}. Tu te connectes toi-même ; le studio ne garde aucun mot de passe.</p><ul>${miss.map(m=>`<li>${esc(m.label)} : ${esc(m.reason)}</li>`).join('')}</ul><button class="primary big" data-page="connections">Ouvrir Mes comptes</button></section>`;}
function accountsBlockBanner(){if(!accountsBlock||page==='connections')return '';
 return `<div class="notice human acc-block" role="alert"><b>Comptes à régler avant de commencer</b>${accountsBlock.list.map(b=>`<p class="hint">${esc(b.label)} : ${esc(b.reason)}</p>`).join('')}<div class="actions"><button class="primary" data-page="connections">Ouvrir Mes comptes</button><button class="secondary" data-acc-dismiss="1">Fermer</button></div></div>`;}
function accountsHome(){const R=accReady(),checked=R.checked?new Date(R.checked).toLocaleString('fr-FR',{dateStyle:'short',timeStyle:'short'}):null,running=(R.pending||[]).length;
 const block=([svc,name,needed,role])=>{const rows=accountRows(svc);  // every block shown: the clip engines are all in the order (0.1.93)
  const add=accountOpenButton(svc,svc==='flow'?'+ Ajouter un compte Google':'+ Ajouter ou changer de compte',rows.length?'secondary':'primary');
  const verify=svc==='flow'?`<button class="secondary" data-acc-verify="flow">Actualiser les comptes Flow</button>`:`<button class="secondary" data-ready-recheck="site:${svc}">Actualiser ${esc(name)}</button>`;
  const line=r=>{const uses=rowUses(r),last=rowLast(r);
   const use=uses.length?`<span class="acc-use live">En cours</span><small class="acc-what">${uses.map(u=>esc(u.what)).join(' · ')}</small>`:last?`<small class="acc-last">Dernier utilisé ${accAgo(last)}</small>`:'';
   return `<li class="acc-row${uses.length?' live':''}"><span class="acc-mail">${svc==='flow'?`<span class="acc-num">Compte ${r.number||'?'}</span>`:''}${r.email?esc(accMask(r.email)):'Compte de cette fenêtre'}</span>${svc==='flow'?`<span class="acc-credits${r.credits<Number(state.settings?.flow_cost||12)?' low':''}">${r.credits==null?'Solde inconnu':`<b>${r.credits}</b> crédit${Math.abs(r.credits)>1?'s':''}`}</span>`:''}<span class="acc-state">${pill(r.tone,r.text)}${r.reason?`<small>${esc(r.reason)}</small>`:''}${use}</span><span class="acc-act">${r.scan?`<button class="secondary" data-acc-verify="${esc(r.scan)}">Retrouver ce compte</button>`:r.verify?`<button class="secondary" data-ready-recheck="${r.key}">Vérifier ce compte</button>`:r.fix?`<button class="primary" data-ready-fix="${r.key}">Régler maintenant</button><button class="secondary" data-ready-recheck="${r.key}">C’est fait</button>`:''}${r.del?`<button class="link-btn danger" data-acc-del='${esc(JSON.stringify(r.del))}' data-acc-name="${esc(accMask(r.email||''))}">Supprimer</button>`:''}</span></li>`;};
  return `<section class="panel acc-service${usageOf(svc).length?' in-use':''}"><div class="acc-head"><div><h2>${name} <span class="tag">${needed?'NÉCESSAIRE':'FACULTATIF'}</span></h2><p class="hint">${role}</p></div><div class="acc-buttons">${add}${verify}</div></div>
${svc==='flow'&&rows.length?`<p class="hint">${rows.filter(r=>r.tone==='ok').length} prêt(s) sur ${rows.length}. Utilise « Retrouver ce compte » si Google a changé l’emplacement d’un compte.</p>`:''}${usageBanner(svc,rows)}<ul class="acc-list">${rows.map(line).join('')||`<li class="acc-empty">${svc==='flow'?'Ajoute ton compte Google. Si tu es déjà connecté dans ce profil Chrome, clique sur « Actualiser mes comptes Flow ».':'Connecte-toi dans l’onglet ouvert par le studio. De retour ici, clique sur « Vérifier » si le compte n’apparaît pas.'}</li>`}</ul>${rows.some(r=>r.del)&&rows.length>1?`<div class="acc-foot"><button class="link-btn danger" data-acc-del-all="${svc}" data-acc-name="${name}">Tout supprimer</button></div>`:''}</section>`;};
 const online=Object.values(state.clients||{}).some(c=>!c.disabled&&c.role!=='flow'&&Date.now()-Date.parse(c.seen)<ONLINE_MS);
 const notice=state.bridge_notice;
 const updating=running||(notice?.action==='scan_flow'&&notice.pending&&Date.now()-Date.parse(notice.at)<120000);
 const picker=`<section id="accountPicker" class="panel acc-picker" ${accountPickerOpen?'':'hidden'}>
 <h2>Quel compte veux-tu ajouter ?</h2>
 <p>Choisis un service et connecte-toi dans Chrome. Le compte apparaît ici dès que FruchtDrama détecte la connexion.</p>
 <div class="acc-buttons">${ACC_SERVICES.map(([svc,name])=>accountOpenButton(svc,name)).join('')}</div>
 </section>`;
 return `<div class="intro"><div><h1>Mes comptes</h1><p>Connecte tes services dans Chrome. Commence par ChatGPT et un moteur vidéo.</p></div>
 <div class="acc-buttons"><button type="button" class="primary big" data-acc-picker="1" aria-expanded="${accountPickerOpen}" aria-controls="accountPicker">+ Ajouter un compte</button>
 <button type="button" class="secondary big" data-acc-verify="all" ${updating?'disabled':''}>${ico('refresh')} ${updating?'Actualisation en cours…':'Actualiser tous les comptes'}</button></div></div>
 ${picker}
<p class="hint acc-checked">${running?'Vérification en cours dans la fenêtre FruchtDrama…':checked?'Dernière vérification : '+checked+'.':'Pas encore vérifié.'}</p>
 ${!online?`<p class="notice human" role="status">Connecteur principal hors ligne. Clique sur l’icône FruchtDrama dans Chrome pour ouvrir sa fenêtre avant d’ajouter ou de vérifier un compte.</p>`:''}
 ${notice?.text&&['open','add_google','scan_flow','login','readiness'].includes(notice.action)?`<p class="hint" role="status">${esc(notice.text)}</p>`:''}`+
 usageSummary()+ACC_SERVICES.map(block).join('')+engineOrderBlock();}
document.addEventListener('click',async e=>{const b=e.target.closest?.('[data-acc-picker],[data-engine-up],[data-ready-prepare],[data-ready-fix],[data-ready-recheck],[data-acc-verify],[data-acc-del],[data-acc-del-all],[data-acc-dismiss],[data-wall-wait]');if(!b)return;e.stopImmediatePropagation();
 try{
  if(b.dataset.accPicker){
   accountPickerOpen=!accountPickerOpen;
   const picker=document.getElementById('accountPicker');
   picker.hidden=!accountPickerOpen;
   b.setAttribute('aria-expanded',String(accountPickerOpen));
   return;
  }
  if(b.dataset.engineUp){const o=engineOrder().slice(),i=o.indexOf(b.dataset.engineUp);if(i>0){[o[i-1],o[i]]=[o[i],o[i-1]];await api('/api/settings',{engine_chain:o});await refresh(true);toast('Ordre des moteurs : '+o.map(e=>ENGINE_NAMES[e]).join(' › '));}return}
  if(b.dataset.accDismiss){accountsBlock=null;render();return}
  if(b.dataset.wallWait){wallWaiting.add(b.dataset.wallWait);render();toast('D’accord : reprise automatique à '+b.dataset.wallTime+', rien à faire.');return}
  if(b.dataset.readyPrepare){await api('/api/sites',{action:'prepare'});await refresh(true);toast('Vérification de tous tes comptes en arrière-plan : aucun crédit, aucun prompt.');return}
  if(b.dataset.readyFix){await api('/api/sites',{action:'fix',target:b.dataset.readyFix});toast('L’onglet du compte s’ouvre : règle-le toi-même, puis reviens et clique « C’est fait ».');return}
  if(b.dataset.readyRecheck){await api('/api/sites',{action:'recheck',target:b.dataset.readyRecheck});accountsBlock=null;await refresh(true);toast('Vérification de ce compte…');return}
  if(b.dataset.accVerify){
   const all=b.dataset.accVerify==='all';
   await api('/api/sites',{action:'scan_flow',check:true,check_all:all,profile:['flow','all'].includes(b.dataset.accVerify)?undefined:b.dataset.accVerify});
   await refresh(true);
   toast(all?'Actualisation des comptes demandée.':'Détection Flow demandée dans le profil Chrome concerné.');
   return;
  }
  if(b.dataset.accDel){const d=JSON.parse(b.dataset.accDel),name=b.dataset.accName||'ce compte';if(!window.confirm('Supprimer '+name+' du studio ?\n\nTes vidéos sont gardées. Le compte reste ouvert dans Chrome : déconnecte-toi toi-même si tu veux.'))return;
   if(d.profile)await api('/api/profile/delete',{id:d.profile});else if(d.engine)await api('/api/engine-account',{id:d.engine,delete:true});else await api('/api/account',{email:d.email,remove_service:d.service});await refresh(true);toast('Compte supprimé');return}
  if(b.dataset.accDelAll){if(!window.confirm('Supprimer tous les comptes '+b.dataset.accName+' du studio ?\n\nUne sauvegarde est faite avant. Tes vidéos sont gardées.'))return;const r=await api('/api/account',{remove_all_service:b.dataset.accDelAll});await refresh(true);toast(r.removed+' compte(s) supprimé(s)'+(r.kept.length?' ; gardé(s) car un clip est en cours : '+r.kept.length:''));return}
 }catch(err){toast(err.message)}},true);
const wallWaiting=new Set();
