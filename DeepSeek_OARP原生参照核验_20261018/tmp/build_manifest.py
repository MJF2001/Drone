import hashlib, json, os, sys
from pathlib import Path
NEW = Path(r'D:\0A无人机仿真02\问题分析+文献分析\DeepSeek_OARP原生参照核验_20261018')
TARGET = NEW / 'manifests' / 'delivery_sha256.json'
skip = {'manifests/delivery_sha256.json'}
files = {}
for root, dirs, names in os.walk(NEW):
    dirs[:] = sorted(d for d in dirs if d not in {'tmp', '__pycache__'})
    for name in sorted(names):
        p = Path(root) / name
        rel = p.relative_to(NEW).as_posix()
        if rel in skip:
            continue
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        files[rel] = h
payload = {'round': 'oarp_native_reference_20261018',
           'root': str(NEW),
           'scope': 'every file under OUT except tmp/ and this manifest',
           'append_only': ['logs/calls_ledger.csv'],
           'append_only_rule': 'prefix seals under manifests/ledger_seal_*.json',
           'file_count': len(files),
           'total_bytes': sum((NEW / n).stat().st_size for n in files),
           'files': files}
TARGET.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding='utf-8')
print('files', len(files), 'bytes', payload['total_bytes'])
