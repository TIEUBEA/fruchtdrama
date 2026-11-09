// FRUIT-Z (09/11/2026): the closing image goes into Flow's « Fin ». Real page layout (new Flow interface, read on
// flow.google.com the same day): chips « Début » [swap_horiz] « Fin »; a filled frame becomes an image button.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const src=fs.readFileSync(path.join(__dirname,'../extension/flow-controls.js'),'utf8');
const ctx=vm.createContext({globalThis:{},document:undefined});ctx.globalThis=ctx;vm.runInContext(src,ctx);
const F=ctx.FruchtFlow;
function el(label,text,rect,img){return {getAttribute:k=>k==='aria-label'?label:null,innerText:text,textContent:text,disabled:false,hidden:false,
 getClientRects:()=>[1],getBoundingClientRect:()=>rect,querySelector:q=>q==='img'&&img?{currentSrc:img,src:img}:null};}
const R=(left,top,w=56,h=56)=>({left,top,right:left+w,bottom:top+h,width:w,height:h});
function page(items){return {defaultView:{getComputedStyle:()=>({visibility:'visible',display:'block'})},querySelectorAll:()=>items};}
const swap=el('Intervertir les première et dernière images','swap_horiz',R(327,763,34,34));
// Début filled, Fin filled: both thumbnails found on their side of the swap button.
const start=el('Ingrédient image','',R(265,752),'https://x/start.jpg'),end=el('Ingrédient image','',R(365,752),'https://x/end.jpg');
let doc=page([start,swap,end]);
assert.equal(F.endThumbnail(doc),end,'Fin thumbnail right of the swap button');
assert.equal(F.startThumbnail(doc),start,'Début thumbnail found without the « Fin » chip');
assert.equal(F.frameThumbnail(doc,'end'),end);assert.equal(F.frameThumbnail(doc,'start'),start);
assert.ok(F.frameMatches(doc,'https://x/end.jpg','end'));assert.ok(!F.frameMatches(doc,'https://x/end.jpg','start'));
// Empty Fin: the chip is matched by the « end » pattern only.
const finChip=el(null,'Fin',R(365,763,40,30)),debutChip=el(null,'Début',R(265,763,50,30));
doc=page([debutChip,swap,finChip]);
assert.equal(F.control(doc,F.slotPattern('end')),finChip);assert.equal(F.control(doc,F.slotPattern('start')),debutChip);
assert.equal(F.endThumbnail(doc),null);
console.log('Flow « Fin » : vignettes Début/Fin repérées autour du bouton d’inversion, cases vides reconnues.');
