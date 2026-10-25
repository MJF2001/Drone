// Offline vector rasterization only; never participates in planning time.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const sharp = require('C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
(async () => {
  const dir = path.join(__dirname, 'figures');
  const rendered = [];
  for (const file of fs.readdirSync(dir).filter(x => x.endsWith('.svg')).sort()) {
    const input = path.join(dir, file);
    const output = input.slice(0, -4) + '.png';
    if (fs.existsSync(output)) throw new Error('Refusing overwrite: ' + output);
    await sharp(input, {density: 120}).png().toFile(output);
    rendered.push({svg: file, png: path.basename(output), metadata: await sharp(output).metadata(), sha256: crypto.createHash('sha256').update(fs.readFileSync(output)).digest('hex')});
  }
  fs.writeFileSync(path.join(__dirname, 'render_receipt.json'), JSON.stringify({node: process.version, sharp: sharp.versions, rendered}, null, 2), {flag: 'wx'});
  console.log('Rendered ' + rendered.length + ' fixed SVG illustrations to PNG; offline only.');
})().catch(e => { console.error(e); process.exitCode = 1; });
