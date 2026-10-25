"""Freeze eligible source list before production static gate; no solves."""
from probe_common import *
paths=[str(p.relative_to(H)) for p in sorted(H.glob('*.py'))]
paths+=['binding_files.json','版本修复与预登记.md','copy_manifest.json','source_contract.json','minimal.diff','actions.json','fixed_order.json','equivalence_exclusions.json']
paths+=[str(p.relative_to(H)) for p in sorted((H/'inputs').glob('*.json'))]+[str(p.relative_to(H)) for p in sorted((H/'jobs').glob('*.json'))]
save(H/'binding_files.json',paths);print('Bound',len(paths),'code/protocol/input/job files before static PASS.')
