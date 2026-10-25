const fs=require('node:fs'), path=require('node:path'),crypto=require('node:crypto');
const sharp=require('C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
(async()=>{
 const dir=path.join(__dirname,'figures'),rows=[];
 for(const file of fs.readdirSync(dir).filter(x=>x.endsWith('.svg')).sort()){
  const src=path.join(dir,file),dst=src.slice(0,-4)+'.png';if(fs.existsSync(dst))throw Error('Refuse overwrite '+dst);
  await sharp(src,{density:120}).png().toFile(dst);rows.push({svg:file,png:path.basename(dst),sha256:crypto.createHash('sha256').update(fs.readFileSync(dst)).digest('hex'),metadata:await sharp(dst).metadata()});
 }
 fs.writeFileSync(path.join(__dirname,'render_receipt.json'),JSON.stringify({node:process.version,sharp:sharp.versions,rows,new_planner_calls:0,distance_queries:0},null,2),{flag:'wx'});console.log('Rendered '+rows.length+' fixed figures.');
})().catch(e=>{console.error(e);process.exitCode=1});
