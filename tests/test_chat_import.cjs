const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const c={};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../extension/composer.js'),'utf8'),c);const helper=c.FruchtComposer;helper.visible=()=>true;
function fixture(mode){
 let mounted=mode==='existing',menu=false,blocked=false;const clicks=[];
 const input={accept:'image/png,image/jpeg',disabled:false};
 const button=(name,fn)=>({innerText:'',getAttribute:key=>key==='aria-label'?name:null,click:()=>{clicks.push(name);fn();}});
 const add=button('Dateien und mehr hinzufügen',()=>{menu=true;if(mode==='menu-input')mounted=true;});
 const upload=button('Fotos und Dateien hinzufügen Vom Computer hochladen',()=>{const event={target:{matches:()=>true},preventDefault:()=>blocked=true};listener?.(event);mounted=true;});
 let listener;
 const doc={querySelectorAll:q=>q.startsWith('input')?(mounted?[input]:[]):[add,...(menu?[upload]:[])],addEventListener:(type,fn)=>listener=fn,removeEventListener:()=>listener=null};
 return{doc,input,clicks,blocked:()=>blocked};
}
(async()=>{
 for(const mode of ['existing','menu-input','upload-input']){const f=fixture(mode);assert.equal(await helper.openImport(f.doc,async()=>{}),f.input);assert.equal(f.clicks.length,{existing:0,'menu-input':1,'upload-input':2}[mode]);if(mode==='upload-input')assert.equal(f.blocked(),true,'Do not open a native file picker');}
 await assert.rejects(helper.openImport({querySelectorAll:()=>[]},async()=>{}),/Aucun prompt envoyé/);
 console.log('ChatGPT imports: existing input, lazy menu, lazy upload input, native picker suppression, no send on failure.');
})().catch(e=>{console.error(e);process.exitCode=1;});
