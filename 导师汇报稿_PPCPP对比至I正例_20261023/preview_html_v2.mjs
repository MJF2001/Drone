import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {spawn} from 'node:child_process';
const dir=path.dirname(fileURLToPath(import.meta.url));
const preview=path.join(dir,'html_v2_preview');
const profile=path.join(preview,'cdp_profile');
fs.mkdirSync(preview,{recursive:true});
const started=Date.now();
const chrome=spawn('C:/Program Files/Google/Chrome/Application/chrome.exe',[
 '--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking','--disable-extensions','--disable-sync','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'
],{windowsHide:true,stdio:'ignore'});
const delay=ms=>new Promise(r=>setTimeout(r,ms));
let ws;
try {
 let portFile=path.join(profile,'DevToolsActivePort');
 for(let i=0;i<100;i++){if(fs.existsSync(portFile)&&fs.statSync(portFile).mtimeMs>=started-500)break;await delay(100);}
 const [port,endpoint]=fs.readFileSync(portFile,'utf8').trim().split(/\r?\n/);
 ws=new WebSocket(`ws://127.0.0.1:${port}${endpoint}`);
 await new Promise((r,j)=>{ws.addEventListener('open',r,{once:true});ws.addEventListener('error',j,{once:true});});
 let next=0;const pending=new Map();
 ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.reject(new Error(JSON.stringify(m.error))):p.resolve(m.result);}}});
 function call(method,params={},sessionId){const id=++next;return new Promise((resolve,reject)=>{pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params,...(sessionId?{sessionId}:{})}));});}
 const {targetId}=await call('Target.createTarget',{url:'about:blank'});
 const {sessionId}=await call('Target.attachToTarget',{targetId,flatten:true});
 const run=(method,params={})=>call(method,params,sessionId);
 const evaluate=async expression=>{const r=await run('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 await run('Page.enable');await run('Runtime.enable');
 const receipts=[];
 const timingOnly=process.argv.includes('--timing');
 const attemptsOnly=process.argv.includes('--attempts');
 const directOnly=process.argv.includes('--direct');
 const setupOnly=process.argv.includes('--setup');
 const pivotOnly=process.argv.includes('--pivot');
 const conciseOnly=process.argv.includes('--concise');
 const replayOnly=process.argv.includes('--replay');
 const views=replayOnly?[['desktop_replay',1440,1650,'route-replay'],['mobile_replay',390,1400,'route-replay']]:conciseOnly?[['desktop_concise_top',1440,1400,''],['desktop_concise_principle',1440,1500,'ppcpp-principle'],['mobile_concise_top',390,1200,''],['mobile_concise_principle',390,1600,'ppcpp-principle'],['desktop_concise_results',1440,1500,'final-comparison']]:pivotOnly?[['desktop_principle',1440,1500,'ppcpp-principle'],['mobile_principle',390,1400,'ppcpp-principle'],['desktop_pivot',1440,1700,'research-pivot'],['mobile_pivot',390,1400,'research-pivot']]:setupOnly?[['desktop_setup',1440,1600,'setup'],['mobile_setup',390,1400,'setup'],['desktop_standards',1440,1600,'new-standards'],['mobile_standards',390,1400,'new-standards']]:directOnly?[['desktop_direct',1440,1700,'direct'],['mobile_direct',390,1500,'direct']]:attemptsOnly?[['desktop_attempts',1440,1600,'attempts'],['mobile_attempts',390,1400,'attempts'],['desktop_branches',1440,1500,'research-local'],['mobile_branches',390,1400,'research-direction']]:timingOnly?[['desktop_timing',1440,1450,'compare'],['mobile_timing',390,1200,'compare']]:[['desktop_top',1440,1000,''],['desktop_cases',1440,1250,'cases'],['desktop_chart',1440,1600,'hypothesis'],['mobile_top',390,1100,''],['mobile_chart',390,1200,'hypothesis']];
 for(const [name,width,height,anchor] of views){
  await run('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<600,screenWidth:width,screenHeight:height});
  await run('Page.navigate',{url:pathToFileURL(path.join(dir,'导师汇报稿_图文阅读版.html')).href});
  for(let i=0;i<50;i++){if(await evaluate("document.readyState==='complete' && !!document.querySelector('main')"))break;await delay(80);}
  await evaluate("Promise.all([document.fonts.ready,...[...document.querySelectorAll('main img')].map(i=>i.decode().catch(()=>{}))]).then(()=>true)");
  await evaluate(`document.documentElement.style.scrollBehavior='auto';${anchor?`document.getElementById(${JSON.stringify(anchor)}).scrollIntoView({block:'start',behavior:'instant'})`:'window.scrollTo(0,0)'}`);
  await delay(100);
  const qa=await evaluate(`(()=>{const over=[...document.querySelectorAll('main > section,.flow,.comparison-panels,.rule-grid,nav')].filter(e=>e.getBoundingClientRect().right>innerWidth+2).map(e=>e.id||e.className);return {viewport:innerWidth,bodyWidth:document.body.scrollWidth,brokenImages:[...document.querySelectorAll('main img')].filter(i=>!i.complete||i.naturalWidth===0).length,layoutOverflow:over,scrollY:scrollY};})()`);
  if(qa.brokenImages||qa.layoutOverflow.length||qa.bodyWidth>qa.viewport+2)throw new Error(JSON.stringify({name,qa}));
  const screen=await run('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
  const screenshot=path.join(preview,name+'.png');fs.writeFileSync(screenshot,Buffer.from(screen.data,'base64'));
  receipts.push({name,width,height,screenshot,qa});
 }
 const replayChecks=replayOnly?await evaluate(`(()=>{const A=window.routeReplayAudit;const s=A.snapshot();const start=s.cards.every(c=>c.stat.includes('已飞 0.0'));A.seek(s.maxSteps);const end=A.snapshot();const allFinished=end.cards.every(c=>c.state.includes('已完成并返航')&&c.state.includes('100.0%'));A.seek(s.maxSteps/2);const middle=A.snapshot().position>0;document.getElementById('replay-reset').click();const reset=A.snapshot().position===0;document.getElementById('replay-play').click();const play=A.snapshot().playing;document.getElementById('replay-play').click();const paused=!A.snapshot().playing;const select=document.getElementById('replay-case');select.value='case00';select.dispatchEvent(new Event('change'));const changed=A.snapshot().caseId==='case00';select.value=s.caseId;select.dispatchEvent(new Event('change'));const nonBlank=[...document.querySelectorAll('#replay-grid canvas')].every(c=>{const a=c.getContext('2d').getImageData(0,0,c.width,c.height).data;let distinct=new Set();for(let i=0;i<a.length;i+=300)distinct.add(a[i]+','+a[i+1]+','+a[i+2]);return distinct.size>4});return {routeCount:A.routeCount,caseCount:A.caseCount,start,allFinished,middle,reset,play,paused,changed,nonBlank};})()`):null;
 if(replayOnly&&(!Object.entries(replayChecks).every(([k,v])=>['routeCount','caseCount'].includes(k)||v)||replayChecks.routeCount!==280||replayChecks.caseCount!==20))throw new Error(JSON.stringify(replayChecks));
 const interactions=await evaluate(`(()=>{const titleCorrect=document.title==='汇报稿'&&document.querySelector('h1').textContent==='汇报稿';const noToolbar=!document.querySelector('.toolbar,#print-report,#expand-evidence');const noNav=!document.querySelector('nav');const scopeCorrect=JSON.stringify([...document.querySelectorAll('main>section')].map(e=>e.id))===JSON.stringify(['setup','compare','attempts','direct']);const detail=document.querySelector('details');detail.querySelector('summary').click();const detailsToggle=detail.open;detail.querySelector('summary').click();document.querySelector('a[href="#ref-R01"]').click();const referenceOpened=[...document.querySelectorAll('details')].some(d=>d.open&&d.contains(document.getElementById('ref-R01')));return {titleCorrect,noToolbar,noNav,scopeCorrect,detailsToggle,referenceOpened};})()`);
 if(!Object.values(interactions).every(Boolean))throw new Error(JSON.stringify(interactions));
 const data={engine:'Chrome CDP, isolated headless profile',views:receipts,interactions,replayChecks};
 fs.writeFileSync(path.join(preview,replayOnly?'browser_qa_replay.json':conciseOnly?'browser_qa_concise.json':pivotOnly?'browser_qa_pivot.json':setupOnly?'browser_qa_setup.json':directOnly?'browser_qa_direct.json':attemptsOnly?'browser_qa_attempts.json':timingOnly?'browser_qa_timing.json':'browser_qa_v2.json'),JSON.stringify(data,null,2)+'\n');
 console.log(JSON.stringify(data,null,2));
 await call('Browser.close').catch(()=>{});ws.close();
}catch(e){console.error(e);if(ws)ws.close();chrome.kill();process.exitCode=1;}
