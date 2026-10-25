"""Pure technical checks, shared by real preflight and negative fixture."""
from pathlib import Path
import ast,hashlib,json
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def syntax_gate(paths,after=None):
    rows=[]
    for p in sorted(set(map(Path,paths))):
        ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p));rows.append(dict(path=str(p.resolve()),sha256=sha(p),passed=True))
    if after:after()
    return rows
def guarded_worker(path,old):
    t=ast.parse(Path(path).read_text(encoding='utf8'));s=Path(old).read_text(encoding='utf8');prefix=s[:s.index('assert Path(runtime.__file__).resolve()')]
    original=ast.parse(s).body[len(ast.parse(prefix).body):]
    main=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='main');body=list(main.body);gate=ast.parse("require('technical')").body[0]
    i=[i for i,n in enumerate(body) if ast.dump(n)==ast.dump(gate)];assert len(i)==1;body.pop(i[0]);assert ast.dump(ast.Module(body=body,type_ignores=[]))==ast.dump(ast.Module(body=original,type_ignores=[]))
    forbidden={'read','save','require','check_seal','sys.addaudithook','runtime.run_payload','p2_adapter.run_payload'}
    for n in t.body:
        if isinstance(n,(ast.FunctionDef,ast.Import,ast.ImportFrom)) or isinstance(n,ast.If):continue
        for c in ast.walk(n):
            if isinstance(c,ast.Call):assert ast.unparse(c.func) not in forbidden,ast.unparse(c)
    assert not any(isinstance(n,ast.Global) for n in ast.walk(main))
    return dict(task_AST_equal_except_one_technical_gate=True,no_global_added=True,task_calls_inside_guard=True)
