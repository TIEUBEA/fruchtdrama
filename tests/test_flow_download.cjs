const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
let matches=true,clicks=[],menu=false;
const item=label=>({innerText:label,getClientRects:()=>[{}],getAttribute:()=>null,click:()=>clicks.push(label)});
const original=item('720p\nOriginalgröße'),upgrade=item('1080p Hochskaliert');
const doc={querySelectorAll:()=>menu?[upgrade,original]:[]};
let downloadLabel='Medien herunterladen';
const ctx={FruchtMedia:{flowMatches:()=>matches},FruchtFlow:{control:(doc,pattern)=>pattern.test(downloadLabel)?({click:()=>{clicks.push('download');menu=true;}}):null},chrome:{runtime:{onMessage:{addListener:()=>{}}}}};
vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/flow-download.js'),'utf8'),ctx);
(async()=>{
 await ctx.FruchtFlowDownload.execute(doc,'exact prompt','task1',async()=>{});assert.deepEqual(clicks,['download','720p\nOriginalgröße']);
 await ctx.FruchtFlowDownload.execute(doc,'exact prompt','task1',async()=>{});assert.equal(clicks.length,2,'Do not start the same download twice');
 matches=false;await assert.rejects(()=>ctx.FruchtFlowDownload.execute(doc,'wrong prompt','task2',async()=>{}),/correspond pas/);assert.equal(clicks.length,2);
 matches=true;original.disabled=true;await assert.rejects(()=>ctx.FruchtFlowDownload.execute(doc,'exact prompt','task3',async()=>{}),/720p originale/);assert.ok(!clicks.includes('1080p Hochskaliert'));
 original.disabled=false;original.innerText="720p\nTaille d'origine";downloadLabel='Télécharger le contenu multimédia';clicks=[];
 await ctx.FruchtFlowDownload.execute(doc,'exact prompt','task-fr',async()=>{});assert.deepEqual(clicks,['download',"720p\nOriginalgröße"]);
 console.log('Libellé français réel du téléchargement et choix original 720p vérifiés.');
 console.log('4 contrôles du téléchargement Flow réussis : prompt, 720p original, idempotence et absence d’achat.');
})().catch(e=>{console.error(e);process.exitCode=1;});
