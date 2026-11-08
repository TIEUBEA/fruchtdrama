// 0.1.95 « Utilisé maintenant » (owner 06/11/2026: « quand le compte 1 est utilisé je dois voir que c'est le compte 1 »):
// Flow accounts sorted by credits (empty and blocked at the bottom), numbered, the account at work badged « En cours »,
// « Dernier utilisé il y a 3 min » otherwise, the AI line on the episode page and the account under each clip.
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const ctx=vm.createContext({document:{addEventListener(){}},esc:s=>String(s),pill:(c,t)=>`<${c}>${t}`,ico:()=>'',page:'connections',Date,JSON,Set,Math});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/accounts.js'),'utf8'),ctx);
const now=Date.now()/1000,iso=new Date().toISOString();
const flow=(id,balance,number,extra={})=>({id,flow_email:id+'.fruit@example.com',balance,number,flow_url:'u',readiness:{state:'ready',at:iso},...extra});
ctx.state={setup:[],settings:{flow_cost:12},quota_status:[],jobs:[],identities:[{email:'olga@example.com',services:['chatgpt']}],
 engine_accounts:[{id:'g1',engine:'grok',email:'grok.one@example.com'},{id:'g2',engine:'grok',email:'grok.two@example.com'}],sites:{},
 readiness:{sites:{chatgpt:{state:'ready',email:'olga@example.com',at:iso},grok:{state:'ready',at:iso}},pending:[]},
 profiles:[flow('aa',12,1),flow('bb',0,2,{refill_at:now+3600}),flow('cc',38,3),flow('dd',90,4,{readiness:{state:'fix',reason:'Connexion requise',at:iso}}),flow('ee',50,5)],
 usage:{in_use:[{key:'flow:cc',service:'flow',label:'Google Flow',what:'Clip 3 de BANANITO',short:'Clip 3',job:'j',slot:'clip:2',email:'cc.fruit@example.com',number:3,credits:38,since:iso},
   {key:'site:chatgpt',service:'chatgpt',label:'ChatGPT',what:'Planche 7 de BANANITO',short:'Planche 7',job:'j',slot:'image:6',since:iso}],
  last_used:{'flow:ee':now-180,'engine:grok:grok.two@example.com':now-3*3600}}};
vm.runInContext('globalThis.o={rows:accountRows("flow"),home:accountsHome()}',ctx);
const {rows,home}=ctx.o;
// 1. Most credits first, empty then blocked at the bottom; each keeps its own number.
assert.deepEqual(rows.map(r=>[r.number,r.credits,r.text]),[[5,50,'Prêt'],[3,38,'Prêt'],[1,12,'Prêt'],[2,0,'Vide'],[4,90,'À régler']]);
assert.match(rows[3].reason,/^Recharge à \d\d:\d\d$/,'refill time shown for an empty account');
ctx.state.profiles.push(flow('unknown',0,6));
vm.runInContext('globalThis.unknown=accountRows("flow").find(r=>r.number===6)',ctx);
assert.equal(ctx.unknown.credits,null);
assert.equal(ctx.unknown.text,'Solde à vérifier');
// 2. Mes comptes says who works now, for what, with the credits left.
const flowBlock=home.split('<section').find(x=>x.includes('Google Flow <span'));
assert.match(flowBlock,/Utilisé maintenant/);assert.match(flowBlock,/<b>Compte 3<\/b> \(cc•••t@example\.com, 38 crédits\) · Clip 3 de BANANITO/);
const live=flowBlock.split('<li').filter(x=>x.includes('acc-row live'));
assert.equal(live.length,1,'one row badged');assert.match(live[0],/Compte 3/);assert.match(live[0],/En cours/);
assert.match(flowBlock,/Compte 5<\/span>ee•••t@example\.com[\s\S]*Dernier utilisé il y a 3 min/);
assert.doesNotMatch(home,/cc\.fruit@example\.com/,'addresses stay masked');
const chatBlock=home.split('<section').find(x=>x.includes('ChatGPT <span'));
assert.match(chatBlock,/Utilisé maintenant[\s\S]*<b>ol•••a@example\.com<\/b> · Planche 7 de BANANITO/);assert.match(chatBlock,/acc-row live/);
const grokBlock=home.split('<section').find(x=>x.includes('Grok <span'));
assert.match(grokBlock,/Pas utilisé en ce moment · dernier : gr•••o@example\.com, il y a 3 h\./);
assert.match(home,/En ce moment[\s\S]*Google Flow[\s\S]*ChatGPT/,'summary at the top');
// 3. Episode page: the AI line in the step card, the account under each received clip.
vm.runInContext('globalThis.e={clips:trackAI({id:"j"},3),boards:trackAI({id:"j"},2),none:trackAI({id:"j"},4),'+
 'tile:madeBy({clip:"c.mp4",engine:"flow",account:{profile:"cc",email:"cc.fruit@example.com"}}),full:madeBy({clip:"c.mp4",engine:"flow",account:{profile:"cc",email:"cc.fruit@example.com"}},true),'+
 'grok:madeBy({clip:"c.mp4",engine:"grok",account:{email:"grok.one@example.com"}},true),old:madeBy({clip:"c.mp4",engine:"arena"}),noclip:madeBy({engine:"flow"})}',ctx);
