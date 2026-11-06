// « Mes comptes » simple (owner 06/11/2026: « trop d'informations, je suis perdu ; je ne sais pas comment ajouter un compte
// ni enlever ceux déjà ajoutés »). Like the Atelier, simpler: one block per service, one line per account (Prêt / À régler +
// raison / Bloqué jusqu'à HH:MM, crédits for Flow), « + Ajouter un compte », « Supprimer », « Tout supprimer ».
// Everything technical is in « Avancé », closed. No password is ever asked or kept.
const ACC_SERVICES=[['chatgpt','ChatGPT',true,'personnages, planches et miniature'],['flow','Google Flow',true,'les clips (ou Grok)'],['grok','Grok',false,'les clips, si tu choisis Grok'],['claude','Claude',false,'l’histoire, si tu préfères Claude'],['arena','Arena',false,'les clips, si tu choisis Arena']];
const accHH=t=>new Date(t*1000).toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'});
const accMask=e=>{e=String(e||'');const i=e.indexOf('@');return i<0?e:e.slice(0,2)+'•••'+(i>3?e[i-1]:'')+e.slice(i);};
const accReady=()=>state.readiness||{sites:{},pending:[]};
let accountsBlock=null;
function showAccountsBlock(list){accountsBlock={list:list||[],at:Date.now()};if(typeof render==='function')render();}
// One line per account of a service: {key, email, label, tone, text, reason, fix, del}
function accountRows(svc){const R=accReady(),pending=new Set(R.pending||[]),now=Date.now()/1000;
 if(svc==='flow'){const cost=Number(state.settings?.flow_cost||12);
  return (state.profiles||[]).filter(p=>p.flow_email||p.label).sort((a,b)=>(a.slot??99)-(b.slot??99)).map(p=>{const r=p.readiness||{},key='flow:'+p.id;let tone,text,reason='';
   if(pending.has(key)){tone='idle';text='Vérification…';}
   else if(r.state==='fix'){tone='bad';text='À régler';reason=r.reason||'';}
   else if(p.blocked==='unavailable'||r.state==='no_access'){tone='bad';text='Pas d’accès à Flow';}
   else if((p.balance||0)<cost){tone='warn';text=p.refill_at?'Vide · recharge à '+accHH(p.refill_at):'Vide';}
   else if(r.state==='ready'){tone='ok';text='Prêt';}
   else{tone='idle';text=p.flow_url?'Non vérifié':'À détecter';}
   return {key,email:p.flow_email||p.label,tone,text,reason,credits:p.balance||0,fix:r.state==='fix',del:{profile:p.id}};});}
 const session=(R.sites||{})[svc],seen=(state.sites||{})[svc]||{},live=session?.email||seen.email||null,key='site:'+svc;
 let emails=(state.identities||[]).filter(i=>(i.services||[]).includes(svc)).map(i=>i.email);
 const engine=['grok','arena'].includes(svc)?(state.engine_accounts||[]).filter(a=>a.engine===svc):[];
 for(const a of engine)if(!emails.includes(a.email))emails.push(a.email);
 if(live&&!emails.includes(live))emails.push(live);
 const rows=emails.map(email=>({email}));
 if(!rows.length&&(session||seen.connected))rows.push({email:null});
 const wall=(state.quota_status||[]).filter(q=>q.blocked&&q.service.startsWith(svc)).sort((a,b)=>a.retry_at-b.retry_at)[0];
 return rows.map(row=>{const acc=engine.find(a=>a.email===row.email),mine=!row.email||!live||row.email===live||rows.length===1;let tone,text,reason='';
  if(acc?.wall&&acc.wall.until>now){tone='warn';text='Bloqué (quota) jusqu’à '+accHH(acc.wall.until);}
  else if(!mine){tone='idle';text='En attente · autre compte ouvert';}
  else if(pending.has(key)){tone='idle';text='Vérification…';}
  else if(wall){tone='warn';text='Bloqué (quota) jusqu’à '+accHH(wall.retry_at);}
  else if(session?.state==='fix'){tone='bad';text='À régler';reason=session.reason||'';}
  else if(session?.state==='ready'||(!session&&seen.connected)){tone='ok';text=session?'Prêt':'Connecté · non vérifié';}
  else{tone='bad';text='Pas connecté';}
  return {key,email:row.email,tone,text,reason,fix:mine&&session?.state==='fix',del:row.email?(acc?{engine:acc.id}:{service:svc,email:row.email}):null};});}
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
 const block=([svc,name,needed,role])=>{const rows=accountRows(svc);if(!needed&&!rows.length&&svc!=='claude'&&svc!=='grok')return '';
  const add=svc==='flow'?`<button class="primary big" data-add-google="1">+ Ajouter un compte</button>`:`<button class="primary big" data-site-open="${svc}">+ Ajouter un compte</button>`;
  const verify=svc==='flow'?`<button class="secondary" data-acc-verify="flow">Vérifier</button>`:`<button class="secondary" data-ready-recheck="site:${svc}">Vérifier</button>`;
  const line=r=>`<li class="acc-row"><span class="acc-mail">${r.email?esc(accMask(r.email)):'Compte de cette fenêtre'}</span>${svc==='flow'?`<span class="acc-credits">${r.credits} crédits</span>`:''}<span class="acc-state">${pill(r.tone,r.text)}${r.reason?`<small>${esc(r.reason)}</small>`:''}</span><span class="acc-act">${r.fix?`<button class="primary" data-ready-fix="${r.key}">Régler maintenant</button><button class="secondary" data-ready-recheck="${r.key}">C’est fait</button>`:''}${r.del?`<button class="link-btn danger" data-acc-del='${esc(JSON.stringify(r.del))}' data-acc-name="${esc(accMask(r.email||''))}">Supprimer</button>`:''}</span></li>`;
  return `<section class="panel acc-service"><div class="acc-head"><div><h2>${name} <span class="tag">${needed?'NÉCESSAIRE':'FACULTATIF'}</span></h2><p class="hint">${role}</p></div><div class="acc-buttons">${add}${verify}</div></div>
<ul class="acc-list">${rows.map(line).join('')||`<li class="acc-empty">Aucun compte. Clique « + Ajouter un compte », connecte-toi dans l’onglet qui s’ouvre, reviens ici et clique « Vérifier ».</li>`}</ul>${rows.some(r=>r.del)&&rows.length>1?`<div class="acc-foot"><button class="link-btn danger" data-acc-del-all="${svc}" data-acc-name="${name}">Tout supprimer</button></div>`:''}</section>`;};
 return `<div class="intro"><div><h1>Mes comptes</h1><p>Ajoute tes comptes une fois, ici. Le studio les vérifie avant chaque vidéo, sans rien dépenser. Aucun mot de passe gardé.</p></div><button class="primary big" data-ready-prepare="1">${ico('refresh')} Préparer mes comptes</button></div>
<p class="hint acc-checked">${running?'Vérification en cours dans la fenêtre FruchtDrama…':checked?'Dernière vérification : '+checked+'.':'Pas encore vérifié.'}</p>`+accountsWelcome()+ACC_SERVICES.map(block).join('');}
document.addEventListener('click',async e=>{const b=e.target.closest?.('[data-ready-prepare],[data-ready-fix],[data-ready-recheck],[data-acc-verify],[data-acc-del],[data-acc-del-all],[data-acc-dismiss],[data-wall-wait]');if(!b)return;e.stopImmediatePropagation();
 try{
  if(b.dataset.accDismiss){accountsBlock=null;render();return}
  if(b.dataset.wallWait){wallWaiting.add(b.dataset.wallWait);render();toast('D’accord : reprise automatique à '+b.dataset.wallTime+', rien à faire.');return}
  if(b.dataset.readyPrepare){await api('/api/sites',{action:'prepare'});await refresh(true);toast('Vérification de tous tes comptes en arrière-plan : aucun crédit, aucun prompt.');return}
  if(b.dataset.readyFix){await api('/api/sites',{action:'fix',target:b.dataset.readyFix});toast('L’onglet du compte s’ouvre : règle-le toi-même, puis reviens et clique « C’est fait ».');return}
  if(b.dataset.readyRecheck){await api('/api/sites',{action:'recheck',target:b.dataset.readyRecheck});accountsBlock=null;await refresh(true);toast('Vérification de ce compte…');return}
  if(b.dataset.accVerify){await api('/api/sites',{action:'scan_flow',check:true});await refresh(true);toast('Recherche de tes comptes Google, puis vérification de chacun.');return}
  if(b.dataset.accDel){const d=JSON.parse(b.dataset.accDel),name=b.dataset.accName||'ce compte';if(!window.confirm('Supprimer '+name+' du studio ?\n\nTes vidéos sont gardées. Le compte reste ouvert dans Chrome : déconnecte-toi toi-même si tu veux.'))return;
   if(d.profile)await api('/api/profile/delete',{id:d.profile});else if(d.engine)await api('/api/engine-account',{id:d.engine,delete:true});else await api('/api/account',{email:d.email,remove_service:d.service});await refresh(true);toast('Compte supprimé');return}
  if(b.dataset.accDelAll){if(!window.confirm('Supprimer tous les comptes '+b.dataset.accName+' du studio ?\n\nUne sauvegarde est faite avant. Tes vidéos sont gardées.'))return;const r=await api('/api/account',{remove_all_service:b.dataset.accDelAll});await refresh(true);toast(r.removed+' compte(s) supprimé(s)'+(r.kept.length?' ; gardé(s) car un clip est en cours : '+r.kept.length:''));return}
 }catch(err){toast(err.message)}},true);
const wallWaiting=new Set();
