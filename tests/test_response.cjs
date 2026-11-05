const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const context={};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../extension/response.js'),'utf8'),context);
const reader=context.FruchtResponse;
const script={title:'Eine Reise',characters:[{id:'oma'}],scenes:Array.from({length:4},()=>({dialogue:[{speaker:'oma',text:'Wir fahren ans Meer.'}]}))};
assert.equal(reader.parse(JSON.stringify(script),4).scenes.length,4);
assert.equal(reader.parse(JSON.stringify(script).slice(0,-1),4),null,'An incomplete response is never accepted');
assert.equal(reader.parse(JSON.stringify(script),6),null,'The input example cannot be accepted as the completed scenario');
assert.equal(reader.parse('```json\n'+JSON.stringify(script)+'\n```',4).title,script.title);
assert.equal(reader.parse('Some prose, not JSON',4),null);
const root={innerText:'json\nCopy\n'+JSON.stringify(script),querySelectorAll:()=>[{innerText:JSON.stringify(script)}]};
const doc={querySelectorAll:s=>s==='[data-message-author-role="assistant"]'?[root]:[]};
assert.equal(JSON.parse(reader.extract(doc,4)).title,script.title,'Read completed JSON without relying on a localized stop button');
assert.equal(reader.parse(JSON.stringify({...script,production_id:'other'}),4,'expected'),null,'Never accept a different production');
assert.equal(reader.parse(JSON.stringify({...script,production_id:'expected'}),4,'expected').title,script.title);
assert.equal(reader.parse(JSON.stringify({...script,production_id:'expected',generation_task_id:'old'}),4,'expected','new'),null,'Do not collect a previous rewrite in the same conversation');
assert.equal(reader.parse(JSON.stringify({...script,production_id:'expected',generation_task_id:'new'}),4,'expected','new').title,script.title);
assert.equal(reader.parse(JSON.stringify(script),4,'expected'),null,'New productions require an explicit correlation ID');
const example={...script,production_id:'expected',scenes:script.scenes.slice(0,1)};
const reply={...script,production_id:'expected',title:'Eine Reise mit {Überraschung} und "Freude"'};
assert.equal(reader.parse('Beispiel: '+JSON.stringify(example)+'\nAntwort: '+JSON.stringify(reply),4,'expected').title,reply.title,'Handle the input example and final JSON in one plain-text page');
const plainDoc={querySelectorAll:()=>[],querySelector:()=>({innerText:'Prompt '+JSON.stringify(example)+'\nChatGPT '+JSON.stringify(reply)})};
assert.equal(JSON.parse(reader.extract(plainDoc,4,'expected')).production_id,'expected','Read plain text without a code block or provider-specific wrapper');
assert.equal(reader.extract(plainDoc,4,'different'),null,'Never use a plain-text response from another production');
console.log('12 contrôles de récupération réussis, dont texte brut sans fichier et réponses mélangées au prompt.');
if(process.argv[2]){
 const actual=fs.readFileSync(process.argv[2],'utf8');const parsed=reader.parse(actual,3,'3a486a9d2669480c');assert.ok(parsed);assert.equal(parsed.characters.length,2);
 console.log('Réponse réelle jointe par le propriétaire : correctement extraite.');
}

assert.equal(reader.parse('Broken example: {\"text\": \"unterminated\n'+JSON.stringify(reply),4,'expected').title,reply.title,'A malformed prompt example must not swallow the bound reply');

const contentDoc={querySelectorAll:()=>[],querySelector:()=>({innerText:'Markdown display changed punctuation',textContent:JSON.stringify({...reply,generation_task_id:'new'})})};
assert.equal(JSON.parse(reader.extract(contentDoc,4,'expected','new')).title,reply.title,'Read raw textContent when rendered innerText alters JSON');

const splitLayout={querySelectorAll:()=>[],querySelector:()=>({textContent:'Prompt only'}),body:{textContent:JSON.stringify({...reply,generation_task_id:'new'})}};
assert.equal(JSON.parse(reader.extract(splitLayout,4,'expected','new')).title,reply.title,'Read a bound reply rendered outside the first main element');
assert.equal(reader.extract(splitLayout,4,'expected','other'),null,'Body fallback still requires the exact request ID');

const qualityReply={production_id:'job',generation_task_id:'task',quality_review:{scenes:[{index:0,status:'pass',detail:'Same pear in sampled frames'}],continuity:{status:'uncertain',detail:'Object hidden'}}};
assert.ok(reader.parse(JSON.stringify(qualityReply),1,'job','task','quality_review'));
assert.equal(reader.parse(JSON.stringify(qualityReply),1,'job','other','quality_review'),null);
assert.equal(reader.parse(JSON.stringify(qualityReply),2,'job','task','quality_review'),null);
// Board check before the clips (lot 4): read only the verdict bound to this task, one per board.
const boardReply={production_id:'job',generation_task_id:'task',board_review:{boards:[{index:0,status:'pass',detail:'ok'},{index:1,status:'issue',detail:'personnage en trop'}]}};
assert.ok(reader.parse('Example {"production_id":"job"} then '+JSON.stringify(boardReply),2,'job','task','board_review'),'board verdict read after the example');
assert.equal(reader.parse(JSON.stringify(boardReply),2,'job','other','board_review'),null,'other task refused');
assert.equal(reader.parse(JSON.stringify(boardReply),3,'job','task','board_review'),null,'missing board refused');
assert.equal(reader.parse(JSON.stringify({...boardReply,board_review:{boards:[{index:0,status:'maybe',detail:'x'},{index:1,status:'pass',detail:'ok'}]}}),2,'job','task','board_review'),null,'unknown status refused');
assert.equal(reader.parse(JSON.stringify(qualityReply),1,'job','task'),null);
assert.equal(reader.parse(JSON.stringify({...qualityReply,quality_review:{...qualityReply.quality_review,continuity:{status:'perfect',detail:'Unknown'}}}),1,'job','task','quality_review'),null);
