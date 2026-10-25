"""Three frozen byte references only: validate source first, never overwrite."""
from pathlib import Path
import hashlib,os,stat
NAMES=('runtime.py','candidate.py','p2_adapter.py')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ordinary(p):
    s=p.lstat()
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and not getattr(s,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',1024),('unexpected_reference_type',str(p))
def references(source_dir,target_dir,expected):
    source_dir=Path(source_dir);target_dir=Path(target_dir)
    assert target_dir.name=='frozen_source_bytes' and target_dir.is_dir() and not target_dir.is_symlink()
    s=target_dir.lstat();assert not getattr(s,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',1024)
    # Check ALL inherited source hashes before creating any reference.
    for name in NAMES:
        src=source_dir/name;ordinary(src);assert str(src.resolve()) in expected,('missing_inherited_hash',str(src))
        assert sha(src)==expected[str(src.resolve())],('frozen_source_drift',str(src))
    rows=[]
    for name in NAMES:
        src=source_dir/name;dst=target_dir/name;assert dst.parent.resolve()==target_dir.resolve()
        raw=src.read_bytes();existed=dst.exists() or dst.is_symlink();before=dst.lstat().st_mtime_ns if existed else None
        if not existed:
            try:
                with dst.open('xb') as f:f.write(raw)
                action='created'
            except FileExistsError:action='race_read_validation'
        else:action='reused_read_only'
        ordinary(dst);assert dst.read_bytes()==raw,('reference_bytes_mismatch',str(dst))
        if existed:assert dst.lstat().st_mtime_ns==before,('reference_timestamp_changed',str(dst))
        rows.append(dict(name=name,action=action,sha256=sha(dst),existing_mtime_unchanged=existed))
    return rows
