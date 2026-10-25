"""Derive the still-unvalidated old stub fixture with hash-bound stage gates."""
from probe_common import *
old=R/'PPCPP一次历史邻格干预诊断_v0.1_20261021/stub_gate.py';txt=old.read_text(encoding='utf8')
txt=txt.replace('from probe_hook import force_history_step','from probe_hook import force_history_step\nfrom stage_control import require_preseal,receipt\nrequire_preseal()')
txt=txt.replace("if __name__=='__main__':save(H/'stub_results.json',run());print('PASS 8 fixed stub checks; helper calls=7, wrapper stub=1, real planner/core=0')","if __name__=='__main__':\n    save(H/'stub_results.json',run());receipt('stubs',[H/'stub_results.json']);print('PASS 8 fixed stub checks; helper calls=7, wrapper stub=1, real planner/core=0')")
with (H/'stub_gate.py').open('xb') as f:f.write(txt.encode('utf8'))
print('Derived unvalidated auxiliary stub from v0.1; added preseal validation and explicit hash-bound PASS receipt. No calls.')
