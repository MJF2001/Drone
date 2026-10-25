"""Two pure fixtures exercise actual prepare_gate.py subprocess fail/next path."""
from stage_control import *
import subprocess,sys
require('static');rows=[]
for label,same in [('mismatch',False),('equal',True)]:
    folder=H/'fixtures'/label;folder.mkdir();(folder/'source.bin').write_bytes(b'a\nb\n');(folder/'target.bin').write_bytes(b'a\nb\n' if same else b'a\r\nb\r\n');save(folder/'config.json',dict(folder=str(folder),source=str(folder/'source.bin'),target=str(folder/'target.bin')))
    p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'prepare_gate.py'),'fixture',str(folder/'config.json')],capture_output=True)
    (folder/'stdout.log').write_bytes(p.stdout);(folder/'stderr.log').write_bytes(p.stderr)
    if same:assert p.returncode==0 and (folder/'preseal.json').exists() and (folder/'next_stage_sentinel.txt').exists()
    else:assert p.returncode!=0 and not (folder/'preseal.json').exists() and not (folder/'next_stage_sentinel.txt').exists() and b'COPY_BYTES_MISMATCH' in p.stderr
    rows.append(dict(case=label,expected_negative=not same,exit_code=p.returncode,preseal_exists=(folder/'preseal.json').exists(),sentinel_executed=(folder/'next_stage_sentinel.txt').exists(),passed=True,planner_calls=0))
save(H/'prep_fixture_results.json',dict(tests=rows,passed=True,real_entries=0,real_cores=0));receipt('prepare_fixtures',[H/'prep_fixture_results.json',*sorted((H/'fixtures').rglob('*.*'))]);print('PASS 2 preparation fixtures: expected byte failure blocks seal/next stage; byte equality permits mock seal; real entries=0')
