"""Event-only descriptive heatmap from independently verified saved results."""
from pathlib import Path
import hashlib,json
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent
ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
OUT=ALGO/'range_diagnostics/verification_v0.1_20261015'
def main():
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    assert read(OUT/'summary.json')['status']=='independently_verified_bounded_road_range_diagnostic'
    dest=OUT/'event_range_vs_P2.png';assert not dest.exists()
    rows=read(OUT/'logical_ledger.json');lookup={(r['case'],r['budget'],r['method']):r for r in rows}
    ids=list(dict.fromkeys(r['case'] for r in rows if r['role']=='event'));assert len(ids)==10
    methods=('R_SEED','R_PLUS1','R_PLUS2','R_ALL');labels=('初始范围','扩一层','扩两层','全部放开')
    im=Image.new('RGB',(1560,940),'#f5f7fa');d=ImageDraw.Draw(im)
    font=lambda s:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',s)
    d.text((26,16),'道路开发诊断：固定范围的完整路程相对强P2',fill='#14263d',font=font(30))
    d.text((26,61),'每格为 范围步数 / P2步数 − 1；蓝色较短，红色较长；F表示最终选择共同保底。',fill='#52677f',font=font(21))
    for bi,budget in enumerate((1,20)):
        left=285+bi*620
        d.text((left+205,101),f'{budget}秒总预算',fill='#14263d',font=font(24))
        for mi,label in enumerate(labels):d.text((left+mi*150+20,142),label,fill='#344c67',font=font(19))
    for i,sid in enumerate(ids):
        y=183+i*56;ref=lookup[sid,1,'P2_MULTI']
        d.text((26,y+4),ref['map_id'].replace('_development',''),fill='#344c67',font=font(19))
        d.text((26,y+27),ref['event'],fill='#63798f',font=font(15))
        for bi,budget in enumerate((1,20)):
            base=lookup[sid,budget,'P2_MULTI'];left=285+bi*620
            for mi,m in enumerate(methods):
                r=lookup[sid,budget,m];x=left+mi*150
                v=(r['metrics']['steps']/base['metrics']['steps']-1)*100 if r['valid'] and base['valid'] and base['metrics']['steps'] else None
                score=min(abs(v or 0)/25,1)
                end=(196,219,244) if v is not None and v<0 else (246,198,194) if v is not None and v>0 else (232,236,241)
                color=tuple(round(248+(z-248)*score) for z in end) if v else end
                d.rounded_rectangle((x,y,x+143,y+49),radius=5,fill=color)
                text='失败/缺失' if v is None else f'{v:+.2f}%' + (' F' if r['fallback_selected'] else '')
                d.text((x+10,y+12),text,fill='#203b56',font=font(20))
    d.text((26,783),'10个事件状态来自原12张开发地图；12个同历史无变化对照另行统计。一个配对种子。',fill='#52677f',font=font(21))
    d.text((26,826),'相同切口的范围共享一次执行；不是额外独立样本。此图不展示事后最佳范围为在线算法。',fill='#52677f',font=font(21))
    d.text((26,869),'全部方法均需覆盖当前可检目标并返航；范围判断、保底、搜索及候选拼接计入总预算。',fill='#52677f',font=font(21))
    im.save(dest)
    with (OUT/'figure_sha256.json').open('x',encoding='utf-8') as f:
        json.dump({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),dest)},f,ensure_ascii=False,indent=2)
    print(dest)
if __name__=='__main__':main()
