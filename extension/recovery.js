globalThis.FruchtRecovery={
 isScenario(task){return task?.slot==='script'&&['chat_text','chat_collect'].includes(task.kind);},
 allowedTab(task,url){try{const host=new URL(url).hostname;return host===(task.payload.provider==='claude'?'claude.ai':'chatgpt.com');}catch{return false;}},
 mayCollect(active,context,time){
  if(!this.isScenario(active.task))return false;
  if(['cancelled','done'].includes(context.task_status)||context.job_stage!=='script'||context.job_status==='paused')return false;
  return time-active.startedAt<20*60*1000&&(active.recoveryAttempts||0)<20;
 },
 sameReply(active,taskId,tabId){return !!active&&active.task.id===taskId&&active.tabId===tabId;}
};
