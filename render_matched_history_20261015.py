"""Static descriptive figure from independently verified statistics; no solving."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parent
ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
SOURCE=ALGO/'development_preflights/matched_history_v2_20261015_verification'
OUT=SOURCE/'ppcpp_relative_quality.png'

def main():
    assert not OUT.exists()
    assert json.loads((SOURCE/'summary.json').read_text(encoding='utf-8'))['status']=='verified_matched_development'
    pairs=json.loads((SOURCE/'paired_comparisons.json').read_text(encoding='utf-8'))
    variants=('H25','H50','H75','V50','new_states');comparators=('P2_MULTI','OARP_CORE2','TREE_MST')
    values={}
    for row in pairs:
        if row['b']=='PPCPP_CORE4' and row['a'] in comparators and row['subset'] in variants:
            # Reverse each saved per-state ratio, then average within map and between maps.
            # Negating the aggregate inverse ratio would not be mathematically equivalent.
            by_map={}
            for s in row['per_state']:
                v=s['relative_difference']
                if v is not None:by_map.setdefault(s['map_id'],[]).append(1/(1+v)-1)
            values[row['subset'],row['budget'],row['a']]=100*sum(sum(v)/len(v) for v in by_map.values())/len(by_map)
    W,H=1500,825;im=Image.new('RGB',(W,H),'#f6f8fb');d=ImageDraw.Draw(im)
    font=lambda n:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n)
    title,body,small=font(32),font(22),font(18)
    d.text((35,20),'固定事件开发检查：PPCPP的相对路程差',fill='#18283f',font=title)
    d.text((35,72),'负值：PPCPP更短；正值：对照更短。先图内等权，再12张开发地图等权。',fill='#43536b',font=body)
    colors={1:'#2375c9',20:'#d45819'}
    for i,b in enumerate((1,20)):
        x=1020+i*190;d.ellipse((x,28,x+16,44),fill=colors[b]);d.text((x+25,22),f'{b}秒预算',fill=colors[b],font=body)
    bound=max(10,5*((int(max(abs(v) for v in values.values()))+4)//5))
    for pi,comp in enumerate(comparators):
        left=35+pi*490;right=left+460;top=125;bottom=655
        d.rounded_rectangle((left,top,right,bottom),radius=12,fill='white',outline='#d7dfe9',width=2)
        d.text((left+20,top+18),'对照 '+comp,fill='#18283f',font=body)
        x0=left+130;x1=right-32;center=(x0+x1)/2;span=(x1-x0)/2
        for tick in (-bound,0,bound):
            x=center+tick/bound*span
            d.line((x,top+76,x,bottom-55),fill='#bac6d5' if tick==0 else '#e8edf4',width=2 if tick==0 else 1)
            label=f'{tick:+g}%' if tick else '0%';d.text((x-24,bottom-41),label,fill='#63738a',font=small)
        for vi,variant in enumerate(variants):
            y=top+110+vi*80
            label='新状态均值' if variant=='new_states' else variant
            d.text((left+17,y-14),label,fill='#34475f',font=small)
            for budget,offset in ((1,-13),(20,13)):
                v=values[variant,budget,comp];x=center+v/bound*span;yy=y+offset
                d.line((center,yy,x,yy),fill=colors[budget],width=3)
                d.ellipse((x-5,yy-5,x+5,yy+5),fill=colors[budget])
                d.text((center+4,yy-21),f'{v:+.2f}%',fill=colors[budget],font=small)
    d.text((35,687),'H/V：横/纵原始覆盖历史；25/50/75：旧目标覆盖进度。新状态均值＝H25、H75、V50。',fill='#43536b',font=body)
    d.text((35,727),'H50曾参与PPCPP调参；其他状态仍来自同批地图。每方法/状态/预算仅一次，不是独立测试。',fill='#43536b',font=body)
    d.text((35,767),'仅比较合法完成并返航的实际移动步数；无显著性推断，不代表真实能耗。',fill='#63738a',font=small)
    im.save(OUT)
    (SOURCE/'figure_metadata.json').write_text(json.dumps(dict(renderer=str(Path(__file__)),
        statistic='mean across maps of within-map mean (PPCPP_steps/comparator_steps - 1)',
        unit='percent',no_solver_calls=True,values=[dict(subset=k[0],budget=k[1],comparator=k[2],percent=v)
        for k,v in values.items()]),ensure_ascii=False,indent=2),encoding='utf-8')
    print(OUT)

if __name__=='__main__':main()
