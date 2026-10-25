from common import *
def main():
 assert not (H/'原生与直达变化澄清.json').exists()
 v=read(H/'216视图完整指标.json');ix={(x['case'],x['seed'],x['branch'],x['env'],x['view']):x for x in v};out=[]
 for c in read(H/'selection.json')['selected']:
  for seed in read(H/'plan.json')['seeds']:
   record={'case':c['id'],'seed':seed}
   for branch in ('B','R','C'):
    for view in ('raw','post'):
     n,e=(ix[(c['id'],seed,branch,env,view)]['metrics']['length'] for env in ('N','E'))
     record[branch+'_'+view+'_N']=n;record[branch+'_'+view+'_E']=e;record[branch+'_'+view+'_delta']=e-n
   assert record['B_raw_delta']==0 and record['R_raw_delta']==2
   out.append(record)
 dump(H/'原生与直达变化澄清.json',{'pairs':out,'B_raw_delta_all':0,'R_raw_delta_all':2,'B_post_delta_range':[min(x['B_post_delta'] for x in out),max(x['B_post_delta'] for x in out)],'no_new_planning_geometry_or_BFS':True,'explanation':'The replan B changes its unit-grid return walk without increasing its edge count. R retains valid old fragments, so its local patch adds two raw edges; common postprocessing yields identical B_E/R_E routes. Raw edge counts are not Euclidean shortcut lengths.'})
 p=H/'00_通俗成对诊断报告.md';first=H/'report_export_v0.1/00_通俗成对诊断报告_原生步数草稿.md';first.parent.mkdir(exist_ok=True);first.write_bytes(p.read_bytes())
 s=p.read_text(encoding='utf-8');bad='原生四邻接路线均比N多2步；共同直达后的增程如表，不能把原生2步当作最终欧氏增程。'
 assert bad in s
 s=s.replace(bad,'B重新规划的原生四邻接边数18组均与N相同，只换了返航格路；R因保留旧有效片段，原始修复路线比R_N多2步。共同直达后的B与R增程如表，原生格路边数与最终欧氏距离必须分开，见原生与直达变化澄清.json。')
 s=s.replace('# 旧计划真实受阻后，PPCPP＋直达发生了什么','# 旧计划真实受阻后，PPCPP＋直达发生了什么\n\n报告导出v0.2；首个草稿把R的原生+2步误写成B，保存于report_export_v0.1，已仅据保存指标纠正，未重跑算法。')
 p.write_text(s,encoding='utf-8')
 p=H/'03_时间转弯与阶段解释.md'
 with p.open('a',encoding='utf-8') as f:f.write('\n补充原生/直达区分：B原生N/E边数差18组均为0，返航格路改变；R原生边数差均为+2。共同直达后B_E与R_E逐点相同，不能把R局部修复的+2原生步数写成B增量。见原生与直达变化澄清.json。主报告首草稿的这一导出错误原样保留，报告v0.2纠正，不涉及任何实验/核心/几何重跑。\n')
 dump(H/'报告导出修正记录.json',{'version':'report v0.2','preserved_first_draft':str(first.relative_to(H)),'issue':'draft misattributed R raw +2 edges to B; complete saved metrics show B raw delta 0, R raw delta +2 for all18','resolution':'saved-data-only correction and explicit raw/post distinction; no solver or geometry replay','new_processing_core_R_post_geometry_BFS':0})
 print({'B_raw_delta':0,'R_raw_delta':2,'saved_pairs':18,'new_solver_geometry':0})
if __name__=='__main__':main()
