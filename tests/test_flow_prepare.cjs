const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
async function run(pressed){
 const c={};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../extension/flow-controls.js'),'utf8'),c);const f=c.FruchtFlow,events=[];
 const back={click:()=>events.push('back')},agent={getAttribute:k=>k==='aria-pressed'?String(pressed):null,click:()=>events.push('agent-off')},settings={click:()=>events.push('close-settings')};
 f.control=(doc,p)=>p.test('Zurück')?back:p.test('Agentenmodus')?agent:null;f.settingsButton=()=>settings;f.configure=async()=>events.push('configure');
 const frame={innerText:'Frames',getClientRects:()=>[{}],getAttribute:k=>k==='aria-checked'?'true':null};
 f.visible=()=>true;
 await f.prepareFrames({body:{innerText:'Einstellungen für KI-Agenten'},querySelectorAll:()=>[frame]},async()=>{},10);
 assert.deepEqual(events,pressed?['back','agent-off','configure','close-settings']:['back','configure','close-settings']);
}
(async()=>{await run(true);await run(false);const runner=fs.readFileSync(path.join(__dirname,'../extension/runner.js'),'utf8');assert.ok(runner.indexOf('prepareFrames(')<runner.indexOf('openImport('),'Configure manual frames before importing references');console.log('Flow: leave agent settings, switch off only an active agent, prepare video before import.');})().catch(e=>{console.error(e);process.exitCode=1;});

const ctx={};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../extension/flow-controls.js'),'utf8'),ctx);const adapter=ctx.FruchtFlow;adapter.visible=()=>true;
let consent=0;const agree={innerText:'Ich stimme zu',getAttribute:()=>null,click:()=>consent++};
const rights={innerText:'Rechte zur Nutzung dieses Bildes',querySelectorAll:()=>[agree]};
assert.equal(adapter.uploadConsent({querySelectorAll:()=>[rights]}),true);assert.equal(consent,1);
assert.equal(adapter.uploadConsent({querySelectorAll:()=>[{...rights,innerText:'Google sign in'}]}),false);
const named={innerText:'',getAttribute:k=>k==='aria-label'?'reference.jpg':null,querySelector:()=>({src:'https://lh3.googleusercontent.com/ref=w720'})};
assert.equal(adapter.referenceKey({querySelectorAll:()=>[named]},'reference.jpg'),'https://lh3.googleusercontent.com/ref');
assert.equal(adapter.referenceKey({querySelectorAll:()=>[named]},'wrong.jpg'),'');

(async()=>{
 const c={};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../extension/flow-controls.js'),'utf8'),c);const f=c.FruchtFlow;
 for(const label of ['Images','Frames','Cadres','Images clés']){
  let selected=false,clicked=0;
  const frame={innerText:label,getClientRects:()=>[{}],getAttribute:k=>k==='aria-checked'?String(selected):null,click:()=>{selected=true;clicked++;}};
  const imageMode={...frame,innerText:'Image',click:()=>{throw Error('Never select image generation instead of frame mode');}};
  f.configure=async()=>{};f.control=()=>null;f.settingsButton=()=>null;
  await f.prepareFrames({body:{innerText:''},querySelectorAll:()=>[imageMode,frame]},async()=>{},12,'gemini_omni_flash','720p',8);
  assert.equal(clicked,1);assert.equal(selected,true);
 }
 await assert.rejects(()=>f.prepareFrames({body:{innerText:''},querySelectorAll:()=>[]},async()=>{},12),/absent ou ambigu/);
 const notSelected={innerText:'Images',getClientRects:()=>[{}],getAttribute:()=>null,click:()=>{}};
 await assert.rejects(()=>f.prepareFrames({body:{innerText:''},querySelectorAll:()=>[notSelected]},async()=>{},12),/non confirmé/);
 assert.equal(f.count('Vidéo · 720p · 8 sx1'),1);
 assert.equal(f.seconds('Vidéo · 720p · 8 sx1'),8);
 console.log('French Images mode: selected automatically; singular Image excluded; unknown/unconfirmed mode blocked; compact 8 sx1 parsed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
