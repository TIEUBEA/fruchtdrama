// Site detection (read-only) and the check routine that only closes the tabs it opened.
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const ctx={URL};vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/sites.js'),'utf8'),ctx);const S=ctx.FruchtSites;
const el=(text,attrs={})=>({innerText:text,getAttribute:k=>attrs[k]??null,getBoundingClientRect:()=>({width:40,height:20})});
const doc=({buttons=[],editor=false,avatar=null})=>({querySelectorAll:q=>q.startsWith('button')?buttons.map(t=>el(t)):q.startsWith('[aria-label*="@"]')?(avatar?[el('',{'aria-label':avatar})]:[]):[],querySelector:q=>editor&&q.startsWith('textarea')?{}:null});
const probe=(name,d,host='x',pathname='/')=>{ctx.location={hostname:host,pathname};return vm.runInContext('FruchtSites.probe',ctx)(name,d);};
assert.equal(probe('chatgpt',doc({buttons:['Log in Log in','Sign up for free'],editor:true})).connected,false,'signed-out ChatGPT (real labels)');
assert.equal(probe('chatgpt',doc({buttons:['New chat'],editor:true})).connected,true);
assert.equal(probe('tiktok',doc({buttons:['For You','Log in']})).connected,false);
assert.equal(probe('tiktok',doc({buttons:['For You','Upload']})).connected,true);
const flow=probe('flow',doc({avatar:'Compte Google arnaud chewa (ArnaudChewa65@gmail.com)'}));assert.equal(flow.connected,true);assert.equal(flow.email,'arnaudchewa65@gmail.com');
assert.equal(probe('flow',doc({})).connected,false);
assert.equal(probe('claude',doc({editor:true}),'claude.ai','/login').connected,false);
(async()=>{
 const created=[],removed=[];
 const chrome={tabs:{query:async()=>[{id:1,url:'https://chatgpt.com/c/1'}],remove:async id=>removed.push(id)},scripting:{executeScript:async({target,func,args})=>func?[{result:{connected:target.tabId===1,site:args[0]}}]:[]}};
 const ws={createTab:async(c,p)=>{const t={id:100+created.length,url:p.url};created.push(p.url);return t;}};
 const out=await S.check(chrome,ws,async()=>{});
 assert.equal(out.chatgpt.connected,true);assert.equal(Object.keys(out).length,6);
 assert.equal(created.length,5,'only missing sites opened');assert.deepEqual(removed.sort(),[100,101,102,103,104],'only the tabs it opened are closed');
 assert.ok(!removed.includes(1),'the owner’s ChatGPT tab is kept');
 console.log('Comptes façon Atelier : détection connecté / non connecté (libellés réels), adresse Flow lue, onglets ouverts pour vérifier puis refermés, onglets du propriétaire gardés.');
})().catch(e=>{console.error(e);process.exitCode=1;});
