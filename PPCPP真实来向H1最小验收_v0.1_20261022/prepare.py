"""Static copies, derivation, side-effect review and fixed slot preregistration."""
from pathlib import Path
import json,hashlib,ast,difflib

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
OLD=ROOT/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020'
SAVED=ROOT/'PPCPP直达质量时间开发比较_v0.1_20261022'

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def main():
    assert not (HERE/'preparation_manifest.json').exists(),'no preparation overwrite'
    for name in ('derived','source_snapshot','inputs','jobs','outputs','logs','tech'):(HERE/name).mkdir(exist_ok=False)
    draft=ROOT/'PPCPP真实来向H1独立适配最小验收执行稿_给sol_20261022.md'
    (HERE/'执行依据_原字节.md').write_bytes(draft.read_bytes())
    (HERE/'根进度_执行前快照.md').write_bytes((ROOT/'当前进度与下一步.md').read_bytes())
    prior=read(ROOT/'真实停止点来向适配审查_v0.1_20261022/源码逐行证据.json')
    native=Path(next(x['path'] for x in prior if x['id']=='S03'))
    reward=Path(next(x['path'] for x in prior if x['id']=='S06'))
    originals={'ppcpp.py':native,'runtime_h1.py':OLD/'runtime.py','candidate_h1.py':OLD/'candidate.py','reward_source.py':reward}
    sources={}
    for row in prior:
        p=Path(row['path']);assert sha(p)==row['sha256'];sources[str(p)]=sha(p)
    for name,p in originals.items():(HERE/'source_snapshot'/name).write_bytes(p.read_bytes())
    text=native.read_text(encoding='utf8')
    text=text.replace('from ppcpp_independent import core,','from ppcpp_independent import ')
    text=text.replace("VERSION='PPCPP_CORE4_FIXED_HISTORY_v0.2_20261019'", "from h1_direction import parse_heading,after_edge\nfrom h1_rewards import reward_options,choose_neighbor\nVERSION='PPCPP_REAL_HEADING_H1_v0.1_20261022'")
    text=text.replace('seed,predator,previous,','seed,predator,heading_request,')
    text=text.replace("accepted=None\n", "accepted=None;heading_state=None\n",1)
    text=text.replace('    def move(segment,pending):\n','    def move(segment,pending):\n        nonlocal heading_state\n')
    text=text.replace('        for p in segment[1:]:tick();route.append(p);pending.discard(p)',
        '        for p in segment[1:]:\n            tick();prior=route[-1];route.append(p);pending.discard(p)\n            heading_state=after_edge(heading_state,prior,p,len(route)-1)')
    text=text.replace("        if previous is not None and sum(abs(a-b) for a,b in zip(previous,s.current))!=1:raise ValueError('historical heading must be adjacent')",'        heading_state=parse_heading(heading_request,s.current)')
    text=text.replace('tick();cur=route[-1];prev=route[-2] if len(route)>1 else previous','tick();cur=route[-1]')
    text=text.replace('core.reward_options(cur,prev,','reward_options(cur,heading_state,')
    text=text.replace('previous=prev,pending_count','incoming_heading=heading_state,pending_count')
    text=text.replace('core.choose_neighbor(options)','choose_neighbor(options)')
    text=text.replace("goal=s.base,pending_count=0))", "goal=s.base,pending_count=0,incoming_heading=heading_state))")
    text=text.replace('initial_previous=previous','initial_heading=heading_request')
    text=text.replace('trace=trace,accepted_seconds','trace=trace,final_heading=heading_state,accepted_seconds')
    assert 'previous' not in text and 'core.' not in text
    (HERE/'derived/ppcpp.py').write_text(text,encoding='utf8')
    runtime=(OLD/'runtime.py').read_text(encoding='utf8')
    runtime=runtime.replace('R=Path(__file__).resolve().parent.parent','R=Path(__file__).resolve().parents[2]')
    runtime=runtime.replace("R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py'", "R/'PPCPP真实来向H1最小验收_v0.1_20261022/derived/ppcpp.py'")
    runtime=runtime.replace('from candidate import solve','from candidate_h1 import solve')
    runtime=runtime.replace("tuple(c['previous']) if c['previous'] else None", "c['incoming_heading']")
    (HERE/'derived/runtime_h1.py').write_text(runtime,encoding='utf8')
    candidate=(OLD/'candidate.py').read_text(encoding='utf8');lines=candidate.splitlines(keepends=True)
    start=next(i for i,t in enumerate(lines) if "if mode=='LAST' and u:" in t)
    end=next(i for i,t in enumerate(lines) if "mark('final_audit_before')" in t)
    candidate=''.join(lines[:start]+lines[end:])
    candidate=candidate.replace('from runtime import native,','from runtime_h1 import native,').replace('previous','heading_request')
    candidate=candidate.replace("('PPCPP','ONE','LAST')", "('PPCPP',)").replace("VERSION='PPCPP_LAST_RESERVE_v0.2'", "VERSION='PPCPP_H1_ENTRY_v0.1'")
    candidate=candidate.replace('Only new policy: one input-selected last target; private F-e then restore F.', 'Independent H1 entry: frozen P0 flow only; LAST branch is excluded.')
    (HERE/'derived/candidate_h1.py').write_text(candidate,encoding='utf8')
    diffs=[]
    for name in ('ppcpp.py','runtime_h1.py','candidate_h1.py'):
        a=(HERE/'source_snapshot'/name).read_text(encoding='utf8').splitlines(keepends=True)
        b=(HERE/'derived'/name).read_text(encoding='utf8').splitlines(keepends=True)
        diffs.extend(difflib.unified_diff(a,b,fromfile='original/'+name,tofile='derived/'+name))
    rootast=ast.parse(reward.read_text(encoding='utf8'));helpers='\n\n'.join(ast.get_source_segment(reward.read_text(encoding='utf8'),n) for n in rootast.body if isinstance(n,ast.FunctionDef) and n.name in ('reward_options','choose_neighbor'))+'\n'
    (HERE/'source_snapshot/reward_helpers.py').write_text(helpers,encoding='utf8')
    diffs.extend(difflib.unified_diff(helpers.splitlines(keepends=True),(HERE/'h1_rewards.py').read_text(encoding='utf8').splitlines(keepends=True),fromfile='original/reward_helpers.py',tofile='h1_rewards.py'))
    (HERE/'最小改动.diff').write_text(''.join(diffs),encoding='utf8')
    # Review top-level Python statements in the actual project import chain.
    frozen=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/frozen_baselines/v2_20261012/source'
    inspect_paths=set(frozen.rglob('*.py'))|{native,reward,OLD/'runtime.py',OLD/'candidate.py',ROOT/'portable_frozen.py',ROOT/'基线复现准备_20261019/ppcpp_independent.py',ROOT/'PPCPP结构候选新开发验证_v0.1_20261020/validation.py'}
    review=[]
    def topwalk(node):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef,ast.Lambda)):return
        if isinstance(node,ast.If) and '__name__' in ast.unparse(node.test):return
        if isinstance(node,ast.Call):yield node
        for child in ast.iter_child_nodes(node):yield from topwalk(child)
    blocked={'solve','solve_file','calibrate','tour_replan','core_route','run_payload','system','Popen'}
    for p in sorted(inspect_paths):
        tree=ast.parse(p.read_text(encoding='utf-8-sig'));calls=[]
        for node in topwalk(tree):
            target=ast.unparse(node.func);assert target.split('.')[-1] not in blocked,(p,node.lineno,target)
            calls.append(dict(line=node.lineno,target=target))
        sources[str(p)]=sha(p);review.append(dict(path=str(p),sha256=sha(p),top_level_calls=calls))
    deps=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/.deps'
    dump(HERE/'顶层导入静态审查.json',dict(project_files=review,
        conclusion='No top-level planner/benchmark/process execution in reviewed project modules. Permitted path setup, read-only profile load, definition decorators, checked module loading/assertions.',
        dependency_initialization='pyscipopt __init__ adds DLL paths and loads bindings; glns __init__ imports numpy and its native binding. Normal library initialization, no solve invocation in these init sources. Native binary internals not claimed statically proved.',
        library_init_hashes={str(deps/pkg/'__init__.py'):sha(deps/pkg/'__init__.py') for pkg in ('glns','pyscipopt')},
        original_modules_imported_during_preparation=False))
    seal=read(SAVED/'source_seal.json')
    for p,digest in seal.items():assert sha(Path(p))==digest,('historical dependency bytes changed',p)
    sources.update(seal)
    input_hashes=read(SAVED/'input_hashes.json');plan=read(SAVED/'plan.json')
    rows=sorted((x for x in plan['formal'] if x['method']=='PPCPP' and x['rep']==0),key=lambda x:x['case'])
    assert len(rows)==54 and len({x['case'] for x in rows})==54
    jobs=[];input_records=[]
    for row in rows:
        p=SAVED/row['input'];digest=sha(p);assert digest==input_hashes[row['input']]
        c=read(p);prev=c['previous'];cur=c['current'];assert prev is not None and all(type(z) is int for z in prev+cur)
        delta=[cur[k]-prev[k] for k in (0,1)];assert sum(map(abs,delta))==1
        assert cur in c['free'] and c['base'] in c['free'] and set(map(tuple,c['targets']))<=set(map(tuple,c['free']))
        heading=dict(status='KNOWN',vector=delta,source=dict(kind='saved_previous',start=prev,end=cur,input_sha256=digest,source_input=str(p)))
        out=HERE/'inputs'/p.name;out.write_bytes(p.read_bytes());sources[str(p)]=digest
        input_records.append(dict(case=row['case'],input='inputs/'+p.name,source=str(p),sha256=digest,seed=row['seed'],legacy_previous=prev,heading=heading))
        for method in ('ORIGINAL','H1'):
            jobs.append(dict(slot=len(jobs)+1,id=f"legacy__{row['case']}__{method}",phase='legacy',case=row['case'],method=method,input='inputs/'+p.name,seed=row['seed'],heading=heading))
    chosen=next(x for x in input_records if set(map(tuple,read(HERE/x['input'])['targets']))-set(map(tuple,read(HERE/x['input'])['covered']))-{tuple(read(HERE/x['input'])['current'])})
    for vector in ([1,1],[1,-1],[-1,1],[-1,-1],[2,2],[2,-2],[-2,2],[-2,-2]):
        for repeat in (0,1):
            ident='diag__'+('_'.join(map(str,vector)))+'__'+str(repeat)
            heading=dict(status='KNOWN',vector=vector,source=dict(kind='synthetic_direction_fixture',fixture_id=ident,base_input_sha256=chosen['sha256'],not_actual_history=True))
            jobs.append(dict(slot=len(jobs)+1,id=ident,phase='diagonal',case=chosen['case'],method='H1',input=chosen['input'],seed=chosen['seed'],heading=heading,repeat=repeat))
    assert len(jobs)==124
    for job in jobs:dump(HERE/'jobs'/f"{job['slot']:03d}.json",job)
    dump(HERE/'计划_124槽.json',dict(jobs=jobs,legacy_entries=108,diagonal_entries=16,chosen_diagonal_case=chosen['case'],retry=False,budget=20,watchdog_seconds=90))
    dump(HERE/'54输入来源清单.json',input_records)
    sources[str(draft)]=sha(draft);sources[str(SAVED/'plan.json')]=sha(SAVED/'plan.json');sources[str(SAVED/'input_hashes.json')]=sha(SAVED/'input_hashes.json')
    dump(HERE/'原来源hash.json',sources)
    dump(HERE/'preparation_manifest.json',dict(copied_sources={name:sha(HERE/'source_snapshot'/name) for name in originals},inputs=54,planned_entries=124,production_imports=0,planning_calls=0))
    print(json.dumps(dict(prepared=True,inputs=54,slots=124,static_project_sources=len(review),source_hashes=len(sources),planning_calls=0)))

if __name__=='__main__':main()
