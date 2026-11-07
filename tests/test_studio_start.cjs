// 0.1.69: the extension starts the local studio itself through the native host (Atelier-like).
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
function harness({up=false,reply={ok:true},nativeError=null,startsAfter=1}={}){
 const store={},sent=[];let fetches=0,startedAt=null;
 const chrome={storage:{local:{get:async k=>({[k]:store[k]}),set:async d=>Object.assign(store,d)}},
  runtime:{getURL:p=>'chrome-extension://id/'+p,sendNativeMessage:async(host,msg)=>{sent.push([host,msg]);if(nativeError)throw Error(nativeError);startedAt=fetches;return reply;}}};
 const fetchFn=async()=>{fetches++;if(up||startedAt!==null&&fetches-startedAt>startsAfter)return {ok:true};throw TypeError('Failed to fetch');};
 const ctx={chrome,AbortController,setTimeout,clearTimeout};vm.createContext(ctx);
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/studio-start.js'),'utf8'),ctx);
 let t=1e6;const opts=extra=>({sleep:async()=>{},now:()=>t,...extra});
 return {s:ctx.FruchtStudio,chrome,fetchFn,store,sent,opts,tick:ms=>{t+=ms;}};
}
(async()=>{
 let h=harness({up:true});
 assert.equal(JSON.stringify(await h.s.ensure(h.chrome,h.fetchFn,h.opts())),'{"ok":true}');assert.equal(h.sent.length,0,'running studio: nothing started');
 h=harness();
 const r=await h.s.ensure(h.chrome,h.fetchFn,h.opts());
 assert.equal(r.ok,true);assert.equal(r.started,true);assert.equal(JSON.stringify(h.sent),'[["com.fruchtdrama.studio",{"cmd":"start"}]]');
 // Background loop: asks once, then waits a minute before asking again.
 h=harness({startsAfter:99});
 assert.equal((await h.s.ensure(h.chrome,h.fetchFn,h.opts({wait:false}))).starting,true);
 assert.equal((await h.s.ensure(h.chrome,h.fetchFn,h.opts({wait:false}))).ok,false);assert.equal(h.sent.length,1);
 h.tick(61000);await h.s.ensure(h.chrome,h.fetchFn,h.opts({wait:false}));assert.equal(h.sent.length,2);
 // Not installed on this computer: clear instruction, no technical message.
 h=harness({nativeError:'Specified native messaging host not found.'});
 const miss=await h.s.ensure(h.chrome,h.fetchFn,h.opts());assert.equal(miss.ok,false);assert.equal(miss.missing,true);assert.match(miss.error,/Installer\.cmd/);
 // Host answers with an error (port taken, terms not accepted): passed on as is.
 h=harness({reply:{ok:false,error:'Port 8840 utilise par une autre installation.'}});
 assert.match((await h.s.ensure(h.chrome,h.fetchFn,h.opts())).error,/8840/);
 assert.equal(h.s.offPage(h.chrome,'a b'),'chrome-extension://id/studio-off.html#a%20b');
 // The manifest allows the native host and keeps a fixed key (same ID everywhere).
 const m=JSON.parse(fs.readFileSync(path.join(__dirname,'../extension/manifest.json'),'utf8'));
 assert.ok(m.permissions.includes('nativeMessaging'));assert.ok(m.key.length>300);
 assert.match(fs.readFileSync(path.join(__dirname,'../extension/background.js'),'utf8'),/'studio-start\.js'/);
 console.log('Démarrage du studio par l’extension : lancé si arrêté, une demande par minute en fond, consigne claire si non installé.');
})().catch(e=>{console.error(e);process.exitCode=1;});