const e=ctx.e;
assert.match(e.clips,/Clip 3 · <b>IA : Flow · compte 3 \(cc•••t@example\.com, 38 crédits\)<\/b>/);
assert.match(e.boards,/Planche 7 · <b>IA : ChatGPT<\/b>/);assert.equal(e.none,'');
assert.equal(e.tile,'Flow · compte 3');assert.equal(e.full,'Flow · compte 3 (cc•••t@example.com)');
assert.equal(e.grok,'Grok · gr•••e@example.com');assert.equal(e.old,'Arena','clips received before 0.1.95: engine only');assert.equal(e.noclip,'');
// 4. Nothing at work: no badge, no summary.
ctx.state.usage={in_use:[],last_used:{}};vm.runInContext('globalThis.h=accountsHome()',ctx);
assert.doesNotMatch(ctx.h,/acc-row live|En ce moment/);assert.match(ctx.h,/Pas utilisé en ce moment\./);
// 5. Episode « Ce qui se passe »: 4 latest useful lines, technical lines and consecutive repeats left to « Tout le journal ».
{const src=fs.readFileSync(path.join(__dirname,'../web/atelier.js'),'utf8');
 const part=src.slice(src.indexOf('const JOURNAL_TECH'),src.indexOf('const journalTime'));
 const jc=vm.createContext({});vm.runInContext(part.replace(/^const journalOpen[\s\S]*?\n(?=function journalLines)/m,'')+';globalThis.f=journalLines;',jc);
 const ev=['Scénario reçu.','Tâche préparée : clip:0','Connecteur en cours : clip:0','Réservation prudente de 12 crédits sur a.','Compte Flow 1 (a, 0 crédit, vide) → compte 2 (b, 38 crédits) ; clips reçus conservés.',
  'Import de la planche dans Flow…','Import de la planche dans Flow…','Média reçu : clip_0.mp4','En cours : Clip 2 · IA : ChatGPT.','Clip 1 reçu.','Clip 1 reçu.','Planche 3 refaite.','Montage lancé.'].map((text,i)=>({at:i,text}));
 assert.deepEqual([...jc.f(ev)].map(e=>e.text),['Montage lancé.','Planche 3 refaite.','Clip 1 reçu.','Compte Flow 1 (a, 0 crédit, vide) → compte 2 (b, 38 crédits) ; clips reçus conservés.']);}
console.log('Utilisé maintenant : comptes Flow triés et numérotés, compte en cours, dernier usage, ligne IA de l’épisode et compte sous chaque clip vérifiés.');
