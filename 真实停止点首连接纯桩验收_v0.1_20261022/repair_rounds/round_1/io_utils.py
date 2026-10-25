import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def now():
    return datetime.now(timezone.utc).isoformat()

def tuple_coords(x):
    # Every coordinate/cell sequence becomes tuple; dictionaries preserve field names.
    if isinstance(x, list):
        return tuple(tuple_coords(y) for y in x)
    if isinstance(x, dict):
        return {k: tuple_coords(v) for k, v in x.items()}
    return x

def plain(x):
    return json.loads(json.dumps(x, ensure_ascii=False, allow_nan=False))
