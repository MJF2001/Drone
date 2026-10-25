from common import *
paths=[str(p.relative_to(H)) for p in sorted(H.glob('*.py'))]+['binding_files.json','protocol.md','maps.json','prep_order.json']+[str(p.relative_to(H)) for p in sorted((H/'inputs').glob('*.json'))]+[str(p.relative_to(H)) for p in sorted((H/'jobs').glob('*.json'))]
save(H/'binding_files.json',paths);print('Bound',len(paths),'code/protocol/preparation inputs before any real calls')
