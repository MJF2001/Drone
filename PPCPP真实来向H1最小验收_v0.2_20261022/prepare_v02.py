"""Read/copy existing bytes; never import production or run a planner."""
from pathlib import Path
import hashlib,json

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;OLD=ROOT/'PPCPP真实来向H1最小验收_v0.1_20261022'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def main():
    assert not (HERE/'准备与旧包绑定.json').exists(),'no overwrite'
    oldmanifest=read(OLD/'completion_manifest.json')
    for rel,digest in oldmanifest['files'].items():assert sha(OLD/rel)==digest,('old package changed',rel)
    for path,digest in read(OLD/'原来源hash.json').items():assert sha(Path(path))==digest,('source conflict',path)
    slots=read(OLD/'124槽实际账.json');assert slots[0]['status']=='failed' and all(x['status']=='not_run' for x in slots[1:])
    assert read(OLD/'status.json')['attempted']==1
    for name in ('source_snapshot','derived','inputs','jobs','tech','logs','outputs','reuse','repair_rounds'):(HERE/name).mkdir(exist_ok=False)
    bindings={}
    for folder in ('source_snapshot','derived','inputs','jobs'):
        for source in sorted((OLD/folder).rglob('*')):
            if source.is_file():
                rel=source.relative_to(OLD);target=HERE/rel;target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(source.read_bytes());bindings[rel.as_posix()]=dict(source=str(source),sha256=sha(source))
    for name in ('h1_direction.py','h1_rewards.py','gates.py','independent_audit.py','worker.py',
                 '计划_124槽.json','54输入来源清单.json','原来源hash.json','顶层导入静态审查.json',
                 '01_合同与数值策略_事前冻结.md','技术门槛预登记.json','最小改动.diff'):
        target=HERE/name;source=OLD/name;target.write_bytes(source.read_bytes())
        bindings[name]=dict(source=str(source),sha256=sha(source))
    # Retain historical gate evidence separately; do not re-execute its 26 cases.
    for source in sorted((OLD/'tech').glob('*')):
        if source.is_file():(HERE/'tech'/source.name).write_bytes(source.read_bytes())
    for name in ('independent_audit.py','worker.py','run.py','verify.py'):
        (HERE/'source_snapshot'/('v01_'+name)).write_bytes((OLD/name).read_bytes())
    draft=ROOT/'PPCPP真实来向H1审核器修复与接续验收执行稿_给sol_20261022.md'
    (HERE/'执行依据_原字节.md').write_bytes(draft.read_bytes())
    (HERE/'根进度_执行前快照.md').write_bytes((ROOT/'当前进度与下一步.md').read_bytes())
    dump(HERE/'准备与旧包绑定.json',dict(old_package=str(OLD),old_manifest_sha256=sha(OLD/'completion_manifest.json'),
        old_manifest_files=len(oldmanifest['files']),old_slot1_status='failed',old_attempts=1,
        algorithm_bindings={rel:row for rel,row in bindings.items() if rel.startswith(('derived/','source_snapshot/','inputs/','jobs/')) or rel in ('h1_direction.py','h1_rewards.py')},
        copied_initial_files=bindings,max_new_entries=123,max_cross_version_entries=124,
        legacy_gate_result_source=str(OLD/'tech/attempt_1_result.json'),legacy_gate_result_sha256=sha(OLD/'tech/attempt_1_result.json'),
        legacy_gate_reexecutions=0,planning_calls=0,
        loading_note='Byte-identical runtime_h1 retains its explicit v0.1 native path; loaded core bytes equal v0.2 copy. Only v0.2 auditor/wrappers are repaired.'))
    print(json.dumps(dict(old_slot1='failed',old_manifest_verified=len(oldmanifest['files']),copied_algorithm_and_inputs=True,new_real_entries=0),ensure_ascii=False))

if __name__=='__main__':main()
