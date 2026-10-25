const fs=require('fs'),path=require('path'),crypto=require('crypto');
const sharp=require('C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
(async()=>{let rows=[];for(const name of fs.readdirSync(path.join(__dirname,'figures')).filter(n=>n.endsWith('.svg')).sort()){
const input=path.join(__dirname,'figures',name),output=input.replace(/\.svg$/,'.png');if(fs.existsSync(output))throw Error('refuse overwrite '+output);await sharp(input).png().toFile(output);rows.push({svg:name,png:path.basename(output),svg_sha256:crypto.createHash('sha256').update(fs.readFileSync(input)).digest('hex'),png_sha256:crypto.createHash('sha256').update(fs.readFileSync(output)).digest('hex')});}
fs.writeFileSync(path.join(__dirname,'render_receipt.json'),JSON.stringify({node:process.version,sharp:sharp.versions,rows,graph_searches:0},null,2),{flag:'wx'});console.log('RENDERED '+rows.length+' fixed pages');})().catch(e=>{console.error(e);process.exit(1)});
