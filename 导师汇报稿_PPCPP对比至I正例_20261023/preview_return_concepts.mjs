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
 for(let i=0;i<60;i++){if(await evaluate('document.readyState==="complete" && !!document.getElementById("return-service-idea")'))break;await delay(100);}
 const checks=await evaluate(`({removed:!document.getElementById('direct-replay')&&!window.directReplayAudit,idea:!!document.getElementById('return-service-idea'),keptComparisons:['scaled-main','scaled-local','scaled-direction'].every(id=>!!document.getElementById(id)),noNewEffect:!document.getElementById('direct').textContent.includes('9.562%')})`);
 if(!Object.values(checks).every(Boolean))throw Error(JSON.stringify(checks));
 const views=[];
 for(const [name,width,height] of [['concept_return_desktop',1440,1600],['concept_return_mobile',390,1500]]){
 await run('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<600});await evaluate('document.getElementById("direct").scrollIntoView({behavior:"instant",block:"start"})');await delay(100);
 const q=await evaluate('({width:innerWidth,body:document.body.scrollWidth})');if(q.body>width+1)throw Error('overflow');views.push({name,...q});const pic=await run('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(path.join(preview,name+'.png'),Buffer.from(pic.data,'base64'));
 }
 fs.writeFileSync(path.join(preview,'browser_qa_return_concepts.json'),JSON.stringify({passed:true,checks,views},null,2));console.log('Concept-only section and retained comparisons passed');await call('Browser.close').catch(()=>{});ws.close();
}catch(e){console.error(e);if(ws)ws.close();chrome.kill();process.exitCode=1;}
