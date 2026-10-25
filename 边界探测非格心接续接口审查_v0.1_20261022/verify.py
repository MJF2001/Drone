"""Read-only SHA/text audit. Never import planners or geometry/executor code."""
from pathlib import Path
import hashlib
import json
import ast

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

def read(name):
    return json.loads((HERE / name).read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    sources = read('来源hash.json')
    for path, digest in sources.items():
        assert sha(Path(path)) == digest, ('source bytes changed', path)
    evidence = read('源码逐行证据.json')
    assert len(evidence) == 18 and len({e['id'] for e in evidence}) == 18
    for e in evidence:
        p = Path(e['path'])
        assert sha(p) == e['sha256'] == sources[str(p)]
        lines = p.read_text(encoding='utf-8-sig').splitlines()
        assert len(lines) == e['line_count']
        assert e['lines'] == [dict(number=i, text=t) for i, t in enumerate(lines, 1)]
    by_id = {e['id']: e for e in evidence}
    citations = read('接口证据定位.json')
    for row in citations:
        e = by_id[row['source_id']]
        lo, hi = row['lines']
        assert 1 <= lo <= hi <= e['line_count'], row['claim']
        excerpt = '\n'.join(q['text'] for q in e['lines'][lo-1:hi])
        assert all(anchor in excerpt for anchor in row['contains']), row['claim']
    old = read('历史源一致性.json')
    seal = json.loads((ROOT / 'PPCPP直达质量时间开发比较_v0.1_20261022/source_seal.json').read_text(encoding='utf-8-sig'))
    for row in old['historical_pipeline_source_matches']:
        assert row['sha256'] == seal[row['path']] == sha(Path(row['path']))
    for row in old['postprocess_byte_identical']:
        assert row['sha256'] == sha(Path(row['original'])) == sha(Path(row['actual_loaded_copy']))
    assert (HERE / '执行依据_v1.2_原字节.md').read_bytes() == (ROOT / '边界探测安全停止模型与接续接口审查执行稿_v1.2_给sol_20261022.md').read_bytes()
    ledger = read('零调用账.json')
    assert len(ledger['counters']) == 16 and all(type(v) is int and v == 0 for v in ledger['counters'].values())
    # Only inspect our utility imports as syntax; never execute inspected source.
    allowed = {'pathlib', 'datetime', 'hashlib', 'json', 'ast'}
    for name in ('collect_static.py', 'verify.py'):
        tree = ast.parse((HERE / name).read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(a.name in allowed for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                assert node.module in allowed
    gates = (HERE / '04_待裁决与有限纸面门槛.md').read_text(encoding='utf-8')
    assert all(gates.count('|G%02d|' % i) == 1 for i in range(1, 19))
    assert '|G19|' not in gates
    for name in ('00_通俗结论.md', '01_真实接口约束.md', '02_模型账本与时序.md',
                 '03_两种接入方案与代价.md', '04_待裁决与有限纸面门槛.md', 'review_packet.md'):
        assert (HERE / name).stat().st_size > 100
    if (HERE / 'completion_manifest.json').exists():
        manifest = read('completion_manifest.json')
        for name, digest in manifest['files'].items():
            assert sha(HERE / name) == digest, ('sealed artifact changed', name)
        assert sha(ROOT / '当前进度与下一步.md') == manifest['root_progress_after_sha256']
        assert (HERE / '根进度_执行后快照.md').read_bytes() == (ROOT / '当前进度与下一步.md').read_bytes()
    print(json.dumps(dict(passed=True, scope='source hashes, numbered text, historical byte links, ledger and package integrity only',
          source_files=len(evidence), hashed_sources=len(sources), paper_gates=18,
          source_citations=len(citations),
          gate_runs=0, planning=0, graph=0, geometry=0, new_inputs=0, new_routes=0,
          sealed=(HERE / 'completion_manifest.json').exists()), ensure_ascii=False))

if __name__ == '__main__':
    main()
