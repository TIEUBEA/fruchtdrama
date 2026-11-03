// Studio page <-> extension, like the Atelier: everything is driven from the main page.
// The page posts {frucht:'wake'} after queuing a request; the worker picks it up at once.
document.documentElement.dataset.fruchtExtension=chrome.runtime.getManifest().version;
window.addEventListener('message',e=>{
 if(e.source!==window||e.origin!==location.origin||e.data?.frucht!=='wake')return;
 try{chrome.runtime.sendMessage({type:'poll'});}catch{}
});
