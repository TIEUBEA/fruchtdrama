// 0.1.91 « Préparer mes comptes »: page verdicts, ready() failures that say which account to fix, background checks that
// never spend or send, and the simple Mes comptes (sidebar subtitle = real state).
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const ext=f=>fs.readFileSync(path.join(__dirname,'../extension',f),'utf8');
const noop={addListener:()=>{}};
(async()=>{
 // 1. Verdicts.
 {const ctx=vm.createContext({});vm.runInContext(ext('readiness.js'),ctx);const R=ctx.FruchtReadiness;
  const flow={kind:'flow',name:'flow',host:'flow.google.com',expectedHosts:R.HOSTS.flow,expectedEmail:'a@example.com',email:'a@example.com',editor:true,text:true};
  assert.equal(R.classify(flow).state,'ready');
  assert.equal(R.classify({...flow,unavailable:true}).state,'no_access');
  assert.match(R.classify({...flow,challenge:true}).reason,/anti-robot/);
  assert.match(R.classify({...flow,host:'accounts.google.com'}).reason,/Connexion requise/);
  assert.match(R.classify({...flow,email:null}).reason,/Connexion Google requise/);
  assert.match(R.classify({...flow,email:'b@example.com'}).reason,/Autre compte/);
  assert.match(R.classify({...flow,editor:false}).reason,/sans zone de saisie/);
  assert.equal(R.classify({...flow,editor:false,home:true}).state,'ready','home page: the production creates its project');
  const chat={kind:'site',name:'chatgpt',host:'chatgpt.com',expectedHosts:R.HOSTS.chatgpt,editor:true,text:true};
  assert.equal(R.classify(chat).state,'ready');
  assert.equal(R.classify({...chat,text:false,connected:true}).state,'ready');
  assert.match(R.classify({...chat,signIn:true}).reason,/Connexion requise/);
  assert.match(R.classify({...chat,editor:false}).reason,/Zone de saisie absente/);
  assert.match(R.classify({...chat,text:false,editor:false}).reason,/Page vide/);
 }
 // A blank ChatGPT tab cannot hide a second tab with a working session.
 {const ctx=vm.createContext({URL});vm.runInContext(ext('readiness.js'),ctx);const R=ctx.FruchtReadiness;
  const tabs=[{id:1,active:true,url:'https://chatgpt.com/'},{id:2,url:'https://chatgpt.com/c/working'}];
  R.look=async(c,tab)=>tab.id===1?{verdict:{state:'fix',reason:'Page vide ou bloquée'},info:{}}:
   {verdict:{state:'ready',reason:''},info:{email:'test@example.com'}};
  R.forget=async()=>{};
  const result=await R.site({tabs:{query:async()=>tabs}},{},'chatgpt',async()=>{});
  assert.equal(result.state,'ready');
  assert.equal(result.email,'test@example.com');
 }
 // 2. ready() fails on a Flow project showing an anti-robot check: the reason is said, the account is « À régler ».
 {const calls=[];
  const chrome={tabs:{get:async()=>({status:'complete',url:'https://flow.google.com/u/1/project/p'})},
   scripting:{executeScript:async o=>{calls.push(o);if(o.files)return [];if(o.args&&o.args[0]==='flow')return [{result:{email:'a@example.com',challenge:true,editor:false,text:true}}];return [{result:false}];}},
   runtime:{onInstalled:noop,onStartup:noop,onMessage:noop},alarms:{onAlarm:noop}};
  const ctx=vm.createContext({chrome,URL,setTimeout:fn=>{fn();}});
  vm.runInContext(ext('readiness.js'),ctx);vm.runInContext(ext('background-worker.js'),ctx);
  const err=await vm.runInContext("ready(1,{kind:'flow_video',payload:{flow_route:{email:'A@example.com',url:'https://flow.google.com/u/1/project/p'}}},'https://flow.google.com/u/1/project/p').then(()=>null,e=>e)",ctx);
  assert.ok(err,'ready() must fail');assert.match(err.message,/90 secondes \(Vérification anti-robot/);assert.match(err.message,/aucun prompt envoyé/);
  assert.equal(err.flowBlocked,'not_ready');assert.equal(err.notReady.state,'fix');
  assert.ok(!calls.some(o=>/submit|run/.test(String(o.func||''))),'read only');
 }
 // 3. Background check: the ready account's tab closes, the one to fix stays open (inactive) for « Régler maintenant ».
 {let id=10;const created=[],closed=[],store={};
  const pages={'https://flow.google.com/u/0/project/a':{email:'a@example.com',editor:true,text:true},'https://flow.google.com/u/1/project/b':{email:'b@example.com',editor:false,text:true,challenge:true}};
  const tabs={};
  const chrome={storage:{local:{get:async k=>({...store}),set:async v=>Object.assign(store,v)}},
   tabs:{query:async()=>[{id:5,url:'https://chatgpt.com/c/x'}],get:async i=>i===5?{id:5,url:'https://chatgpt.com/c/x',status:'complete'}:{...tabs[i],status:'complete'}},
   scripting:{executeScript:async o=>{if(o.files)return [];const t=o.target.tabId===5?{url:'https://chatgpt.com/'}:tabs[o.target.tabId];
    if(o.args&&o.args[0]==='chatgpt')return [{result:{editor:true,text:true,email:'olga@example.com'}}];
    if(o.args&&o.args[0]==='flow')return [{result:pages[t.url]}];return [{result:{email:pages[t.url]?.email,balance:37}}];}},
   windows:{update:async()=>{}}};
  const ws={createTab:async(c,p)=>{const t={id:++id,url:p.url,windowId:1,active:p.active};tabs[t.id]=t;created.push(t);return t;},close:async(c,ids)=>closed.push(...ids),adopt:async(c,t)=>t};
  const ctx=vm.createContext({chrome,URL,setTimeout:fn=>fn()});vm.runInContext(ext('readiness.js'),ctx);
  const report=await ctx.FruchtReadiness.run(chrome,ws,{id:'r1',sites:['chatgpt'],profiles:[{id:'a',url:'https://flow.google.com/u/0/project/a',email:'a@example.com'},{id:'b',url:'https://flow.google.com/u/1/project/b',email:'b@example.com'}]},async()=>{});
  assert.equal(report.sites.chatgpt.state,'ready');assert.equal(report.sites.chatgpt.email,'olga@example.com');
  assert.equal(report.profiles.a.state,'ready');assert.equal(report.profiles.a.balance,37);
  assert.equal(report.profiles.b.state,'fix');assert.match(report.profiles.b.reason,/anti-robot/);
  assert.ok(created.every(t=>t.active===false),'never in the foreground during a check');
  assert.deepEqual(closed,[created[0].id],'the existing ChatGPT tab is kept, the ready Flow tab closes, the one to fix stays');
  assert.equal(store.readinessTabs['flow:b'],created[1].id);
  // « Régler maintenant » (owner's click): that very tab comes to the front.
  const shown=[];chrome.tabs.update=async(i,p)=>{shown.push([i,p.active]);return tabs[i];};
  await ctx.FruchtReadiness.show(chrome,ws,{type:'show',profile:{id:'b',url:'https://flow.google.com/u/1/project/b'}});
  assert.deepEqual(shown,[[created[1].id,true]]);
 }
 // An already signed-in account is linked without waiting for a new login.
 {const tab={id:5,url:'https://chatgpt.com/',windowId:1},store={},calls=[];
  const chrome={tabs:{query:async()=>[tab],update:async()=>tab},
   windows:{update:async()=>{}},storage:{local:{get:async()=>store,set:async v=>Object.assign(store,v)}},
   runtime:{onInstalled:noop,onStartup:noop,onMessage:noop},alarms:{onAlarm:noop}};
  const ctx=vm.createContext({chrome,URL,Date,FruchtWorkspace:{adopt:async(_,t)=>t},
   FruchtSites:{list:{chatgpt:{hosts:['chatgpt.com']}}},calls});
  vm.runInContext(ext('background-worker.js'),ctx);
  const linked=await vm.runInContext(`loginState=async()=>({connected:true,email:'test@example.com'});
   call=async(path,body)=>calls.push({path,body});openLogin('chatgpt','gateway')`,ctx);
  assert.equal(linked,true);
  assert.equal(calls[0].path,'/api/bridge/sites');
  assert.equal(calls[0].body.sites.chatgpt.email,'test@example.com');
  assert.equal(store.pendingLogins.chatgpt.existing,true);
 }
 // 4. Simple Mes comptes: one line per account, sidebar says the real state.
 {const ctx=vm.createContext({document:{addEventListener(){}},esc:s=>String(s),pill:(c,t)=>`<${c}>${t}`,ico:()=>'',page:'connections',Date,JSON,Set});
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/accounts.js'),'utf8'),ctx);
  const now=new Date().toISOString();
  ctx.state={setup:[],settings:{flow_cost:12},quota_status:[],jobs:[],identities:[{email:'olga@example.com',services:['chatgpt']}],engine_accounts:[],sites:{},
   readiness:{sites:{chatgpt:{state:'ready',email:'olga@example.com',at:now}},pending:[]},
   profiles:[{id:'a',flow_email:'fruit.a@example.com',balance:40,slot:0,flow_url:'u',readiness:{state:'ready',at:now}},{id:'b',flow_email:'fruit.b@example.com',balance:50,slot:1,flow_url:'u',readiness:{state:'fix',reason:'Connexion requise',at:now}}]};
  vm.runInContext('globalThis.out={rows:accountRows("flow"),chat:accountRows("chatgpt"),sum:accountsSummary(),home:accountsHome()}',ctx);
  const o=ctx.out;
  assert.deepEqual(o.rows.map(r=>r.text),['Prêt','À régler']);assert.equal(o.rows[1].reason,'Connexion requise');
  assert.equal(o.chat[0].text,'Prêt');assert.equal(o.sum,'1 compte à régler','real case 12:46: never « tout est prêt » with an account to fix');
  assert.match(o.home,/fr•••a@example\.com/);assert.match(o.home,/fr•••b@example\.com/);assert.doesNotMatch(o.home,/fruit\.a@example\.com/,'addresses partly masked');
  assert.match(o.home,/\+ Ajouter un compte/);assert.match(o.home,/Régler maintenant/);assert.match(o.home,/Tout supprimer/);
  assert.match(o.home,/Actualiser tous les comptes/);
  assert.match(o.home,/aria-controls="accountPicker"/);
  assert.match(o.home,/Quel compte veux-tu ajouter/);
  ctx.state.profiles[1].readiness.state='ready';ctx.state.quota_status=[{service:'chatgpt_image',label:'ChatGPT images',blocked:true,retry_at:Date.now()/1000+1800}];
  vm.runInContext('globalThis.sum=accountsSummary()',ctx);assert.match(ctx.sum,/^ChatGPT bloqué jusqu’à \d\d:\d\d$/);
  ctx.state.setup=[{label:'ChatGPT',reason:'aucun compte prêt'}];
  vm.runInContext('globalThis.sum=accountsSummary();globalThis.w=accountsWelcome()',ctx);assert.equal(ctx.sum,'ajoute tes comptes');assert.match(ctx.w,/Ajoute tes comptes pour commencer/);
 }
 console.log('Préparer mes comptes : verdicts, échec de page expliqué, vérification sans premier plan ni dépense, « Régler maintenant », Mes comptes simple et sous-titre réel vérifiés.');
})().catch(e=>{console.error(e);process.exitCode=1;});
