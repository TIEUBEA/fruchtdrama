const why=document.getElementById('why'),retry=document.getElementById('retry');
why.textContent=decodeURIComponent(location.hash.slice(1))||'Studio injoignable.';
retry.onclick=async()=>{
 retry.disabled=true;retry.textContent='Démarrage…';
 const r=await chrome.runtime.sendMessage({type:'start-studio'}).catch(e=>({ok:false,error:e.message}));
 if(r?.ok){location.replace('http://127.0.0.1:8840/');return;}
 why.textContent=r?.error||'Démarrage impossible.';retry.disabled=false;retry.textContent='Réessayer';
};
