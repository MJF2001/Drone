from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parent.parent
OLD='31_导师汇报稿_剩余覆盖路径重规划研究进展_20261011'
NEW='32_导师汇报稿_图示精简版_剩余覆盖路径重规划_20261011'
FOLDER=Path(__file__).resolve().parent
font=lambda size:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',size)

def diagram():
    im=Image.new('RGB',(1800,650),'white');d=ImageDraw.Draw(im)
    colors={'covered':'#D5E7D6','pending':'#F3F4F6','new':'#CFE2F5','obstacle':'#C76A63'}
    old={(x,y) for x in range(7) for y in range(1,4)}
    added={(x,y) for x in range(7,10) for y in range(2,4)}|{(9,4)}
    done={(x,1) for x in range(5)}
    route=[(4,1),(5,1),(6,1),(6,2)]+[(x,2) for x in range(5,-1,-1)]+[(0,3)]+[(x,3) for x in range(1,7)]
    def dashed(a,b):
        import math
        length=math.dist(a,b)
        for q in range(0,int(length),18):
            e=min(q+10,length)
            d.line((a[0]+(b[0]-a[0])*q/length,a[1]+(b[1]-a[1])*q/length,a[0]+(b[0]-a[0])*e/length,a[1]+(b[1]-a[1])*e/length),fill='#77828E',width=4)
    for panel,title in enumerate(['事件一  待检区域扩展','事件二  新发现障碍']):
        ox=90+panel*900;oy=100;cell=62
        d.text((ox,12),title,font=font(37),fill='#111111')
        def xy(p):return (ox+p[0]*cell+cell/2,oy+(4-p[1])*cell+cell/2)
        for x in range(10):
            for y in range(5):
                p=x,y;a=ox+x*cell;b=oy+(4-y)*cell
                fill=colors['covered'] if p in done else colors['pending'] if p in old else colors['new'] if panel==0 and p in added else 'white'
                d.rectangle((a,b,a+cell,b+cell),fill=fill,outline='#B8C0C7',width=2)
        for a,b in zip(route,route[1:]):dashed(xy(a),xy(b))
        if panel==1:
            a=ox+6*cell;b=oy+2*cell
            d.rectangle((a+2,b+2,a+cell-2,b+cell-2),fill=colors['obstacle'])
            d.line((a+17,b+17,a+cell-17,b+cell-17),fill='white',width=5)
            d.line((a+17,b+cell-17,a+cell-17,b+17),fill='white',width=5)
        cx,cy=xy((4,1));d.ellipse((cx-16,cy-16,cx+16,cy+16),fill='#1E527C',outline='white',width=3)
        bx,by=xy((0,1));d.rectangle((bx-10,by-10,bx+10,by+10),fill='#111111')
        d.text((ox,435),'原路线未包含新增待检部分' if panel==0 else '原路线连接受阻  需更新后续路线',font=font(32),fill='#222222')
    legend=[('covered','已覆盖'),('pending','剩余待检'),('new','新增待检'),('obstacle','新障碍')]
    for i,(key,label) in enumerate(legend):
        x=85+i*315;d.rectangle((x,525,x+35,560),fill=colors[key],outline='#AAB3BC')
        d.text((x+48,522),label,font=font(31),fill='#222222')
    d.ellipse((1350,530,1376,556),fill='#1E527C');d.text((1390,522),'当前位置',font=font(31),fill='#222222')
    d.line((85,609,160,609),fill='#77828E',width=4);d.text((178,587),'灰色虚线为原剩余路线',font=font(30),fill='#444444')
    d.rectangle((770,596,792,618),fill='#111111');d.text((810,587),'基地',font=font(30),fill='#444444')
    # Actual dashed line sample for consistency with the map.
    d.rectangle((85,603,160,615),fill='white')
    for x in range(85,160,18):d.line((x,609,min(x+10,160),609),fill='#77828E',width=4)
    im.save(FOLDER/'events_schematic.png')

