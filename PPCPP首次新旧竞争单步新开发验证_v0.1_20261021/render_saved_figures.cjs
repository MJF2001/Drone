// Post-run rendering only: all paths are saved actual SVG routes.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const sharp=require('C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const h=__dirname,fig=path.join(h,'figures');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const write=(p,b)=>fs.writeFileSync(p,b,{flag:'wx'});
(async()=>{
  const names=fs.readdirSync(fig).filter(n=>n.endsWith('.svg')).sort();if(names.length!==48)throw Error('expected48 saved diagrams');
  const rows=[];
  for(const n of names){const b=await sharp(fs.readFileSync(path.join(fig,n))).png().toBuffer();const dest=n.replace(/\.svg$/,'.png');write(path.join(fig,dest),b);rows.push({svg:n,png:dest,sha256:hash(b)});}
  const groups=['g00_b012','g03_b018','g05_b032'],conds=['CONTROL','H_SIDE','MIXED_SIDE','U_SIDE'];
  const items=[];let cellHeight=0;
  for(const g of groups)for(const c of conds){const n=`${g}_${c}.png`;const b=await sharp(path.join(fig,n)).resize({width:960}).png().toBuffer();const m=await sharp(b).metadata();cellHeight=Math.max(cellHeight,m.height);items.push(b);}
  const composites=items.map((input,i)=>({input,left:(i%2)*960,top:Math.floor(i/2)*cellHeight}));
  const contact=await sharp({create:{width:1920,height:6*cellHeight,channels:3,background:'white'}}).composite(composites).png().toBuffer();write(path.join(h,'固定三组12条件联系表.png'),contact);
  write(path.join(h,'render_receipt.json'),JSON.stringify({saved_SVGs:48,rendered_PNGs:48,contact_cases:12,source:'saved actual routes only',new_planner_calls:0,new_graph_searches:0,files:rows,contact_sha256:hash(contact)},null,2));
  process.stdout.write('PASS rendered48 saved actual diagrams and12 fixed-condition contact sheet; planner/search0\n');
})().catch(e=>{process.stderr.write(e.stack+'\n');process.exitCode=1;});
