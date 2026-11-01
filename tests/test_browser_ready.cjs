const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
async function scenario(status,url,probe){
 let probes=0;
 const noop={addListener:()=>{}};
 const chrome={tabs:{get:async()=>({status,url})},scripting:{executeScript:async()=>{probes++;return [{result:probe}];}},runtime:{onInstalled:noop,onStartup:noop,onMessage:noop},alarms:{onAlarm:noop}};
 const ctx=vm.createContext({chrome,URL,setTimeout:fn=>{fn();}});
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/background-worker.js'),'utf8'),ctx);
 const promise=vm.runInContext("ready(1,{kind:'chat_image',payload:{provider:'chatgpt'}})",ctx);
 return {promise,getProbes:()=>probes};
}
(async()=>{
 const editor=await scenario('loading','https://chatgpt.com/',true);await editor.promise;assert.equal(editor.getProbes(),1);
 const complete=await scenario('complete','https://chatgpt.com/',true);await complete.promise;assert.equal(complete.getProbes(),1);
 const timeout=await scenario('loading','https://chatgpt.com/',false);await assert.rejects(timeout.promise,/90 secondes/);
 const wrong=await scenario('complete','https://unrelated.example/',true);await assert.rejects(wrong.promise,/aucun prompt envoyé/);assert.equal(wrong.getProbes(),0);
 console.log('4 contrôles du chargement réussis : éditeur prêt, page complète, délai et domaine incorrect.');
})().catch(e=>{console.error(e);process.exitCode=1;});
