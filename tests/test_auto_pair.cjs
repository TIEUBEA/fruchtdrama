// Hidden studio key: the extension pairs itself once with the local studio, then never again.
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
(async()=>{
 const store={},calls=[];const listener={addListener:()=>{}};
 const chrome={storage:{local:{get:async key=>key==null?{...store}:Array.isArray(key)?Object.fromEntries(key.map(k=>[k,store[k]])):{[key]:store[key]},set:async data=>Object.assign(store,data)}},tabs:{},scripting:{},runtime:{onInstalled:listener,onStartup:listener,onMessage:listener},alarms:{onAlarm:listener}};
 const fetch=async(url,init)=>{calls.push(url);return {ok:true,json:async()=>({client:'c1',token:'secret',enabled:true})};};
 const context=vm.createContext({chrome,URL,Date,setTimeout,fetch});
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/recovery.js'),'utf8'),context);
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/background-worker.js'),'utf8'),context);
 assert.equal(await vm.runInContext('autoPair()',context),true);
 assert.equal(calls[0],'http://127.0.0.1:8840/api/bridge/auto-pair');
 assert.equal(store.token,'secret');assert.equal(store.role,'all');assert.equal(store.enabled,true);assert.equal(store.auto_paired,true);
 assert.equal(await vm.runInContext('autoPair()',context),false,'already paired: no second request');
 assert.equal(calls.length,1);
 // Studio-page buttons run inside the poll loop, which holds both lane flags (0.1.89): they must not lock themselves out.
 vm.runInContext('busy.chat=true;busy.video=true',context);
 await assert.rejects(vm.runInContext('registerFlow(true)',context),e=>!/Attendez la fin/.test(e.message));
 await assert.rejects(vm.runInContext('registerFlow()',context),/Attendez la fin/);
 console.log('Appairage automatique : une seule demande, clé gardée par l’extension, rôle complet activé.');
})().catch(e=>{console.error(e);process.exitCode=1;});
