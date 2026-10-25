from pathlib import Path
import json,hashlib,shutil
import engine
H=Path(__file__).resolve().parent;R=H.parent;OLD=R/'任意方向直达模型前审查_v0.1_20261022'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def dump(p,v):
    with p.open('x',encoding='utf8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
def main():
    assert read(H/'gate_attempt_1.json')['passed'];assert not (H/'frozen_manifest.json').exists()
    for name,v in read(OLD/'completion_manifest.json')['files'].items():assert sha(OLD/name)==v,name
    sources=read(OLD/'来源hash.json')
    for p,v in sources.items():assert sha(Path(p))==v,p
    sources[str(OLD/'completion_manifest.json')]=sha(OLD/'completion_manifest.json');sources[str(OLD/'60份字段与原路线段账.json')]=sha(OLD/'60份字段与原路线段账.json')
    old=read(OLD/'60份字段与原路线段账.json');jobs=[];(H/'inputs').mkdir(exist_ok=True);(H/'outputs').mkdir(exist_ok=True);(H/'audits').mkdir(exist_ok=True)
    for r in old:
        specs=[('PPCPP',Path(r['input']),Path(r['output']))]
        if r['batch']=='54_states':
            q=r['P2_pairings'][0];assert q['physical_equal'];specs.append(('P2_MULTI',Path(q['input']),Path(q['output'])))
        elif r['P2_pairings'][0]['physical_equal']:
            q=r['P2_pairings'][0];sp=Path(q['output_session']);req=read(sp)['sessions']['P2_MULTI']['requests'][q['request_index']];stem=r['case']+'_P2_MULTI_t%03d'%req['tick'];specs.append(('P2_MULTI',sp.parent.parent/'inputs'/(stem+'.json'),sp.parent.parent/'outputs'/(stem+'.json')))
        for method,ip,op in specs:
            c=read(ip);o=read(op);native=o['result'] if 'result' in o else o['entry']['native_return'];raw=native['raw'];n=len(raw['route'])-1;u=engine.ps(c['targets'])-engine.ps(c['covered'])
            # Verify every extra source against its pre-existing sealed package, never just a fresh hash.
            for p in (ip,op):
                if str(p) in sources:assert sources[str(p)]==sha(p),str(p)
                else:
                    root=p.parent.parent;mf=root/'completion_manifest.json';entries=read(mf)['files'];rel=str(p.relative_to(root));assert entries.get(rel,entries.get(p.relative_to(root).as_posix()))==sha(p),str(p);sources[str(mf)]=sha(mf)
                sources[str(p)]=sha(p)
            assert c['current']==r['physical']['current'] and c['base']==r['physical']['base'];assert engine.ps(c['free'])==engine.ps(r['physical']['F']);assert engine.ps(c['covered'])==engine.ps(r['physical']['H']);assert u==engine.ps(r['physical']['U'])
            jid=r['batch']+'__'+r['case']+'__'+method;payload={'id':jid,'input':c,'raw':raw};pp=H/'inputs'/(jid+'.json');dump(pp,payload)
            jobs.append({'id':jid,'batch':r['batch'],'case':r['case'],'method':method,'payload':str(pp.relative_to(H)),'source_input':str(ip),'source_output':str(op),'source_input_sha256':sha(ip),'source_output_sha256':sha(op),'payload_sha256':sha(pp),'original_edges':n,'required_tasks':len(u),'saved_generation_seconds':native['entry_seconds'],'saved_generation_budget':native['budget'],'limits':{'candidate_geometry':4096,'source_geometry':n,'output_geometry':n,'independent_geometry':n,'main_service_intersections':n*len(u),'independent_service_intersections':n*len(u)}})
    assert len(jobs)==117 and sum(j['batch']=='54_states' for j in jobs)==108;dump(H/'117固定清单.json',jobs)
    limits={k:sum(j['limits'][k] for j in jobs) for k in jobs[0]['limits']};dump(H/'正式批预登记成本上限.json',{'routes':117,'per_entry_total_seconds':20,'per_entry_soft_stop_seconds':18,'totals':limits,'geometry_preprocessing':'No visibility construction or query. Build F set and first-service indices; time charged in entry.','initial_payload_extraction':'Saved payload extraction/source preflight outside entry and not historical planning generation; no new planning','independent_audit':'outside entry, separately counted; at most one geometric pass per output edge this batch','failures':'source conflict, exception, invalid final output: stop remaining slots; no reruns'})
    dump(H/'来源hash.json',sources);shutil.copyfile(R/'任意方向合法直达有限诊断执行稿_给sol_20261022.md',H/'执行稿原文快照.md')
    dump(H/'技术准备记录.json',{'schema_inspection_error':'Before gate preparation, read-only inspection looked for nonexistent session responses key. Correct saved schema is requests[k].response, with native route/trace/timing in corresponding sealed outputs. No planning/postprocessing had run; no saved data changed.','prepare_attempt_1':'Stopped before creating any route payload: assumed every legacy package has completion_manifest.json. Fixed to use the already sealed predecessor source hashes for known sources, and six-world package completion manifest for new sources. Failed log preserved; no source hash conflict or postprocessing call occurred.','gate_attempts':1,'gate_passed':24,'source_conflicts':0})
    names=['geometry.py','audit_geometry.py','engine.py','gates.py','prepare.py','batch.py','verify.py','24门槛预登记.json','gate_attempt_1.json','117固定清单.json','正式批预登记成本上限.json','来源hash.json','执行稿原文快照.md']
    dump(H/'frozen_manifest.json',{'files':{name:sha(H/name) for name in names},'protocol':'D1-D5 exactly as execution draft; farthest original index per locked nominal first-service interval; 4096 candidates / 18 s soft / 20 s entry; one pass each','gate_passed':24})
    print(json.dumps({'frozen_routes':len(jobs),'caps':limits,'source_hashes':len(sources)},ensure_ascii=False))
if __name__=='__main__':main()
