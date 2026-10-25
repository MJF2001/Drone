"""No-planner isolated reproduction of the prepared-reference/seal contract conflict.

Only the actual seal.py is executed. All common data interfaces and inventory
subprocess are synthetic; this is NOT a production seal or a passed preflight.
"""
from pathlib import Path
import sys, json, hashlib, types, subprocess, runpy, traceback
H = Path(__file__).resolve().parent
F = H / 'preflight' / 'SYNTHETIC_NOT_EXPERIMENT_seal_collision'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p, x):
    with Path(p).open('x', encoding='utf8') as f:
        json.dump(x, f, ensure_ascii=False, indent=2)
def child():
    events = []
    c = types.ModuleType('common')
    c.__file__ = str(F / 'STUB_common_NOT_REAL.py')
    c.H = F; c.R = F; c.P = F / 'STUB_frozen_sources'; c.S = F; c.M = F
    c.Path = Path; c.json = json; c.sha = sha
    c.read = lambda p: {}
    c.save = put
    c.require = lambda name: events.append({'synthetic_gate': name})
    c.binding = lambda: {'SYNTHETIC_NOT_EXPERIMENT': True}
    c.receipt = lambda *args: (_ for _ in ()).throw(AssertionError('must not reach receipt'))
    sys.modules['common'] = c
    def synthetic_inventory(argv, **kwargs):
        assert argv[-1] == 'inventory' and Path(argv[-2]).name == 'worker.py'
        events.append({'inventory': 'STUB_ONLY_NO_WORKER_EXECUTION', 'argv': argv})
        return types.SimpleNamespace(stdout=b'{"paths": []}')
    subprocess.run = synthetic_inventory
    try:
        ns = runpy.run_path(str(H / 'seal.py'), run_name='SYNTHETIC_NOT_EXPERIMENT_seal')
        ns['run'](1)
    finally:
        events.append({'real_planner_modules_loaded': [n for n in sys.modules if n in ('runtime', 'candidate', 'p2_adapter', 'ppcpp', 'p2_search_audit')]})
        put(F / 'synthetic_events.json', events)
def main():
    assert not F.exists(), 'preserve previous technical attempts'
    F.mkdir()
    (F / 'STUB_frozen_sources').mkdir(); (F / 'frozen_source_bytes').mkdir()
    for name in ('runtime.py', 'candidate.py', 'p2_adapter.py'):
        raw = b'# SYNTHETIC_NOT_EXPERIMENT; never imported or executed\n'
        for parent in (F / 'STUB_frozen_sources', F / 'frozen_source_bytes'):
            with (parent / name).open('xb') as f: f.write(raw)
    p = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(Path(__file__).resolve()), '--child'], capture_output=True)
    for name, data in [('stdout.log', p.stdout), ('stderr.log', p.stderr)]:
        with (F / name).open('xb') as f: f.write(data)
    events = json.loads((F / 'synthetic_events.json').read_text(encoding='utf8'))
    assert p.returncode != 0 and b'FileExistsError' in p.stderr
    assert b"target.open('xb')" in p.stderr and b'runtime.py' in p.stderr
    assert events[-1]['real_planner_modules_loaded'] == []
    assert not (F / 'seal1.json').exists() and not (F / 'actual_order.jsonl').exists()
    current = {name: {'prepared_path': str(H / 'frozen_source_bytes' / name),
                     'prepared_exists': (H / 'frozen_source_bytes' / name).exists(),
                     'prepared_sha256': sha(H / 'frozen_source_bytes' / name)}
               for name in ('runtime.py', 'candidate.py', 'p2_adapter.py')}
    assert all(x['prepared_exists'] for x in current.values())
    put(H / 'preflight' / 'SEAL_CREATION_CONTRACT_BLOCK.json', {
        'status': 'BLOCKED_ADDITIONAL_TECHNICAL_DEFECT', 'synthetic_not_experiment': True,
        'actual_source_under_test': str(H / 'seal.py'), 'source_sha256': sha(H / 'seal.py'),
        'expected_exception': 'FileExistsError', 'child_exit_code': p.returncode,
        'prepared_production_reference_files': current, 'real_entries': 0, 'real_cores': 0,
        'production_seal_not_attempted': True, 'inventory_subprocess': 'stubbed, no worker execution',
        'gates': 'synthetic only to isolate file creation; does not validate or bypass production gates',
        'subsequent_action': 'STOP; do not repair production seal or start experiment'})
    print('CONFIRMED BLOCK: actual seal.py exclusive creation conflicts with prepared references; synthetic fixture only; real entries/cores=0', flush=True)
    return 2
if __name__ == '__main__':
    if sys.argv[1:] == ['--child']: child()
    else: sys.exit(main())
