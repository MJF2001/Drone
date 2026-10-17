"""Offline figure and exact saved-reference input replay; no planner calls."""
from pathlib import Path
import copy,hashlib,json
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent
BASE=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/old_plan_quality_diagnostics'
RUN=BASE/'run_v0.1_20261016';VERIFY=BASE/'verification_v0.1_20261016';REPLAY=BASE/'inputs_saved_reference_replay_v0.1_20261016'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,o):
    with p.open('x',encoding='utf-8') as f:json.dump(o,f,ensure_ascii=False,indent=2)
assert read(VERIFY/'summary.json')['status']=='independently_verified'
assert all(sha(RUN/n)==h for n,h in read(RUN/'sha256.json').items())
REPLAY.mkdir(parents=True,exist_ok=False);checks=[]
for i,e in enumerate(read(RUN/'reference_ledger.json')):
    original=read(Path(e['source_case']));strong=copy.deepcopy(original)
    strong['old_route']=read(RUN/'runs'/(e['preparation_run_id']+'.json'))['raw']['route']
    assert all(strong[k]==original[k] for k in original if k!='old_route')
    for ref,c in [('RAW',original),('P2_REF',strong)]:
        p=REPLAY/f'c{i:02d}_{ref}.json';write(p,c);expected=sha(RUN/'inputs'/p.name);assert sha(p)==expected
        checks.append(dict(file=p.name,sha256=expected))
write(REPLAY/'completion.json',dict(valid=True,identical_input_files=24,checks=checks,
    solver_called=False,reference_source='Saved preparation routes, not repeat limited-time optimization',holdout_used=False))
write(REPLAY/'sha256.json',{p.name:sha(p) for p in REPLAY.iterdir() if p.is_file()})
paired=read(VERIFY/'paired_summary.json');rows=paired[0]['per_map'];lookup={(s['budget'],s['reference']):{v['map_id']:v for v in s['per_map']} for s in paired}
im=Image.new('RGB',(1200,910),'white');d=ImageDraw.Draw(im)
font='C:/Windows/Fonts/msyh.ttc';f=lambda n:ImageFont.truetype(font,n)
d.text((45,25),'旧计划质量敏感性检查',font=f(32),fill='#111111')
d.text((45,75),'12个无变化开发状态  同组KEEP相对P2的路程差',font=f(23),fill='#333333')
columns=[(1,'RAW'),(1,'P2_REF'),(20,'RAW'),(20,'P2_REF')];x0=350;cw=195;y0=145;rh=48
d.text((45,155),'基础地图',font=f(23),fill='#111111')
for j,(b,ref) in enumerate(columns):
    d.rectangle((x0+j*cw,y0,x0+(j+1)*cw,y0+rh),fill='#e5edf5',outline='#c0c8d0')
    label=f'{b}秒 '+('原扫描' if ref=='RAW' else '优化参考')
    d.text((x0+j*cw+16,y0+10),label,font=f(22),fill='#111111')
for i,row in enumerate(rows):
    y=y0+(i+1)*rh;name=row['map_id'].replace('_development','')
    d.text((45,y+10),name,font=f(22),fill='#111111')
    for j,key in enumerate(columns):
        v=lookup[key][row['map_id']];r=v['relative'];a=min(abs(r)/.5,1)
        col=(255,int(255-90*a),int(255-90*a)) if r>=0 else (int(255-90*a),int(255-50*a),255)
        d.rectangle((x0+j*cw,y,x0+(j+1)*cw,y+rh),fill=col,outline='#d9d9d9')
        label=f"{r:+.1%}  ({v['difference']:+d})"
        d.text((x0+j*cw+13,y+12),label,font=f(19),fill='#222222')
d.text((45,800),'正值表示保留更长  括号为步差  红色越深表示损失越大',font=f(21),fill='#333333')
d.text((45,843),'优化参考另有20秒准备额度  本图不是跨参考的同总预算排名',font=f(22),fill='#8a3030')
im.save(VERIFY/'old_plan_quality_gap.png')
preflight=BASE/'preflight_v0.1_20261016/unit_tests.log'
(VERIFY/'unit_tests.log').write_bytes(preflight.read_bytes())
write(VERIFY/'supplementary_record.json',dict(input_replay=str(REPLAY),identical_files=24,solver_called=False,
    finalize_source_sha256=sha(Path(__file__)),preflight_log_sha256=sha(preflight)))
write(VERIFY/'supplement_sha256.json',{p.name:sha(p) for p in VERIFY.iterdir() if p.is_file() and p.name not in ('sha256.json','supplement_sha256.json')})
print('PASS: 24 saved-reference inputs replay identically; figure and supplementary manifest saved; no solve')
