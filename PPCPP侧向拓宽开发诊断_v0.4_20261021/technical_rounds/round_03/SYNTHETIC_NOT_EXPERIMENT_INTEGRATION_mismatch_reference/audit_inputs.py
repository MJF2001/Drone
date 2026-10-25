"""Pre-event read-only input audit using the exact saved verify geometry block."""
from common import *
import ast
def main():
    require('technical');require('prep');require('generated')
    # Reuse the independently checking code of verify, without its later
    # complete-experiment assertions. No planner imports or route generation.
    tree=ast.parse((H/'verify.py').read_text(encoding='utf8'))
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='verify')
    start=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='maps' for t in n.targets))
    end=next(i for i in range(start,len(fn.body)) if isinstance(fn.body[i],ast.Expr) and isinstance(fn.body[i].value,ast.Call) and isinstance(fn.body[i].value.func,ast.Name) and fn.body[i].value.func.id=='print')
    namespace=dict(globals());exec(compile(ast.Module(body=fn.body[start:end],type_ignores=[]),'<exact readonly verify input block>','exec'),namespace)
    assert namespace['BFS']==24
    save(H/'input_audit.json',dict(passed=True,ordinary_BFS=24,groups=12,states=48,real_histories=6,planner_calls=0,source='exact AST geometry/history/candidate/witness block of bound verify.py'))
    receipt('inputs_audited',[H/'input_audit.json',H/'groups.json',H/'states.json',*sorted((H/'history').glob('*.json')),*sorted((H/'inputs').glob('*.json')),*sorted((H/'witnesses').glob('*.json'))])
    print('PASS independent48 input/history/candidate/feasibility audit; ordinary BFS24; planner calls0',flush=True)
if __name__=='__main__':main()
