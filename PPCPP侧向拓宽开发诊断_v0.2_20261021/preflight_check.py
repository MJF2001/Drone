"""Syntax check then static import safety; never import unsafe task modules."""
from pathlib import Path
import json,hashlib,ast,sys
H=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
    with p.open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def fullname(node):
    if isinstance(node,ast.Name):return node.id
    if isinstance(node,ast.Attribute):return fullname(node.value)+'.'+node.attr
    return ast.unparse(node)
def top_nodes(tree):
    for node in tree.body:
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):continue
        if isinstance(node,ast.If) and ast.unparse(node.test) in ("__name__ == '__main__'",'__name__ == "__main__"'):continue
        yield from ast.walk(node)
def main():
    active=sorted(H.glob('*.py'));rows=[]
    for p in active:
        row=dict(file=p.name,path=str(p),sha256=sha(p),passed=False)
        try:ast.parse(p.read_text(encoding='utf8'),filename=str(p));row['passed']=True
        except SyntaxError as ex:row.update(error=ex.msg,line=ex.lineno)
        rows.append(row)
    save(H/'preflight/active_syntax.json',dict(stage='A',active_files=rows,passed=all(r['passed'] for r in rows),pass_count=sum(r['passed'] for r in rows),real_entries=0))
    if not all(r['passed'] for r in rows):raise RuntimeError('A syntax gate failed')
    print('PASS A:',len(rows),'active Python sources parse; no code executed',flush=True)
    modules=[];unsafe=[]
    for name in ('run.py','analysis.py','verify.py','generate.py','worker.py'):
        p=H/name;tree=ast.parse(p.read_text(encoding='utf8'));calls=[]
        for node in top_nodes(tree):
            if isinstance(node,ast.Call):
                target=fullname(node.func)
                if target in ('runtime.run_payload','p2_adapter.run_payload','sys.addaudithook','subprocess.run','subprocess.Popen') or (target.endswith('.open') and any(isinstance(a,ast.Constant) and a.value in ('x','w','xb','wb') for a in node.args)):
                    calls.append(dict(line=node.lineno,target=target,expression=ast.unparse(node),source_line=p.read_text(encoding='utf8').splitlines()[node.lineno-1]))
        record=dict(file=name,sha256=sha(p),unsafe_top_level_calls=calls,safe_for_dynamic_import=not calls);modules.append(record)
        if calls:unsafe.append(record)
    save(H/'preflight/import_static.json',dict(stage='B_STATIC',modules=modules,passed=not unsafe,dynamic_import_attempts=0,actual_entry_markers=0,core_markers=0))
    if unsafe:
        save(H/'preflight/B_STATIC_BLOCK.json',dict(status='BLOCKED_BEFORE_DYNAMIC_IMPORT',reason='Required worker has unguarded top-level planning/read-hook/output actions',unsafe=unsafe,worker_import_not_attempted=True,following_stages='C / negative fixtures / eight stubs / seals / preparation / formal not run',instruction='v0.2 section3B: if import itself solves or writes formal results, stop and report; do not directly execute unsafe import.'))
        print('BLOCK B_STATIC: worker.py has top-level planner calls/output write; no dynamic import or solver executed',flush=True);return 2
    print('B static safe; dynamic/C stages still require separate implementation and receipts',flush=True);return 0
if __name__=='__main__':sys.exit(main())
