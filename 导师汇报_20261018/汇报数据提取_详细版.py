"""Read saved results only; no planner imports or calls; writes this report folder."""
import collections,hashlib,json,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parent;WORK=ROOT.parent
SOURCE=WORK/'DeepSeek_底层算法开发比较_20261018'
METHODS=['P2_MULTI','TREE_MST','OARP_CORE2','PPCPP_CORE4']
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    rows=[];hashes={}
    for batch in ('BUDGET1','BUDGET20','LONG120'):
        for p in sorted((SOURCE/'runs'/batch/'results').glob('*.json')):
            d=load(p)
            if d['kind']!='development':continue
            hashes[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest();rows.append(d)
    assert len(rows)==300 and len({d['run_id'] for d in rows})==300
    summary=[];percase=[]
    for method in METHODS:
        for batch in ('BUDGET1','BUDGET20','LONG120'):
            ds=[d for d in rows if d['method_id']==method and d['batch']==batch];assert len(ds)==20
            summary.append({'method':method,'batch':batch,'n':20,'legal':sum(d['audit']['valid'] and d['resource_check']['ok'] for d in ds),
                'in_budget':sum(d['within_budget'] and d['audit']['valid'] and d['resource_check']['ok'] for d in ds),
                'fallback':sum(d['fallback_used'] for d in ds),'mean_steps_all20':statistics.mean(d['route_steps'] for d in ds),
                'median_seconds_all20':statistics.median(d['call_total_seconds'] for d in ds),
                'mean_seconds_all20':statistics.mean(d['call_total_seconds'] for d in ds)})
    cases=sorted({d['case_id'] for d in rows},key=lambda s:({'small':0,'medium':1,'large':2}[s.split('_')[0]],s))
    for case in cases:
        entry={'case':case}
        for method in METHODS:
            ds=sorted([d for d in rows if d['case_id']==case and d['method_id']==method and d['batch']=='LONG120'],key=lambda d:d['seed'])
            entry[method]={'steps':[d['route_steps'] for d in ds],'seconds':[d['call_total_seconds'] for d in ds],
                'in_budget':[d['within_budget'] for d in ds],'fallback':[d['fallback_used'] for d in ds]}
        percase.append(entry)
    assert next(s for s in summary if s['method']=='P2_MULTI' and s['batch']=='LONG120')['mean_steps_all20']==525.7
    diag=load(WORK/'OARP改进方向诊断_v0.1_20261018/analysis.json')
    assert diag['aggregate']['FULL']['sum_core_steps']==1212 and diag['aggregate']['PACKED']['sum_core_steps']==1260
    sources=[WORK/'OARP改进方向诊断_v0.1_20261018/analysis.json',WORK/'OARP改进方向诊断_v0.1_20261018/micro_analysis.json',
        WORK/'OARP原生参照修订_v0.2_20261018/summary.json',SOURCE/'reports/derived_v2/summary_v2.json',
        WORK/'DeepSeek_epsilon机制与接口集成_20261018/reports/验证结果与未闭合项.md']
    hashes.update({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    output={'development_rows':len(rows),'summary_all_samples':summary,'LONG120_percase':percase,
        'diagnostic_aggregate':diag['aggregate'],'input_sha256':hashes,'new_planner_calls':0}
    (ROOT/'汇报数据核对_详细版.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['## 附录A：120秒档逐状态步数与耗时','',
        '每格为“种子A步数/种子B步数；两次公共耗时均值（秒）”。†表示至少一次超120秒，保留路线作诊断，不计入严格预算内成绩。全部状态均为旧五方法开发比较中的共同P2执行历史，OARP指旧OARP_CORE2。','',
        '| 状态 | P2_MULTI | TREE_MST | OARP_CORE2 | PPCPP_CORE4 |','|---|---|---|---|---|']
    for r in percase:
        values=[]
        for method in METHODS:
            x=r[method];values.append('/'.join(map(str,x['steps']))+'；'+f"{statistics.mean(x['seconds']):.3f}"+('†' if not all(x['in_budget']) else ''))
        lines.append('| '+r['case'].removesuffix('_development')+' | '+' | '.join(values)+' |')
    lines+=['','数据由本目录 `汇报数据提取_详细版.py` 只读提取。完整300项读取路径及SHA256保存在 `汇报数据核对_详细版.json`；未启动规划器。','']
    (ROOT/'逐状态数据附录_详细版.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2));print('\n'.join(lines[:18]))
if __name__=='__main__':main()
