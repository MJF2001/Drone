import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const out=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(out,'../..');
const src=path.join(root,'DeepSeek_底层算法开发比较_20261018');
const methods=['P2_MULTI','TREE_MST','OARP_CORE2','PPCPP_CORE4','EPSILON_STAR'];
const names=['P2','TREE','OARP核心','PPCPP','ε*'];
const cases=['small_g2','small_g3','small_g4','medium_g1','medium_g2','medium_g4','large_g1','large_g2','large_g3','large_g4'];
const batches=['LONG120','BUDGET20','BUDGET1'];
let rows=[];
for(const b of batches){
 const dir=path.join(src,'runs',b,'results');
 for(const file of await fs.readdir(dir)) if(file.endsWith('.json')){
  const r=JSON.parse(await fs.readFile(path.join(dir,file),'utf8'));
  if(r.kind==='development')rows.push({...r,source:path.join(dir,file)});
 }
}
rows.sort((a,b)=>batches.indexOf(a.batch)-batches.indexOf(b.batch)||cases.indexOf(a.case_id.replace('_development',''))-cases.indexOf(b.case_id.replace('_development',''))||a.seed-b.seed||methods.indexOf(a.method_id)-methods.indexOf(b.method_id));
if(rows.length!==300||new Set(rows.map(r=>r.run_id)).size!==300)throw Error('invalid 300-run set');
const headers=['run_id','批次','地图','事件类型','种子','算法','预算_秒','路线_步','总调用_秒','预算内返回','完整合法','覆盖完整','最终来源','选中保底','原始状态','原始自然标志_待核心复核','rank状态','rank上限','原始结果文件'];
const raw=rows.map(r=>[r.run_id,r.batch,r.case_id,r.input?.meta?.event??'',r.seed,r.method_id,r.soft_limit_seconds,r.route_steps??null,r.call_total_seconds??null,!!r.within_budget,!!r.audit?.valid,!!r.audit?.coverage_complete,r.final_source??'',!!r.fallback_used,r.status,r.termination?.natural??null,r.meta?.rank_status??'',r.meta?.rank_cap??null,r.source]);
const noteRows=[
 ['实验范围','10个真实历史快照 × 5种方法 × 2种子 × 3预算；300项开发结果。'],
 ['历史来源','事件前由P2规划并实际执行；各方法收到相同位置、覆盖账本、地图、资源和旧路线。'],
 ['OARP旧条带','从共同P2旧路线恢复；这是输入适配，不是在核心中调用P2搜索。不是OARP自身初始计划的整轮实验。'],
 ['路线步数','完整剩余覆盖加返航；无路线留空，不写0。'],
 ['时间单位','秒。call_total_seconds含公共入口到返回的必要计算与检查，子进程启动另计。'],
 ['对照表状态','及时=完整合法且公共返回在预算内；超时=路线合法但公共返回超预算；无路线=未形成评分路线。'],
 ['超时结果','仍展示已保存路线与耗时，只作诊断，不冒充预算内成绩。'],
 ['自然结束','保留原始标志供核查；部分OARP内部时限与上层标志不一致，不能直接用它证明核心自然结束。'],
 ['保底来源','最终选中保底不证明核心没算完；可能核心更长或等长。看逐次明细final_source。'],
 ['独立算法比较','本批是同快照条件比较，不是各算法自行初始化、执行、发现事件的完整流程比较。'],
 ['简称','OARP为OARP_CORE2；PPCPP为PPCPP_CORE4；ε*为当前场景核心适配；TREE不是TRACE。'],
 ['精度','表格显示到0.001秒；逐次明细保留数值原精度，CSV保留完整精度。'],
 ['来源目录',path.join(src,'runs')],
 ['数据处理','仅从保存JSON提取与逐行引用，不启动规划器、不筛除超时或失败。'],
 ['汇总限制','不同方法成功子集不同；不据各自成功子集的中位数直接排名。']
];
const wb=Workbook.create();
function style(sheet,range){sheet.showGridLines=false;sheet.getRange(range).format.font={name:'Arial',size:10};sheet.getRange(range).format.rowHeight=24;sheet.getRange(range).format.verticalAlignment='center';}
const notes=wb.worksheets.add('阅读说明');
notes.getRange('A2').values=[['算法步数与时间详细结果']];
notes.getRange('A2').format.font={name:'Arial',size:15,bold:true};
notes.getRange(`A4:B${noteRows.length+3}`).values=noteRows;
style(notes,`A4:B${noteRows.length+3}`);
notes.getRange(`A4:A${noteRows.length+3}`).format.font.bold=true;
notes.getRange('A:A').format.columnWidth=22;
notes.getRange('B:B').format.columnWidth=105;
notes.getRange(`B4:B${noteRows.length+3}`).format.wrapText=true;
notes.getRange(`A4:B${noteRows.length+3}`).format.rowHeight=39;
const views=batches.map((b,i)=>wb.worksheets.add(['120秒逐图','20秒逐图','1秒逐图'][i]));
const data=wb.worksheets.add('300项逐次明细');
data.getRangeByIndexes(0,0,301,headers.length).values=[headers,...raw];
style(data,'A1:S301');
data.getRange('A1:S1').format={fill:'#193B53',font:{name:'Arial',bold:true,color:'#FFFFFF',size:10},rowHeight:40,wrapText:true};
data.getRange('A:S').format.columnWidth=19;
data.getRange('A:A').format.columnWidth=56;
data.getRange('C:C').format.columnWidth=25;
data.getRange('F:F').format.columnWidth=22;
data.getRange('H2:H301').setNumberFormat('0');data.getRange('I2:I301').setNumberFormat('0.000000');
data.getRange('M:M').format.columnWidth=29;data.getRange('O:O').format.columnWidth=30;data.getRange('S:S').format.columnWidth=65;
data.freezePanes.freezeRows(1);data.freezePanes.freezeColumns(3);
data.tables.add('A1:S301',true,'AllRuns');
const idx=new Map(rows.map((r,i)=>[r.run_id,i+2]));
let md='# 算法实验详细步数与耗时\n\n来源：已保存300项开发结果。所有耗时为秒，均包含完整剩余任务与返航。两次种子分别列出。\n\n';
md+='说明：**迟**表示完整合法路线在公共预算之后返回，只作诊断；**无**表示没有评分路线。未标记者及时合法。原始自然结束标志需按核心状态另行核查。本批共享P2执行历史，不是各方法自行初始化的整轮实验。\n\n';
const display=[];
for(let bi=0;bi<3;bi++){
 const sheet=views[bi],batch=batches[bi];
 sheet.getRange('A2').values=[[`${[120,20,1][bi]}秒预算：逐图步数与耗时`]];sheet.getRange('A2').format.font={name:'Arial',size:15,bold:true};
 sheet.getRange('A3').values=[['步数与耗时均展示原始返回；“超时”不计预算内成绩。两种子逐项列出。']];
 const head=['地图','种子',...names.flatMap(n=>[n+'步数',n+'秒',n+'返回'])];
 sheet.getRange('A5:Q5').values=[head];
 style(sheet,'A5:Q25');sheet.getRange('A5:Q5').format={fill:'#193B53',font:{name:'Arial',bold:true,color:'#FFFFFF',size:10},rowHeight:34,wrapText:true};
 sheet.getRange('A:A').format.columnWidth=18;sheet.getRange('B:B').format.columnWidth=14;sheet.getRange('C:Q').format.columnWidth=12;
 let rowNum=6;
 md+=`## ${[120,20,1][bi]}秒预算\n\n每格为“步数 / 秒数”。\n\n| 地图 | 种子 | ${names.join(' | ')} |\n|---|---|${names.map(()=>'---:').join('|')}|\n`;
 for(const c of cases)for(const seed of [20261018,20261019]){
  sheet.getRange(`A${rowNum}:B${rowNum}`).values=[[c,seed]];
  let cells=[];
  for(let mi=0;mi<5;mi++){
   const r=rows.find(x=>x.batch===batch&&x.case_id===c+'_development'&&x.seed===seed&&x.method_id===methods[mi]);
   if(!r)throw Error('missing task');
   const rr=idx.get(r.run_id), col=2+mi*3;
   sheet.getCell(rowNum-1,col).formulas=[[r.route_steps==null?'="—"':`='300项逐次明细'!H${rr}`]];
   sheet.getCell(rowNum-1,col+1).formulas=[[`='300项逐次明细'!I${rr}`]];
   sheet.getCell(rowNum-1,col+2).formulas=[[`=IF('300项逐次明细'!K${rr},IF('300项逐次明细'!J${rr},"及时","超时"),"无路线")`]];
   sheet.getCell(rowNum-1,col).setNumberFormat('0');sheet.getCell(rowNum-1,col+1).setNumberFormat('0.000');
   const flag=r.audit?.valid?(r.within_budget?'':' 迟'):' 无';
   const cell=`${r.route_steps??'—'} / ${r.call_total_seconds.toFixed(3)}${flag}`;
   cells.push(cell);
  }
  md+=`| ${c} | ${seed} | ${cells.join(' | ')} |\n`;
  if(bi===0&&seed===20261018)display.push([c,...cells]);
  if((rowNum-6)%4<2)sheet.getRange(`A${rowNum}:Q${rowNum}`).format.fill='#F0F4F7';
  rowNum++;
 }
 sheet.freezePanes.freezeRows(5);sheet.freezePanes.freezeColumns(2);
 for(let mi=0;mi<5;mi++)sheet.getRangeByIndexes(5,4+mi*3,20,1).conditionalFormats.add('containsText',{text:'超时',format:{fill:'#FFF0D0',font:{color:'#8C4B0D'}}});
 md+='\n';
}
await fs.writeFile(path.join(out,'全部结果_300项详细表.md'),md,'utf8');
const csvEsc=v=>v==null?'':`"${String(v).replaceAll('"','""')}"`;
await fs.writeFile(path.join(out,'全部结果_300项逐次明细.csv'),'\ufeff'+[headers,...raw].map(row=>row.map(csvEsc).join(',')).join('\r\n'),'utf8');
await fs.writeFile(path.join(out,'120秒_种子A_展示.json'),JSON.stringify(display,null,2),'utf8');
wb.recalculate();
console.log((await wb.inspect({kind:'table',range:"'120秒逐图'!A5:H10",include:'values,formulas',tableMaxRows:6,tableMaxCols:8,maxChars:2400})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!',options:{useRegex:true,maxResults:15},summary:'formula scan',maxChars:600})).ndjson);
for(const s of ['阅读说明','120秒逐图','20秒逐图','1秒逐图','300项逐次明细']){
 const range=s==='阅读说明'?'A2:B10':s==='300项逐次明细'?'C1:L10':'A2:Q12';
 const img=await wb.render({sheetName:s,range,scale:1.3,format:'png'});
 await fs.writeFile(path.join(out,`预览_${s}.png`),new Uint8Array(await img.arrayBuffer()));
}
await (await SpreadsheetFile.exportXlsx(wb)).save(path.join(out,'算法步数与时间_300项详细结果.xlsx'));
console.log('EXPORT OK 300 records, 60 comparison rows, 5 worksheets');
