from common import *
from spec import *
import sys,platform
def main():
 assert not (H/'protocol.json').exists();defs=[];slots=[];overview=['# 生成前固定几何概览\n\n#道路，X障碍，.道路外可飞；各图全矩形，y从高到低，x递增。只看几何，不调用算法。']
 for family in ('I','L','Z'):
  for size in SIZES:
   d=definition(size,family);d['base_id']=f'{size}_{family}';defs.append(d);f,t=before(d);assert t<=f and len(f)<=10000
   if family=='Z':assert d['Z_between_corner_straight']>=2*d['w']
   def draw(t,b=set()):return '\n'.join(''.join('X' if (x,y) in b else '#' if (x,y) in t else '.' for x in range(d['domain'][0])) for y in range(d['domain'][1]-1,-1,-1))
   overview+=['## '+d['base_id']+' 原道路',str(d),'```\n'+draw(t)+'\n```']
   for event in ('straight','corner','obstacle'):
    ff,pub,b,selected,valid=after(d,event,(-99,-99));assert valid and pub<=f and len(pub)<=1500
    if event!='obstacle':assert pub-t and not rect(*d[event+'_rectangle'])&t and len(pub-t)==d['extension_length']*d['w']
    for p in (30,70):slots.append(dict(id=f"{d['base_id']}_{event}_p{p}",base_id=d['base_id'],family=family,size=size,L=d['L'],w=d['w'],event=event,progress=p))
    overview+=['### '+event,'```\n'+draw(pub,b)+'\n```']
   overview+=['### 障碍备用侧','```\n'+draw(t,rect(*d['obstacle_rectangles'][1]))+'\n```']
 save(H/'几何坐标表.json',defs);(H/'几何概览.md').write_text('\n\n'.join(overview)+'\n',encoding='utf-8')
 old=R/'PPCPP保留末采集格候选_v0.1_20261020';reused={}
 for n in ('candidate.py','runtime.py','worker.py','audit.py','common.py'):assert sha(H/n)==sha(old/n);reused[n]=dict(source=str((old/n).relative_to(R)),sha256=sha(H/n))
 # Locate old input originals from sealed protocols rather than re-counting copies.
 catalog=[];protocols=[]
 p=old/'protocol.json';protocols.append(p)
 for c in read(p)['cases']:catalog.append(dict(collection='LAST60',batch=c['batch'],name=c['name'],path=str((R/c['source']).resolve())))
 for folder,collection in [('PPCPP结构候选新开发验证_v0.1_20261020','STRUCT_new36'),('PPCPP两窗口结构候选_v0.1_20261020','timing_original20_controlled27')]:
  p=R/folder/'protocol.json';protocols.append(p)
  for c in read(p)['cases']:catalog.append(dict(collection=collection,batch=c['batch'],name=c['case_id'],path=str(Path(c['input']).resolve())))
 unique={}
 for c in catalog:
  path=Path(c['path']);c['sha256']=sha(path);unique.setdefault(str(path),c)
 save(H/'old_input_catalog.json',dict(records=catalog,unique_source_paths=len(unique),unique_byte_inputs=len({c['sha256'] for c in catalog})))
 paths=[p for p in H.glob('*.py')]+[old/n for n in reused]+[H/'预登记.md',H/'几何坐标表.json',H/'几何概览.md',H/'old_input_catalog.json']+protocols+[Path(c['path']) for c in catalog]
 prior=read(old/'protocol.json')
 paths += [R/p for p in prior['files'] if p.endswith('.py')]
 paths += [old/'source_seal.json',old/'gate_index.json',old/'gate_exact_bounds.json',old/'manifest.json',R/'PPCPP结束位置跨几何验证_v0.1_20261020/equivalence.py',R/'实验结论与PPCPP改进讨论_20261020/交给6.1sol_LAST固定实现新开发地图验证执行稿_v1_20261020.md']
 save(H/'protocol.json',dict(version='v0.1_20261020',slots=slots,definitions=defs,reused=reused,files={str(p.relative_to(R)):sha(p) for p in sorted(set(paths))},budget=20,watchdog=90,repetitions=[0,1,2,3,4],max_calls=dict(prep=9,gates=108,formal=540),ordering='repetition, slot in fixed protocol order, rotate PPCPP/LAST by slot_index+repetition',read_scope='unchanged worker; planning reads only unique input, imported modules logged',environment=dict(python=sys.version,executable=sys.executable,platform=platform.platform()),stop_rule='fixed matrix only; cross-shape preservation requires >=2 families with non-old-copy non-D4-equivalent improved geometries'))
 print('before-call protocol fixed',sha(H/'protocol.json'),'slots',len(slots),'old records',len(catalog),'unique paths',len(unique),flush=True)
if __name__=='__main__':main()
