const assert=require('node:assert/strict');
const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
const context={};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../extension/composer.js'),'utf8'),context);
const helper=context.FruchtComposer;
function element(props={}){return {hidden:false,disabled:false,id:'',dataset:{},innerText:'',getBoundingClientRect:()=>({width:50,height:30}),getClientRects:()=>[{}],getAttribute(k){return props[k]??null},...props};}
const hiddenTextarea=element({getBoundingClientRect:()=>({width:1,height:1})});
const richEditor=element({id:'prompt-textarea',contenteditable:'true',closest:()=>null});
const doc={querySelectorAll:q=>q.startsWith('#prompt-textarea')?[richEditor]:q.startsWith('textarea')?[hiddenTextarea]:[]};
assert.equal(helper.editor(doc),richEditor,'Prefer the visible rich-text editor to a hidden fallback textarea');
assert.equal(helper.visible(hiddenTextarea),false);
const send=element({'aria-label':'Nachricht absenden'}),stop=element({'aria-label':'Stop generating'}),disabled=element({id:'composer-submit-button',disabled:true});
assert.equal(helper.button({querySelectorAll:()=>[disabled,stop,send]},richEditor),send,'Recognize German send label and reject disabled/stop buttons');
const explicit=element({id:'composer-submit-button'});
assert.equal(helper.button({querySelectorAll:()=>[send,explicit]},richEditor),explicit,'Prefer known composer button');
const outside=element({id:'composer-submit-button'}),form={querySelectorAll:()=>[]};
assert.equal(helper.button({querySelectorAll:()=>[outside]},{closest:()=>form}),outside,'Handle submit button outside editor form');
assert.equal(helper.button({querySelectorAll:()=>[disabled,stop]},richEditor),null,'Do not submit through inactive or stop buttons');
console.log('6 contrôles du connecteur réussis (fixtures DOM, pas un test du compte ChatGPT).');
const footer='Diese Website ist durch reCAPTCHA geschützt. Datenschutzbestimmungen und Nutzungsbedingungen gelten.';
assert.equal(helper.challenge({body:{innerText:footer},querySelectorAll:()=>[]}),false);
const badge=element({title:'reCAPTCHA',getBoundingClientRect:()=>({width:256,height:60})});
assert.equal(helper.challenge({body:{innerText:footer},querySelectorAll:()=>[badge]}),false);
const challenge=element({title:'reCAPTCHA challenge',getBoundingClientRect:()=>({width:400,height:500})});
assert.equal(helper.challenge({body:{innerText:''},querySelectorAll:()=>[challenge]}),true);
assert.equal(helper.challenge({body:{innerText:'Verify you are human'},querySelectorAll:()=>[]}),true);
console.log('4 contrôles de défi réussis : pied de page, badge passif, véritable widget et demande explicite.');
// P2-03: content refusal, only in a NEW short assistant reply.
const reply=t=>element({innerText:t});
const old=reply("I can't create that image because it violates our content policies.");
const fresh=reply("I can't create that image because it violates our content policies.");
const docOf=list=>({querySelectorAll:q=>q==='[data-message-author-role="assistant"]'?list:[]});
assert.equal(helper.refusal(docOf([old]),new Set([old])),null,'an old refusal from a previous attempt is ignored');
assert.match(helper.refusal(docOf([old,fresh]),new Set([old])),/can't create/);
for(const t of ['Je ne peux pas créer cette image, elle enfreint nos règles.','Ich kann dieses Bild nicht erstellen, da es gegen unsere Inhaltsrichtlinien verstößt.','I’m unable to generate that image.'])
 assert.ok(helper.refusal(docOf([reply(t)]),new Set()),t);
assert.equal(helper.refusal(docOf([reply('Here is your image of Oma Orange in the kitchen.')]),new Set()),null,'normal reply');
assert.equal(helper.refusal(docOf([reply('x'.repeat(700)+' content policy')]),new Set()),null,'long reply never read as a refusal');
// P2-04: renewal delay.
assert.equal(helper.retryAfter("You've hit the plus plan limit for image generations requests. You can create more images when the limit resets in 22 hours and 16 minutes."),22*3600+16*60);
assert.equal(helper.retryAfter('Try again. ... Limite atteinte : vous pourrez réessayer, le quota se renouvelle dans 3 heures.'),3*3600);
assert.equal(helper.retryAfter('Limit erreicht. Bitte versuche es in 45 Minuten erneut.'),45*60,'German word order: delay just before the anchor');
assert.equal(helper.retryAfter('Limit erreicht. Erneut möglich in 45 Minuten.'),45*60);
assert.equal(helper.retryAfter('Usage limit reached.'),null);
console.log('Refus de contenu (nouvelle réponse seulement, FR/DE/EN) et délai de renouvellement vérifiés.');
