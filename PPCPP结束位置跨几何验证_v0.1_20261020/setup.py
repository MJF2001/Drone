from common import *
from spec import *
import platform,sys
def ascii_map(f,t,b=set()):
 return '\n'.join(''.join('X' if (x,y) in b else '#' if (x,y) in t else '.' for x in range(max(x for x,y in f)+1)) for y in range(5,-1,-1))
def main():
 assert not (H/'protocol.json').exists();slots=[];defs=[];overview=['# 生成前纯几何概览\n\n#为道路，X为障碍，.为非道路可飞。行从y=5到0，列x递增。未执行PPCPP或精确查询。']
 for p in plans():
  d=definition(p['scale'],p['family']);f,t=before(p['scale'],p['family']);assert t<=f
  defs.append(dict(**p,definition=d,free=sorted(f),initial_targets=sorted(t)))
  overview+=['## '+p['base_id']+'：事件前', '```\n'+ascii_map(f,t)+'\n```']
  for event in ('straight','corner','obstacle'):
   for progress in (25,60):
    ff,pub,b,valid=after(p['scale'],p['family'],event,(-99,-99));upper=len(pub)-(len(t)*progress+99)//100
    assert len(ff)<=48 and upper<=14 and pub<=f
    if event!='obstacle':assert pub-t and not cells(d[event+'_rectangles'])&t
    slots.append(dict(**p,event=event,progress=progress,id=f"{p['base_id']}_{event}_p{progress}",pending_upper=upper))
   if event=='obstacle':
    for q in d['obstacle_candidates']:overview+=['### '+event+' blocked='+str(q),'```\n'+ascii_map(f-{q},t,{q})+'\n```']
   else:overview+=['### '+event,'```\n'+ascii_map(ff,pub,b)+'\n```']
 (H/'几何概览.md').write_text('\n\n'.join(overview)+'\n',encoding='utf-8')
 save(H/'几何坐标表.json',defs)
 old=R/'PPCPP小图最优差距诊断_v0.2_20261020'
 for n in ('exact.py','independent.py','common.py','tests.py'):assert sha(H/n)==sha(old/n)
 paths=list(H.glob('*.py'))+[H/'预登记.md',H/'几何概览.md',H/'几何坐标表.json',R/'实验结论与PPCPP改进讨论_20261020/交给6.1sol_结束位置损失跨几何验证执行稿_v1_20261020.md']
 paths += [R/k for k in read(old/'protocol.json')['files'] if not k.startswith('PPCPP小图最优差距诊断_v0.2_20261020/')]
 paths += [old/'exact.py',old/'independent.py']+list((old/'inputs').glob('*.json'))
 save(H/'protocol.json',dict(version='v0.1_20261020',slots=slots,definitions=defs,files={str(p.relative_to(R)):sha(p) for p in sorted(set(paths))},exact_limits=dict(seconds=60,states=800000),independent_recheck_wall_seconds=60,ppcpp_budget=20,distance_budget=1000000,environment=dict(python=sys.version,executable=sys.executable,platform=platform.platform()),max_calls=dict(preparation=6,formal_ppcpp=36,formal_exact=108),repeat_criterion='E>0 in >=2 families, distinct D4 shape groups, no old full-state/shape copies; within-family repeats separately'))
 print('protocol fixed',sha(H/'protocol.json'),len(slots),flush=True)
if __name__=='__main__':main()
