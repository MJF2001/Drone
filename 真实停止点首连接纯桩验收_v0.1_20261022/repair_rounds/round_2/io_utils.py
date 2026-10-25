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
    # Change coordinate containers only; expression term arrays retain their schema.
    if isinstance(x, list):
        values = [tuple_coords(y) for y in x]
        coordinate = len(x) == 2 and all(type(y) is int or
                        isinstance(y, dict) and set(y) == {'n', 'd'} for y in x)
        return tuple(values) if coordinate else values
    if isinstance(x, dict):
        return {k: tuple_coords(v) for k, v in x.items()}
    return x

def plain(x):
    return json.loads(json.dumps(x, ensure_ascii=False, allow_nan=False))
