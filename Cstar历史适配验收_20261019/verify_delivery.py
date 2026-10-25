"""Read-only content integrity check. Not a rerun or algorithm certification."""
import json,hashlib
from pathlib import Path
root=Path(__file__).resolve().parent
manifest=json.loads((root/'delivery_manifest.json').read_text(encoding='utf8'))
for name,sha in manifest['files'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,name
print('Content hashes verified:',len(manifest['files']),'files; acceptance gate:',manifest['acceptance_gate'])
