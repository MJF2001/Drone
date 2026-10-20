"""Audit every rendered step/time cell against its saved per-run evidence."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PACKAGE=ROOT.parent/'OARP独立基线复测_v0.1_20261018'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    data=json.loads((ROOT/'汇报版三档数据依据.json').read_text(encoding='utf-8'))
    assert all(sha(Path(p))==h for p,h in data['input_sha256'].items())
    records=data['records'];assert len(records)==240
    methods=('P2_MULTI','TREE_MST','PPCPP_CORE4','OARP_FULL_INDEPENDENT_SCENE')
    assert len({(d['budget'],d['case'],d['seed'],d['method']) for d in records})==240
    text=(ROOT/'导师汇报稿_汇报版_20261018.md').read_text(encoding='utf-8')
    section=text[text.index('## 三、'):text.index('## 四、')]
    headers=[line for line in section.splitlines() if line.startswith('| 预算 |')]
    assert len(headers)==1 and 'OARP独立运行' in headers[0]
    table=[line for line in section.splitlines() if line.startswith('| ') and ('秒 |' in line or '秒** |' in line)]
    assert len(table)==33
    cells_checked=0
    for line in table:
        cells=[c.strip() for c in line.strip('|').split('|')]
        budget=int(cells[0].replace('*','').removesuffix('秒'));label=cells[1].replace('*','')
        for method,value in zip(methods,cells[2:]):
            rs=[r for r in records if r['budget']==budget and r['method']==method and (label=='20次合计' or r['case']==label+'_development')]
            assert len(rs)==(20 if label=='20次合计' else 2)
            legal=sum(r['legal'] for r in rs)
            steps=str(sum(r['steps'] for r in rs)) if legal==len(rs) else '—'
            expected=f"{steps} / {sum(r['seconds'] for r in rs):.3f}"
            if legal<len(rs):expected+=f'（合法{legal}/{len(rs)}）'
            if label=='20次合计':expected+=f'；及时{sum(r["timely"] for r in rs)}/{len(rs)}'
            elif any(not r['timely'] for r in rs):expected+='†'
            assert value.replace('*','')==expected,(budget,label,method,value,expected)
            cells_checked+=1
    assert '18/20、20/20、20/20' in section and '10658' in section
    assert '不使用额外贪心或旧路线候选' in section
    expected_tail=(ROOT/'第四节_底层算法研究方向.md').read_text(encoding='utf-8')+'\n'+(ROOT/'第五节_下一步规划.md').read_text(encoding='utf-8')
    assert text[text.index('## 四、'):]==expected_tail
    assert text.count('## 五、下一步规划')==1
    assert '研究重心确定为PPCPP，OARP保留为对照' in text
    assert '？' not in text and 'D:/' not in text
    before={str(p):sha(p) for p in PACKAGE.rglob('*') if p.is_file()}
    process=subprocess.run([sys.executable,'-B','-X','utf8',str(PACKAGE/'seal.py'),'--check'],capture_output=True,text=True,encoding='utf-8')
    assert process.returncode==0,process.stdout+process.stderr
    after={str(p):sha(p) for p in PACKAGE.rglob('*') if p.is_file()}
    assert before==after
    result={'pass':True,'report_sha256':sha(ROOT/'导师汇报稿_汇报版_20261018.md'),
        'data_rows':240,'combined_tables_in_section3':1,'state_rows':30,'subtotal_rows':3,
        'numeric_cells_checked':cells_checked,'source_hashes_checked':len(data['input_sha256']),
        'verification_changed_files':0,'verification_planner_calls':0,'independent_package_files_checked':len(before),
        'verification_stdout':process.stdout}
    (ROOT/'汇报版三档复核记录.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='verification_stdout'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
