const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
async function check(task,tabId,storageFails){
 let handler;const store={activeTask:{task:{id:'active'},tabId:7,submissionIntent:false}};
 const noop={addListener:()=>{}};
 const chrome={storage:{local:{get:async()=>structuredClone(store),set:async data=>{if(storageFails)throw Error('disk');Object.assign(store,structuredClone(data));}}},runtime:{onMessage:{addListener:fn=>handler=fn},onInstalled:noop,onStartup:noop},alarms:{onAlarm:noop}};
 const ctx=vm.createContext({chrome,URL,Date,setTimeout});
 for(const f of ['recovery.js','background-worker.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension',f),'utf8'),ctx);
 const reply=await new Promise(resolve=>handler({type:'submission-intent',task},{tab:{id:tabId}},resolve));
 return {store,reply};
}
(async()=>{
 const good=await check('active',7,false);assert.equal(good.reply.ok,true);assert.equal(good.store.activeTask.submissionIntent,true);
 for(const [task,tab] of [['other',7],['active',8]]){const r=await check(task,tab,false);assert.equal(r.reply.ok,false);assert.equal(r.store.activeTask.submissionIntent,false);}
 const failed=await check('active',7,true);assert.equal(failed.reply.ok,false);assert.equal(failed.store.activeTask.submissionIntent,false);
 console.log('4 contrôles du point de reprise avant envoi réussis : persistance, tâche, onglet et échec de sauvegarde.');
})().catch(e=>{console.error(e);process.exitCode=1;});
