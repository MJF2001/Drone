"""Hashes and scalar arithmetic of a hand-written proof only. No planning."""
from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    for p,h in read(H/'来源hash.json').items():assert sha(Path(p))==h,p
    if (H/'completion_manifest.json').exists():
        for p,h in read(H/'completion_manifest.json')['files'].items():assert sha(H/p)==h,p
    refs=read(H/'文献获取记录.json');assert len(refs)==4
    for r in refs:
        if r['saved']:assert sha(H/r['file'])==r['sha256'] and (H/r['file']).read_bytes().startswith(b'%PDF')
        else:assert r['full_text_read_with_web']
    p=read(H/'手工算术证据.json');nominal=sum(p['nominal_segment_lengths']);actual=sum(p['actual_segment_lengths']);incumbent=sum(p['incumbent_segment_lengths']);assert nominal==12 and actual==8 and incumbent==10 and actual<incumbent<=p['budget']==nominal;assert p['actual_first_order']!=p['nominal_order'];assert max(p['root_bound_terms'])==actual
    z=read(H/'零调用账.json');assert all(z[k]==0 for k in ('real_planning','core','graph_search','visibility_queries','project_candidate_generation','new_project_routes','performance_experiments','production_module_imports','old_verify_runs','input_transformations'));assert z['original_papers_read']==4 and z['candidate_bound_formulas_examined']==1
    # This checks the recorded scalar witness, not the entire mathematical
    # theorem or literature novelty. Those require the cited text and proof.
    print(json.dumps({'passed':True,'source_hashes':len(read(H/'来源hash.json')),'papers':4,'saved_pdfs':sum(r['saved'] for r in refs),'manual_sums':[nominal,actual,incumbent],'new_project_calls':0,'verification_scope':'hashes + hand-written scalar equalities; proof and novelty judged in prose'},ensure_ascii=False))
if __name__=='__main__':main()
