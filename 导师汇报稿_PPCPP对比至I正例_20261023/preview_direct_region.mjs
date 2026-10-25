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

 await run('Page.navigate',{url:pathToFileURL(path.join(dir,'导师汇报稿_图文阅读版.html')).href});
 for(let i=0;i<80;i++){if(await evaluate('!!window.directReplayAudit'))break;await delay(100);}
 const tests=await evaluate(`(()=>{const A=window.directReplayAudit,R=[];if(A.snapshot().count!==3)throw Error('count');for(let i=0;i<3;i++){A.select(i);let s=A.snapshot();if(!s.cards.every(c=>c.credits===1&&!c.released))throw Error('nonzero initial');for(const c of s.cards){A.seek(c.event_distance-.001);if(A.snapshot().cards[s.cards.indexOf(c)].released)throw Error('early reveal');A.seek(c.event_distance);if(!A.snapshot().cards[s.cards.indexOf(c)].released)throw Error('missing reveal');}A.seek(s.max);s=A.snapshot();if(!s.cards.every(c=>c.credits===c.expected&&JSON.stringify(c.position)===JSON.stringify(c.base)))throw Error('final '+i);A.seek(s.max/2);if(A.snapshot().cards.some(c=>c.credits>c.expected))throw Error('mid '+i);R.push({i,passed:true});}A.select(0);document.querySelector('#dr-play').click();return R})()`);
 await delay(900);if(!await evaluate('window.directReplayAudit.snapshot().t>0'))throw Error('play failed');
 const receipts=[];
 for(const [name,width,height,index] of [['direct_region_small',1440,1500,0],['direct_region_large',1440,1500,2],['direct_region_mobile',390,1700,1]]){
 await run('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<600});
 await evaluate(`window.directReplayAudit.select(${index});document.querySelector('#dr-end').click();document.getElementById('direct-replay').scrollIntoView({behavior:'instant',block:'start'});`);
 await delay(100);
 const qa=await evaluate(`({body:document.body.scrollWidth,width:innerWidth,cards:document.querySelectorAll('#dr-grid canvas').length})`);
 if(qa.body>width+1||qa.cards!==4)throw Error('layout '+JSON.stringify(qa));
 const pic=await run('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(path.join(preview,name+'.png'),Buffer.from(pic.data,'base64'));receipts.push({name,...qa});
 }
 await evaluate(`document.querySelector('#dr-return').click();document.querySelector('#dr-reset').click();if(window.directReplayAudit.snapshot().t!==0)throw Error('reset');document.querySelector('#dr-case').value='2';document.querySelector('#dr-case').dispatchEvent(new Event('change'));if(window.directReplayAudit.snapshot().index!==2)throw Error('select');`);
 fs.writeFileSync(path.join(preview,'browser_qa_direct_region_base.json'),JSON.stringify({passed:true,tests,receipts},null,2));console.log('3 worlds / 12 full flights and desktop/mobile controls passed');
 await call('Browser.close').catch(()=>{});ws.close();
}catch(e){console.error(e);if(ws)ws.close();chrome.kill();process.exitCode=1;}
