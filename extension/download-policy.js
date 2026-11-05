globalThis.FruchtDownloads={
 timeoutMs:5*60*1000,
 matches(item,request){
  if(!item||!request||!Number.isFinite(Date.parse(item.startTime))||!Number.isFinite(Date.parse(request.requestedAt)))return false;
  const delta=Date.parse(item.startTime)-Date.parse(request.requestedAt);
  if(delta < -1000 || delta>this.timeoutMs)return false;
  const flowHost=url=>{try{return ['flow.google.com','labs.google'].includes(new URL(url).hostname);}catch{return false;}};
  const origin=flowHost(item.referrer)||(/^blob:https:\/\//.test(item.url||'')&&flowHost(item.url.slice(5)));
  return origin&&(/video\/(mp4|webm)/i.test(item.mime||'')||/\.(mp4|webm)$/i.test(item.filename||''));
 },
 choose(items,request){
  const candidates=items.filter(item=>this.matches(item,request));
  if(candidates.length>1)throw Error('Plusieurs téléchargements Flow correspondent à la tâche. Aucun fichier choisi automatiquement.');
  return candidates[0]||null;
 }
};
