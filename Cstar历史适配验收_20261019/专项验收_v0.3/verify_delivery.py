"""Read-only integrity verification for this delivery and both ancestors."""
import json,hashlib
from pathlib import Path
root=Path(__file__).resolve().parent
for directory in (root,root.parent/'修正版_v0.2',root.parent):
    m=json.loads((directory/'delivery_manifest.json').read_text(encoding='utf8'))
    for path,sha in m['files'].items():assert hashlib.sha256((directory/path).read_bytes()).hexdigest()==sha,str(directory/path)
    print(directory.name,len(m['files']),'hashes verified')
print('Bounded-special gate only; no performance freeze or ranking.')
