"""Serial 12-slot gate. Any failure stops remaining slots; no retries."""
from pathlib import Path
import subprocess, os, sys, json, traceback, time
from common import HERE, read, dump, sha, now

def main():
    assert not (HERE/'attempts.jsonl').exists(), 'real batch was already started; no rerun'
    reg = read(HERE/'registration.json')
    tech = read(HERE/'technical_rounds/round_1/result.json')
    assert tech['failed'] == 0 and tech['passed'] == 11
    freeze = read(HERE/'real_freeze.json')
    for name, digest in freeze['files'].items():
        assert sha(HERE/name) == digest
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    attempted, completed, failure = [], [], None
    for job in reg['jobs']:
        attempted.append(job['id'])
        with (HERE/'attempts.jsonl').open('a', encoding='utf-8') as file:
            file.write(json.dumps({'utc': now(), 'id': job['id'], 'event': 'attempted_once'}, ensure_ascii=False)+'\n')
        start = time.perf_counter()
        try:
            proc = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(HERE/'worker.py'), job['id']],
                                   env=env, capture_output=True, timeout=45)
            (HERE/'logs'/(job['id']+'.log')).write_bytes(proc.stdout+proc.stderr)
            if proc.returncode != 0:
                raise RuntimeError('worker_nonzero:'+str(proc.returncode))
            data = read(HERE/'outputs'/(job['id']+'.json'))
            assert data['passed'] is True
            completed.append(job['id'])
        except Exception as error:
            failure = {'job': job, 'reason': repr(error), 'traceback': traceback.format_exc(),
                       'external_worker_wall_seconds': time.perf_counter()-start}
        status = {'utc': now(), 'planned': 12, 'attempted': attempted, 'completed': completed,
                  'failed': 1 if failure else 0, 'not_run': 12-len(attempted), 'failure': failure,
                  'stopped': bool(failure) or len(completed) == 12}
        dump(HERE/'batch_status.json', status)
        print(job['id'], 'STOP_FAILED' if failure else 'passed', f'{len(completed)}/12', flush=True)
        if failure:
            break
    if failure:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
