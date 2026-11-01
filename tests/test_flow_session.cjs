const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const ctx={URL,chrome:{runtime:{onMessage:{addListener:()=>{}}}}};
vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/flow-session.js'),'utf8'),ctx);
const session=ctx.FruchtFlowSession;
const url='https://flow.google.com/u/3/project/production';
const target={url,email:'owner@example.com',client:'browser'};
const button=(label,text='')=>({innerText:text,getAttribute:key=>key==='aria-label'?label:null,getClientRects:()=>[{}],click(){this.clicks=(this.clicks||0)+1;}});
const account=button('Compte Google Owner (owner@example.com)');
const doc={location:{href:url},querySelectorAll:()=>[account]};
assert.equal(session.verify(doc,target),true);
assert.equal(session.verify(doc,{...target,email:'another@example.com'}),false);
assert.equal(session.verify({...doc,location:{href:'https://flow.google.com/u/2/project/production'}},target),false);
assert.equal(session.describe({...doc,querySelectorAll:()=>[account,button('Google Account Other (other@example.com)')]}),null);
for(const prefix of ['Compte Google','Google Account','Google-Konto','Cuenta de Google']){
 assert.equal(session.identity({...doc,querySelectorAll:()=>[button(prefix+' (owner@example.com)')]}),'owner@example.com');
}
for(const label of ['Nouveau projet','Neues Projekt','New project']){
 const create=button(label),homeDoc={location:{href:session.home(url)},querySelectorAll:()=>[account,create]};
 session.newProject(homeDoc,target,label);session.newProject(homeDoc,target,label);
 assert.equal(create.clicks,1,'No duplicate project click for the same task');
}
const wrong=button('Créer une collection');
assert.throws(()=>session.newProject({location:{href:session.home(url)},querySelectorAll:()=>[account,wrong]},target,'wrong'),/absent ou ambigu/);
assert.equal(wrong.clicks,undefined);
assert.equal(session.project('https://unrelated.example/project/x'),null);
assert.equal(session.project(url+'/edit/video'),url);

(async()=>{
 const store={},created=[],updated=[];let tabs=[{id:1,url:'https://flow.google.com/u/0/project/user-tab'}];
 const chrome={storage:{local:{get:async key=>({[key]:store[key]}),set:async data=>Object.assign(store,data)}},
  tabs:{query:async()=>tabs,create:async data=>{created.push(data);const tab={...data,id:2};tabs.push(tab);return tab;},update:async(id,data)=>{updated.push({id,...data});const tab={id,...data};tabs=tabs.map(t=>t.id===id?tab:t);return tab;},get:async id=>tabs.find(t=>t.id===id)}};
 const task={id:'task',job:'job',profile:'profile',payload:{flow_route:target}};
 await session.tabFor(task,chrome);assert.equal(created.length,1);assert.equal(updated.length,0,'Do not navigate a user-owned unrelated tab');
 const second={...task,payload:{flow_route:{...target,url:'https://flow.google.com/u/4/project/next'}}};
 await session.tabFor(second,chrome);assert.equal(created.length,1);assert.equal(updated.length,1,'Reuse the connector-owned tab between accounts');
 store.flowProjects={'job:profile':url};
 const cached=await session.prepareProject(task,{id:2},chrome,async()=>{});
 assert.equal(cached.url,url);assert.equal(created.length,1,'Reuse the production project on recovery');
 delete store.flowProjects;let newProjectSent=0,requested=false;
 chrome.scripting={executeScript:async()=>[]};
 chrome.tabs.get=async()=>({id:2,url:requested?'https://flow.google.com/u/3/project/new':session.home(url)});
 chrome.tabs.sendMessage=async(id,message)=>{assert.equal(message.type,'frucht-flow-new-project');newProjectSent++;requested=true;return {ok:true};};
 const fresh=await session.prepareProject(task,{id:2},chrome,async()=>{});
 assert.equal(fresh.url,'https://flow.google.com/u/3/project/new');assert.equal(newProjectSent,1);
 assert.equal(store.flowProjects['job:profile'],fresh.url,'Remember a created project before delivery to the studio');
 console.log('Sessions Flow : identité, comptes distincts, FR/DE/EN, nouveau projet unique, onglet à la demande et reprise sans duplication vérifiés.');
})().catch(e=>{console.error(e);process.exitCode=1;});