text=(ROOT/(OLD+'.md')).read_text(encoding='utf-8')
start=text.index('本阶段围绕');end=text.index('## 二 主要参考文献')
opening='''本研究关注施工待检区域扩展或新发现障碍后的无人机剩余覆盖路径重规划。目标是保留已完成覆盖记录，从当前位置更新后续路线，降低剩余巡检与返航的移动代价。本文汇报研究范围、文献依据及阶段性实验结果。

## 一 研究问题与研究范围

### 1 环境变化与重规划问题

已知静态区域可采用往返扫描完成覆盖。本课题关注执行过程中出现的两类变化，如图1所示。

![两类环境变化](events_schematic.png)

图1 两类环境变化及原剩余路线示意

**核心问题**：待检区域扩展或新发现障碍后，如何利用已有覆盖进度，从当前位置更新剩余路线，减少重复移动与绕行？

局部航段最短不保证整条覆盖路线最短。因此，除修复受阻连接外，还需检验剩余目标的访问顺序和覆盖组织方式。

### 2 研究边界与模型假设

| 项目 | 本阶段设定 |
|---|---|
| 研究对象 | 单无人机剩余覆盖路径重规划 |
| 环境变化 | 待检区域扩展与新发现障碍 |
| 主要目标 | 完成剩余可执行覆盖并返航的移动步数 |
| 同时评价 | 计算时间与路线可行性 |
| 暂不涉及 | 视觉识别 飞控 多机协同与复杂任务调度 |

**运动与采集**：采用二维四邻接栅格，每移动一格计一步，仅采集正下方一格。当前位置与已覆盖区域来自事件前实际执行轨迹。

**障碍与目标**：障碍禁止飞入并遮挡路面。被遮挡的未完成目标保留为暂缓任务，不计为完成。各方法接收相同的当前信息，不获取未来事件。

**适用范围**：当前主要测试固定飞行域内的待检区域扩展，以及单次信息更新后的规划。连续多事件和飞行域本身扩展尚未全面验证；步数与资源上限尚未标定为真实电量。

研究不以新增路面必须立即检查为前提，重点评价路径代价与计算开销。

'''
text=text[:start]+opening+text[end:]
# Literature remains explanatory prose, but each paragraph has one explicit role.
replacements={
'OARP-Replan研究已有覆盖路线':'**研究对象**：OARP-Replan研究已有覆盖路线',
'该方法利用已有路线':'**核心方法**：该方法利用已有路线',
'与本课题的差异在于，该文':'**适用差异**：该文',
'TRACE面向未知静态环境':'**研究对象**：TRACE面向未知静态环境',
'其局部规划结合往返扫描':'**核心方法**：其局部规划结合往返扫描',
'该文对本课题的主要启示是':'**借鉴与边界**：该文对本课题的主要启示是',
'C*面向未知环境':'**核心方法**：C*面向未知环境',
'该方法说明覆盖规划不仅':'**借鉴与边界**：该方法说明覆盖规划不仅',
'P2中的2-opt通过':'**P2的优化方式**：P2中的2-opt通过',
'P2_SHARED在原P2基础上':'\n\n**共同保底机制**：P2_SHARED在原P2基础上',
'GLNS即广义大邻域搜索':'\n\n**条带排序工具**：GLNS即广义大邻域搜索',
'OARP核心适配已实现':'**复现范围**：OARP核心适配已实现',
'尚未复现原论文完整的持续运动':'\n\n尚未复现原论文完整的持续运动',
'部分快照共享初始历史':'\n\n部分快照共享初始历史',
'无合法路线的执行按失败保留':'\n\n无合法路线的执行按失败保留',
'部分方法使用C++求解器':'\n\n部分方法使用C++求解器',
'后续固定条带、拆分旧段约束时':'\n\n后续固定条带、拆分旧段约束时',
'短预算下，优化使程序':'\n\n短预算下，优化使程序',
'优化后仍存在短预算损失':'\n\n优化后仍存在短预算损失',
'当前P2在微型开发场景':'**当前证据**：当前P2在微型开发场景',
'常规实现优化能够显著改变':'\n\n**研究判断**：常规实现优化能够显著改变',
'上述判断以当前人工场景':'**适用限制**：上述判断以当前人工场景',
}
for a,b in replacements.items():text=text.replace(a,b)
# Keep implementation names out of the visual summaries when not needed.
text=text.replace('首先，冻结合理优化','**第一步 统一基线并开展新场景复核**\n\n冻结合理优化')
text=text.replace('其次，若仍有明确缺口','**第二步 针对稳定缺口设计候选方法**\n\n若仍有明确缺口')
text=text.replace('再次，在候选方法具有稳定收益后','**第三步 验证连续多事件与机制贡献**\n\n在候选方法具有稳定收益后')
text=text.replace('最后，对候选贡献开展','**第四步 完成独立测试与相关工作核查**\n\n对候选贡献开展')
text=text.replace('<!-- pagebreak -->','')
(ROOT/(NEW+'.md')).write_text(text,encoding='utf-8')
diagram()
builder=(FOLDER/'build_report.py').read_text(encoding='utf-8').replace(OLD,NEW)
builder=builder.replace("count=len(data[0]);widths={3:","count=len(data[0]);widths={2:[1.35,5.45],3:")
builder=builder.replace("p.alignment=WD_ALIGN_PARAGRAPH.LEFT if (count==3 and j<2)","p.alignment=WD_ALIGN_PARAGRAPH.LEFT if count==2 or (count==3 and j<2)")
builder=builder.replace("if line.startswith('|'):","if line.startswith('!['):\n        p=doc.add_paragraph();p.paragraph_format.first_line_indent=Pt(0);p.paragraph_format.keep_with_next=True\n        p.add_run().add_picture(str(Path(__file__).resolve().parent/'events_schematic.png'),width=Inches(6.8))\n        continue\n    if line.startswith('|'):")
builder=builder.replace("p=doc.add_paragraph(line);p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY","p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY\n        import re\n        for fragment in re.split(r'(\\*\\*.*?\\*\\*)',line):\n            r=p.add_run(fragment[2:-2] if fragment.startswith('**') else fragment);r.bold=fragment.startswith('**')\n        if line.startswith('图1 '):\n            p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.first_line_indent=Pt(0)\n            for r in p.runs:r.font.size=Pt(10.5)\n        if line.startswith('**'):\n            p.paragraph_format.first_line_indent=Pt(0)\n        if line.startswith('**第') and line.endswith('**'):\n            p.paragraph_format.keep_with_next=True")
(FOLDER/'build_visual_report.py').write_text(builder,encoding='utf-8')
print(ROOT/(NEW+'.md'))
