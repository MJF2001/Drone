from common import *
from collections import Counter
import sys,json,math
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,str(ROOT/'中心区PPCPP直达质量时间开发比较_v0.1_20261022'))
from center_bench_v01_20261022.exact import Expr,certificate
def main():
 assert not (H/'行为补充与阶段分解.json').exists()
 selection=read(H/'selection.json')['selected'];pairs=read(H/'同状态同seed六分支配对.json');analysis=read(H/'PPCPP行为与返航差异.json');summary=read(H/'summary.json');stage=[]
 for a,p in zip(analysis,pairs):
  ss={k:Expr.load(a['B_stages_E'][k]['exact'])-Expr.load(a['B_stages_N'][k]['exact']) for k in ('to_first_witness','between_first_last_witness','after_last_witness_return')}
  full=Expr.load(p['B_E_minus_B_N']['certificate']['exact']);assert ss['to_first_witness'].sign()==ss['between_first_last_witness'].sign()==0 and (ss['after_last_witness_return']-full).sign()==0
  stage.append({'case':a['case'],'seed':a['seed'],'delta_stages':{k:certificate(v) for k,v in ss.items()},'all_delta_in_saved_after_last_witness_stage':True,'full_trace_equal':a['B_N_E_first_full_trace_difference'] is None,'same_B_R_raw_E':a['B_vs_R_E_same_raw_route'],'turn_delta':p['B_turn_delta'],'old_block_position':'last native return leg near base, obstacle [0,1]','interpretation':'path observations and exact witness convention decomposition; not a necessary-cost lower bound or removable-cost certificate'})
 extra={'pairs':stage,'all18_full_trace_equal':all(x['full_trace_equal'] for x in stage),'same_B_R_raw_E':sum(x['same_B_R_raw_E'] for x in stage),'all18_delta_only_saved_return_stage':True,'all18_turn_delta':dict(Counter(k+':'+str(v) for p in pairs for k,v in p['B_turn_delta'].items())),'all18_B_R_time_delta_mean':sum(p['BE_time']-p['RE_time'] for p in pairs)/len(pairs),'all18_B_R_time_delta_range':[min(p['BE_time']-p['RE_time'] for p in pairs),max(p['BE_time']-p['RE_time'] for p in pairs)]}
 dump(H/'行为补充与阶段分解.json',extra)
 txt=['# 计算时间与完整行为摘录','', '所有秒数为本批保存计时；单次测量不是硬件稳定速度或纯算法理论耗时。P95采用最近秩。R种子重复只表示同一路线的重复计时。','', '|分支/环境（18次）|原生/修复均值s|共同端到端均值s|中位s|P95 s|最大s|post增量均值s|独立审核均值s|进程内墙钟均值s|','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for k,v in summary['timing'].items():txt.append('|'+k+'|'+ '|'.join(f'{z:.9f}' for z in [v['native_entry_seconds']['mean'],v['combined_end_to_end']['mean'],v['combined_end_to_end']['median'],v['combined_end_to_end']['P95'],v['combined_end_to_end']['max'],v['post_increment']['mean'],v['independent_wall_seconds']['mean'],v['worker_wall_seconds']['mean']])+'|')
 txt+=['', '|状态/seed|总转弯Δ|90°Δ|180°Δ|其他Δ|完整B trace相同|所有增量在保存返航阶段|','|---|---:|---:|---:|---:|---|---|']
 for p,a in zip(pairs,stage):txt.append('|'+p['case']+'/'+str(p['seed'])+'|'+ '|'.join(str(p['B_turn_delta'][k]) for k in ('total','90','180','other'))+'|'+str(a['full_trace_equal'])+'|True|')
 txt+=['','全部216视图含原/直达距离、各类转弯、有效/公开覆盖分母、初始H/暂缓D、新信用、返航/预算、无新信用整段长度和触达事件，保存于216视图完整指标.json。108入口计时.csv另列冷导入/独立/落盘扣除及各迟到标志，主报告不靠单个均值掩盖最坏情况。','',f"B_E−B_N端到端时间：均值{summary['B_time_delta_pairs']['mean']:.9f}s，中位{summary['B_time_delta_pairs']['median']:.9f}s，P95/最大{summary['B_time_delta_pairs']['P95']:.9f}s，最小{summary['B_time_delta_pairs']['min']:.9f}s。R_E与B_E逐点相同18/18，不是不同路线的优化对照；B_E−R_E均值{extra['all18_B_R_time_delta_mean']:.9f}s，范围{extra['all18_B_R_time_delta_range']}。不得仅因R快就把诊断工具宣布为改进算法。",'', '18组B完整trace、名义锚点和信用见证顺序均相同，至最后名义锚点的直达前缀逐点相同；阶段根式差恰等于保存after_last_witness_return阶段差，前两段差精确0。这里的内部见证约定可能包含最后服务段后半段，不是唯一物理首次入区时刻；相等证书不证明这些返航增量不可避免。P2在N已更短，E仍更短，不能把该差距全部归于新障碍或自动推出需要重排。']
 (H/'03_时间转弯与阶段解释.md').write_text('\n'.join(txt)+'\n',encoding='utf-8')
 font=lambda n:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n)
 for c in selection:
  im=Image.new('RGB',(1440,1060),'white');d=ImageDraw.Draw(im);d.text((25,18),c['id']+' / 固定首seed 20261020：N/E × B/R/C',font=font(23),fill='#13263c');d.text((25,56),'灰细线=原生/修复完整路线；彩线=共同直达；橙格=新障碍；灰点=H，蓝点=未采任务',font=font(17),fill='#34445a')
  for row,env in enumerate(('N','E')):
   for col,b in enumerate(('B','R','C')):
    ident=f"formal__{c['id']}__20261020__{b}__{env}";x=read(H/'outputs'/(ident+'.json'));inp=x['input'];v=x['views']['C' if b=='C' else 'B'];raw=x['native']['raw']['route'];F=ps(inp['free']);P=ps(inp['published_targets']);Hh=ps(inp['covered']);xmin=min(p[0] for p in F);xmax=max(p[0] for p in F);ymin=min(p[1] for p in F);ymax=max(p[1] for p in F);scale=min(400/(xmax-xmin+1),290/(ymax-ymin+1));ox=col*480+35;oy=row*445+135
    def pt(p):return ox+(p[0]-xmin+.5)*scale,oy+310-(p[1]-ymin+.5)*scale
    d.text((ox,oy-32),env+' / '+b+{'B':' PPCPP','R':' 保序修复','C':' P2'}[b],font=font(21),fill='#172b45')
    for q in F:
     a=pt((q[0]-.5,q[1]+.5));z=pt((q[0]+.5,q[1]-.5));d.rectangle((*a,*z),fill='#f1f4f7',outline='#e1e6ed',width=1)
    if env=='E':
     for q in c['obstacles']:
      a=pt((q[0]-.5,q[1]+.5));z=pt((q[0]+.5,q[1]-.5));d.rectangle((*a,*z),fill='#f08035')
    for q in P:
     xx,yy=pt(q);d.ellipse((xx-2,yy-2,xx+2,yy+2),fill='#a1a5aa' if q in Hh else '#6e9bc4')
    d.line([pt(p) for p in raw],fill='#9fa7b3',width=1);color={'B':'#185bb6','R':'#6b52aa','C':'#148370'}[b];d.line([pt(p) for p in v['path']],fill=color,width=2)
    for key,fill in [('current','#ce3543'),('base','#13263c')]:
     xx,yy=pt(inp[key]);d.ellipse((xx-4,yy-4,xx+4,yy+4),fill=fill)
    d.text((ox,oy+330),f"距离 {v['metrics']['length']:.6f} m / 总时 {x['timing']['combined_end_to_end']:.6f} s",font=font(17),fill='#172b45')
    d.text((ox,oy+357),f"新增信用 {v['metrics']['new_credit']} / 未完成 {v['metrics']['missing']} / 已返航",font=font(16),fill='#172b45')
  d.text((25,1010),'旧计划受阻成立；图仅画已保存路线。等长、必要绕行与顺序原因须结合精确配对及原trace判断。',font=font(19),fill='#172b45');im.save(H/'figures'/(c['id']+'.png'))
 # Explicit return-only picture from saved suffixes, with independent panels.
 im=Image.new('RGB',(1440,970),'white');d=ImageDraw.Draw(im);d.text((25,18),'B：至末锚点前缀相同，变化集中返航（固定首seed；六例均阻断[0,1]）',font=font(24),fill='#172b45');d.text((25,56),'蓝=N返航，橙=E返航；红块=新增闭障碍格；R_E与B_E逐点相同。此图不是返航最优性证明。',font=font(18),fill='#34445a')
 for idx,c in enumerate(selection):
  a=next(a for a in analysis if a['case']==c['id'] and a['seed']==20261020);xx=[a['B_N_return_suffix'],a['B_E_return_suffix']];xmax=max(p[0] for path in xx for p in path);ymax=max(p[1] for path in xx for p in path);scale=min(300/(xmax+1),290/(ymax+1));ox=(idx%3)*480+70;oy=(idx//3)*420+150
  def pt(p):return ox+(p[0]+.5)*scale,oy+280-(p[1]+.5)*scale
  d.text((idx%3*480+25,oy-45),c['base_id']+' / B返航',font=font(23),fill='#172b45')
  for x in range(xmax+1):
   for y in range(ymax+1):
    aa=pt((x-.5,y+.5));zz=pt((x+.5,y-.5));d.rectangle((*aa,*zz),fill='#f1f4f7',outline='#dce3eb')
  aa=pt((-.5,1.5));zz=pt((.5,.5));d.rectangle((*aa,*zz),fill='#ef7a59')
  for path,color,width in [(xx[0],'#185bb6',4),(xx[1],'#dc9225',3)]:d.line([pt(p) for p in path],fill=color,width=width)
  bx,by=pt((0,0));d.ellipse((bx-5,by-5,bx+5,by+5),fill='#172b45');d.text((ox,oy+305),'同一基地[0,0]；完整信用/返航均合格',font=font(16),fill='#172b45')
 im.save(H/'figures/六例返航端放大.png')
 print(json.dumps({'full_trace_equal':extra['all18_full_trace_equal'],'same_B_R_raw_E':extra['same_B_R_raw_E'],'R_B_mean_time_difference':extra['all18_B_R_time_delta_mean'],'figures':7,'new_core_R_post_geometry_BFS':0},ensure_ascii=False))
if __name__=='__main__':main()
