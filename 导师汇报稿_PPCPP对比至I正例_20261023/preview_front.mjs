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
 '--headless=new','--disable-background-timer-throttling','--disable-renderer-backgrounding','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking','--disable-extensions','--disable-sync','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'
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
 await run('Page.enable');await run('Runtime.enable');await run('Page.bringToFront');
 const receipts=[];
 const timingOnly=process.argv.includes('--timing');
 const attemptsOnly=process.argv.includes('--attempts');
 const directOnly=process.argv.includes('--direct');
 const setupOnly=process.argv.includes('--setup');
 const pivotOnly=process.argv.includes('--pivot');
 const conciseOnly=process.argv.includes('--concise');
 const replayOnly=process.argv.includes('--replay');
 const views=[['desktop_front',1440,1800,'continuous-replay'],['mobile_front',390,1500,'continuous-replay']];
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
 const replayChecks=await evaluate(`(()=>{const A=window.continuousReplayAudit,checks=[];for(let i=0;i<7;i++){A.select(i);const start=A.snapshot();if(!start.cards.every(c=>c.unsupported||c.credit===0&&!c.event))throw Error('initial');for(const c of start.cards){for(let j=0;j<c.triggers.length;j++){A.seek(c.triggers[j]-.01);if(A.snapshot().cards.find(x=>x.method===c.method).phase!==j)throw Error('early event');A.seek(c.triggers[j]);if(A.snapshot().cards.find(x=>x.method===c.method).phase!==j+1)throw Error('missing event');}}A.seek(start.max);const end=A.snapshot();if(!end.cards.every(c=>c.unsupported||c.done&&c.credit===c.expected))throw Error('final');checks.push(end);}A.select(0);document.getElementById('cr-play').click();return checks;})()`);
 await delay(1200);const moved=await evaluate('window.continuousReplayAudit.snapshot().t>0');if(!moved)throw Error(JSON.stringify(await evaluate('({state:window.continuousReplayAudit.snapshot(),visibility:document.visibilityState})')));await evaluate("document.getElementById('cr-play').click();window.continuousReplayAudit.select(4);document.getElementById('cr-event-select').value='0';document.getElementById('cr-event').click();document.getElementById('continuous-replay').scrollIntoView()");
 await run('Emulation.setDeviceMetricsOverride',{width:1440,height:1800,deviceScaleFactor:1,mobile:false});
 await evaluate("document.getElementById('continuous-replay').scrollIntoView({block:'start',behavior:'instant'})");const eventImage=await run('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(path.join(preview,'desktop_front_event.png'),Buffer.from(eventImage.data,'base64'));
 const sixMethods=await evaluate(`(()=>{const a=window.routeReplayAudit.snapshot();return {oldCards:a.cards.length,oldRoutes:window.routeReplayAudit.routeCount,newCards:window.continuousReplayAudit.snapshot().cards.length,noOarp:!document.getElementById('compare').textContent.includes('OARP'),nonBlank:[...document.querySelectorAll('#cr-grid canvas')].every(c=>{const a=c.getContext('2d').getImageData(0,0,c.width,c.height).data;let colors=new Set();for(let i=0;i<a.length;i+=300)colors.add(a[i]+','+a[i+1]+','+a[i+2]);return colors.size>4})}})()`);if(sixMethods.oldCards!==6||sixMethods.oldRoutes!==240||sixMethods.newCards!==6||!sixMethods.noOarp||!sixMethods.nonBlank)throw Error(JSON.stringify(sixMethods));
 const interactions=await evaluate(`(()=>{const titleCorrect=document.title==='汇报稿'&&document.querySelector('h1').textContent==='汇报稿';const noToolbar=!document.querySelector('.toolbar,#print-report,#expand-evidence');const noNav=!document.querySelector('nav');const scopeCorrect=JSON.stringify([...document.querySelectorAll('main>section')].map(e=>e.id))===JSON.stringify(['setup','compare','attempts','direct']);const detail=document.querySelector('details');detail.querySelector('summary').click();const detailsToggle=detail.open;detail.querySelector('summary').click();document.querySelector('a[href="#ref-R01"]').click();const referenceOpened=[...document.querySelectorAll('details')].some(d=>d.open&&d.contains(document.getElementById('ref-R01')));return {titleCorrect,noToolbar,noNav,scopeCorrect,detailsToggle,referenceOpened};})()`);
 if(!Object.values(interactions).every(Boolean))throw new Error(JSON.stringify(interactions));
 const data={engine:'Chrome CDP, isolated headless profile',views:receipts,interactions,replayChecks,sixMethods};
 fs.writeFileSync(path.join(preview,true?'browser_qa_front.json':conciseOnly?'browser_qa_concise.json':pivotOnly?'browser_qa_pivot.json':setupOnly?'browser_qa_setup.json':directOnly?'browser_qa_direct.json':attemptsOnly?'browser_qa_attempts.json':timingOnly?'browser_qa_timing.json':'browser_qa_v2.json'),JSON.stringify(data,null,2)+'\n');
 console.log(JSON.stringify(data,null,2));
 await call('Browser.close').catch(()=>{});ws.close();
}catch(e){console.error(e);if(ws)ws.close();chrome.kill();process.exitCode=1;}


