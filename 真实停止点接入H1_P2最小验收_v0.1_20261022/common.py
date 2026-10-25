from pathlib import Path
from datetime import datetime, timezone
from fractions import Fraction
import json, hashlib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def now():
    return datetime.now(timezone.utc).isoformat()

def evidence(value):
    if isinstance(value, Fraction):
        return {'invalid_runtime_type': 'Fraction', 'n': value.numerator, 'd': value.denominator}
    if isinstance(value, dict):
        return {k: evidence(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [evidence(v) for v in value]
    return value
