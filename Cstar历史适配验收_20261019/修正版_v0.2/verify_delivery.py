"""Read-only delivery integrity, including preservation of the prior prototype."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parent
for folder in (root,root.parent):
    manifest=json.loads((folder/'delivery_manifest.json').read_text(encoding='utf8'))
    for name,sha in manifest['files'].items():
        assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==sha,str(folder/name)
    print(folder.name,len(manifest['files']),'content hashes verified')
print('Micro gate PASS_BOUNDED; performance ranking not authorized or executed.')
