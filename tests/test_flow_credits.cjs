const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const ctx={Date,URL,chrome:{runtime:{onMessage:{addListener:()=>{}}}}};vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/flow-credits.js'),'utf8'),ctx);const c=ctx.FruchtCredits;
const scope=(labels,text='')=>({innerText:text,querySelectorAll:()=>labels.map(label=>({innerText:label,getAttribute:()=>null}))});
for(const label of ['0 Google Flow-Guthabenpunkte','50 Google Flow credits','50 crédits Google Flow','50 AI credits'])assert.equal(c.parse(scope([label])).balance,label.startsWith('0 ')?0:50);
assert.equal(c.parse(scope(['10 credits used for generation'])),null);assert.equal(c.parse(scope(['10 Google Flow credits','50 Google Flow credits'])),null);
const now=new Date(2026,9,31,18,0).getTime(),result=c.parse(scope(['20 Google Flow-Guthabenpunkte'],'Das Guthaben wird täglich um 19:40 aktualisiert'),now);
assert.equal(result.balance,20);assert.equal(new Date((result.reset_at-120)*1000).getHours(),19);assert.equal(new Date((result.reset_at-120)*1000).getMinutes(),40);
assert.ok(c.parse(scope(['20 Google Flow credits'],'daily at 17:40'),now).reset_at>now/1000);
console.log('Visible Flow balance: FR/DE/EN, zero, ambiguous/cost labels rejected, next daily reset.');

assert.equal(c.parse(scope(['50 crédits Google\u00a0Flow'])).balance,50,'French non-breaking spaces are displayed as normal spaces');

(async()=>{
 const target={email:'owner@example.com',url:'https://flow.google.com/project/test'};ctx.FruchtFlowSession={describe:()=>({...target}),project:url=>url};
 let clicked=0;const button={getClientRects:()=>[{}],getAttribute:()=> 'Détails du compte',click:()=>clicked++};
 const pendingDoc={querySelectorAll:q=>q==='[role="dialog"]'?[]:[button]};
 assert.equal((await c.read(pendingDoc,target)).pending,true);assert.equal(clicked,1,'Open panel without awaiting throttled page timers');
 const panel={...scope(['50 crédits Google\u00a0Flow'],'owner@example.com'),getClientRects:()=>[{}]};
 const completedDoc={querySelectorAll:q=>q==='[role="dialog"]'?[panel]:[button]};
 assert.equal((await c.read(completedDoc,target)).balance,50);
})().catch(e=>{console.error(e);process.exitCode=1;});
