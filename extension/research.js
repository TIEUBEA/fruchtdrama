// Search-card observations only; no invented views, dates, or audience geography.
globalThis.FruchtResearch={
 number(value){
  if(!value)return null;
  const text=String(value).trim().replace(/[\u00a0\u202f]/g,' ');
  const m=text.match(/^(\d+(?:[.,]\d+)?)\s*(k|m|b|tsd\.?|mio\.?)?$/i);
  return m?Number(m[1].replace(',','.'))*({k:1e3,m:1e6,b:1e9,tsd:1e3,mio:1e6}[m[2]?.toLowerCase().replace('.','')]||1):null;
 },
 metrics(card){
  const result={views:null,likes:null,signal:null};
  if(!card)return result;
  const nodes=[...card.querySelectorAll('strong,[data-e2e],[aria-label]')];
  for(const node of nodes){
   const label=node.getAttribute('aria-label')||'',marker=node.getAttribute('data-e2e')||'';
   const value=this.number(node.innerText||node.textContent);
   const viewMarker=/^(?:video-views|search-card-video-views|search-card-views|search_video-views)$/i.test(marker);
   const likeMarker=/^(?:like-count|video-like-count|search-card-like-count)$/i.test(marker);
   let tagged=label.match(/^(\d+(?:[.,]\d+)?\s*(?:k|m|b|tsd\.?|mio\.?)?)\s*(views?|vues?|Aufrufe|likes?|mentions? J[’']aime|Gefällt mir)$/i);
   const amount=tagged?this.number(tagged[1]):value;
   if(amount===null)continue;
   if(viewMarker||tagged&&/views?|vues?|Aufrufe/i.test(tagged[2]))result.views=amount;
   else if(likeMarker||tagged)result.likes=amount;
   else if(result.signal===null&&value!==null)result.signal=value;
  }
  return result;
 },
 extract(doc){
  const rows=[],seen=new Set();
  for(const a of doc.querySelectorAll('a[href*="/video/"]')){
   let u;try{u=new URL(a.href);}catch{continue;}
   if(!['www.tiktok.com','tiktok.com'].includes(u.hostname)||!/^\/@[^/]+\/video\/\d+$/.test(u.pathname)||seen.has(u.pathname))continue;
   seen.add(u.pathname);
   let card=a.closest('[data-e2e="search_top-item"],[data-e2e="search-common-link"],[data-e2e="search-common-card"]')||a.parentElement?.parentElement||a;
   const urls=new Set([...card.querySelectorAll('a[href*="/video/"]')].map(x=>{try{return new URL(x.href).pathname;}catch{return '';}}).filter(Boolean));
   if(urls.size>1)card=a;
   const title=(card.innerText||a.getAttribute('aria-label')||a.innerText||'').slice(0,1500);
   const time=card.querySelector('time[datetime]'),raw=time?.getAttribute('datetime')||'';
   const date=/^\d{4}-\d{2}-\d{2}(?:T|$)/.test(raw)?raw.slice(0,10):'';
   rows.push({url:'https://www.tiktok.com'+u.pathname,title,...this.metrics(card),date});
   if(rows.length>=30)break;
  }
  return rows;
 }
};
