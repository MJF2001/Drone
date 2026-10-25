"""Read-only static package verification. No source execution, queries or replay."""
from pathlib import Path
import hashlib
import json
import ast
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(name):
    return json.loads((HERE / name).read_text(encoding='utf-8-sig'))

def main():
    hashes = read('来源hash.json')
    for path, digest in hashes.items():
        assert sha(Path(path)) == digest, ('source bytes changed', path)
    evidence = read('源码逐行证据.json')
    assert len(evidence) == 19 and len({e['id'] for e in evidence}) == 19
    by_id = {e['id']: e for e in evidence}
    for e in evidence:
        p = Path(e['path'])
        assert e['sha256'] == hashes[str(p)] == sha(p)
        rows = p.read_text(encoding='utf-8-sig').splitlines()
        assert len(rows) == e['line_count']
        assert e['lines'] == [dict(number=i, text=t) for i, t in enumerate(rows, 1)]
    for row in read('接口证据定位.json'):
        e = by_id[row['source_id']]
        lo, hi = row['lines']
        assert 1 <= lo <= hi <= e['line_count'], row['claim']
        text = '\n'.join(q['text'] for q in e['lines'][lo-1:hi])
        assert all(t in text for t in row['contains']), row['claim']
    occurrences = read('current_previous文本出现清单.json')['sources']
    assert len(occurrences) == 19
    for row in occurrences:
        expected = [q for q in by_id[row['id']]['lines'] if re.search(r'\b(current|previous|prev|cur|initial_previous)\b', q['text'])]
        assert row['occurrences'] == expected
    consistency = read('历史源与旧包一致性.json')
    prior = ROOT / '边界探测非格心接续接口审查_v0.1_20261022'
    manifest = json.loads((prior / 'completion_manifest.json').read_text(encoding='utf-8-sig'))
    assert sha(prior / 'completion_manifest.json') == consistency['prior_package_manifest_sha256']
    for name, digest in manifest['files'].items():
        assert sha(prior / name) == digest
    for row in consistency['postprocess_copies']:
        assert sha(Path(row['original'])) == row['sha256'] == sha(Path(row['actual_loaded_copy']))
    assert (HERE / '执行依据_原字节.md').read_bytes() == (ROOT / '真实停止点与来向独立适配审查执行稿_给sol_20261022.md').read_bytes()
    zero = read('零调用账.json')
    assert len(zero['counters']) == 16 and all(type(v) is int and v == 0 for v in zero['counters'].values())
    assert zero['paper_gates'] == 8 and zero['paper_gate_runs'] == 0
    gates = (HERE / '04_聚焦未决与八项纸面门槛.md').read_text(encoding='utf8')
    assert all(gates.count('|G%02d|' % i) == 1 for i in range(1, 9)) and '|G09|' not in gates
    allowed = {'pathlib', 'datetime', 'hashlib', 'json', 'ast', 're'}
    for name in ('collect_static.py', 'verify.py'):
        tree = ast.parse((HERE / name).read_text(encoding='utf8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(alias.name in allowed for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                assert node.module in allowed
    for name in ('00_通俗说明.md', '01_源码追踪与最小改动.md', '02_推荐合同与方向首连接.md',
                 '03_P2比较口径与采集动作.md', '04_聚焦未决与八项纸面门槛.md', 'review_packet.md'):
        assert (HERE / name).stat().st_size > 100
    sealed = (HERE / 'completion_manifest.json').exists()
    if sealed:
        m = read('completion_manifest.json')
        for name, digest in m['files'].items():
            assert sha(HERE / name) == digest, ('sealed artifact changed', name)
        assert sha(HERE / '根进度_执行后快照.md') == m['root_progress_after_sha256']
        assert sha(ROOT / '当前进度与下一步.md') == m['root_progress_after_sha256']
    print(json.dumps(dict(passed=True, scope='static file hashes, source line/text anchors, prior artifact preservation and ledger only',
        sources=19, hashed_files=len(hashes), source_citations=len(read('接口证据定位.json')),
        paper_gates=8, gate_runs=0, new_algorithm_calls=0, sealed=sealed), ensure_ascii=False))

if __name__ == '__main__':
    main()
