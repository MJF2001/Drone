"""Actual fail-closed copy gate, also used by the two fixture subprocesses."""
from stage_control import *
import sys,ast
def gated_next(pairs,next_stage):
    for source,target in pairs:
        assert Path(source).read_bytes()==Path(target).read_bytes(),('COPY_BYTES_MISMATCH',str(target))
        assert sha(source)==sha(target),('COPY_HASH_MISMATCH',str(target))
    return next_stage()
def production():
    pairs=[(x['source'],x['target']) for x in read(H/'copy_manifest.json') if x['kind']=='required_exact_binary']
    def after():
        for path,h in read(H/'source_contract.json').items():assert sha(path)==h,('frozen_source_drift',path)
        for c in read(H/'copy_manifest.json'):assert sha(c['source'])==c['source_sha256'] and sha(c['target'])==c['target_sha256']
        old=(R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py').read_text(encoding='utf8');new=(H/'native_probe.py').read_text(encoding='utf8');tree=ast.parse(new);loop=lambda t:next(n for n in ast.walk(ast.parse(t)) if isinstance(n,ast.While))
        assert ast.dump(loop(old),include_attributes=False)==ast.dump(loop(new),include_attributes=False)
        hooks=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='force_history_step'];assert len(hooks)==1 and hooks[0].lineno<loop(new).lineno
        orig=(P/'runtime.py').read_bytes();expected=orig.replace("R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py'".encode(),("R/'"+H.name+"/native_probe.py'").encode());assert (H/'runtime.py').read_bytes()==expected
        assert b'\r\n' not in (H/'native_probe.py').read_bytes() if b'\r\n' not in (R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py').read_bytes() else True
        for p in H.glob('*.py'):ast.parse(p.read_text(encoding='utf8'))
        assert len(read(H/'fixed_order.json'))==24 and set(read(H/'actions.json'))==set(CASES)
        for c in CASES:
            a=read(H/'actions.json')[c];assert a['current']==[5,2] and a['previous']==[4,2] and a['next']==[5,1]
        assert not (H/'preseal.json').exists() and not (H/'actual_order.jsonl').exists()
        receipt('static',[H/'copy_manifest.json',H/'minimal.diff',H/'source_contract.json']);print('PASS production static gate: exact bytes/hash, original while, only intended native/path differences; no preseal yet')
    gated_next(pairs,after)
if __name__=='__main__':
    if sys.argv[1]=='production':production()
    else:
        config=read(sys.argv[2]);folder=Path(config['folder'])
        def mock_seal():
            save(folder/'preseal.json',dict(status='MOCK_SEAL_PASS',real_entries=0));(folder/'next_stage_sentinel.txt').write_bytes(b'EXECUTED');print('MOCK_SEAL_PASS')
        gated_next([(config['source'],config['target'])],mock_seal)
