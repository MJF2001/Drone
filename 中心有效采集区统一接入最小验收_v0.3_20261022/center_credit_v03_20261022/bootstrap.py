"""Copy source only, preserve originals; no experiment on import."""
from pathlib import Path
import shutil,json,hashlib,difflib,ast
HERE=Path(__file__).resolve().parents[1]
PKG=Path(__file__).resolve().parent
OLD=HERE.parent/'斜向执行障碍发现首次闭环_v0.1_20261022'

def main():
    assert not (HERE/'source_bindings.json').exists()
    bindings=[];diffs=[]
    def copy(src,dst,transform=lambda s:s):
        original=(OLD/src).read_text(encoding='utf-8-sig')
        text=transform(original)
        target=PKG/dst;target.parent.mkdir(exist_ok=True,parents=True)
        target.write_text(text,encoding='utf-8')
        bindings.append({'source':str(OLD/src),'copy':str(target.relative_to(HERE)),
                         'source_sha256':hashlib.sha256((OLD/src).read_bytes()).hexdigest(),
                         'changed':text!=original})
        if text!=original:
            diffs.append(''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile=str(OLD/src),tofile=str(target))))
    def names(s):
        for name in ('exact','connector','public_contract','pipeline','detector'):
            s=s.replace('from '+name+' import ','from .'+name+' import ')
        s=s.replace('from common import HERE, sha','from .utils import HERE, sha')
        s=s.replace('import geometry as geo','from . import geometry as geo')
        s=s.replace('import geometry,detector','from . import geometry,detector')
        s=s.replace('import geometry\n','from . import geometry\n')
        return s
    copy('loop_utils.py','utils.py',lambda s:s.replace('Path(__file__).resolve().parent','Path(__file__).resolve().parents[1]'))
    for name in ('exact.py','geometry.py','detector.py','public_contract.py','pipeline.py','worlds.py'):
        copy(name,name,names)
    def connector(s):
        s=names(s)
        a=s.index('def credit_move(');b=s.index('def select(',a)
        s=s[:a]+'from .service import collect,credit_move\n\n'+s[b:]
        return s
    copy('connector.py','connector.py',connector)
    def executor(s):
        s=names(s).replace('from public_contract import','from .public_contract import')
        s=s.replace('class Executor:', 'from .service import collect,credit_move\n\nclass Executor:')
        s=s.replace('writer=None,initial=None):','writer=None,initial=None,technical=False):')
        s=s.replace('        self.nominal=','        self.technical=technical\n        self.nominal=',1)
        s=s.replace('def action(self,kind,to=None):','def action(self,kind,to=None,before_event=False):')
        s=s.replace("        if self.counts['execution_action_calls']>204:","        if self.counts['execution_action_calls']>212:")
        s=s.replace("        before=self.snapshot()\n        a=self.s['S']", "        assert self.technical or not before_event\n        assert kind in ('move','collect_here')\n        before=self.snapshot()\n        a=self.s['S']")
        s=s.replace("        credits=[]\n        if kind=='collect_here':", "        self.s['S']=a\n        end_open=probe['kind']=='detected' or before_event\n        credits=[]\n        if kind=='collect_here':")
        a=s.index("            self.counts['explicit_collect_checks']")
        b=s.index('        if a!=stop:',a)
        s=s[:a]+"            if probe['kind']!='detected':\n                credits=collect(self.s,self.counts,'execution')\n        else:\n            credits=credit_move(self.s,a,stop,self.counts,'execution',end_open)\n"+s[b:]
        s=s.replace('distance=certificate(length),squared_source=square,after=self.snapshot())',
                    'distance=certificate(length),squared_source=square,prefix_end_open=end_open,after=self.snapshot())')
        s=s.replace("        for endpoint in points[1:]:", "        collected=self.action('collect_here')\n        if collected['status']!='committed':\n            return collected['status']\n        for endpoint in points[1:]:")
        at=s.index('    def execute(')
        publish='''    def publish(self,targets=(),blocked=()):
        assert self.technical,'no real expansion/event extension'
        before=self.snapshot()
        extra=cellset(targets);new=cellset(blocked)
        assert extra<=self.nominal and new<=self.nominal
        self.s['P']|=extra
        self.truth|=new
        self.known|=new
        self.refresh()
        self.counts['technical_publications']+=1
        return self.append({'kind':'technical_publish','targets':cells(extra),'blocked':cells(new),
                            'before':before,'after':self.snapshot(),'status':'published',
                            'ordering':'settled_prefix_then_publish_then_explicit_collection'})

'''
        s=s[:at]+publish+s[at:]
        return s
    copy('executor.py','executor.py',executor)
    copy('postsrc/geometry.py','post/geometry.py')
    (PKG/'post/__init__.py').write_text('"""Namespaced conservative shortcut wrapper."""\n',encoding='utf-8')
    def engine(s):
        s=s.replace('import geometry as G','from . import geometry as G\nfrom .. import service as C')
        a=s.index('def credits(');b=s.index('def turns(',a)
        credit='''def credits(path,U,counters):
    seen=set();out=[]
    for p in sorted(U):
        if C.inside(path[0],p,counters,'post'):
            seen.add(p)
            out.append({'point':list(p),'edge':-1,'collect_here':True,
                        'witness':{'t':C.rat(0),'point':C.pt(path[0])}})
    for k,(a,b) in enumerate(zip(path,path[1:])):
        found=[]
        for p in sorted(U):
            counters['service_intersections']+=1
            evidence=C.intersection(a,b,p,counters,'post')
            if evidence is not None and p not in seen:
                t=evidence['witness']['t'];found.append((None,p,evidence))
        # Exact order is diagnostic witness order, not a claimed first internal time.
        from fractions import Fraction
        found.sort(key=lambda z:(Fraction(z[2]['witness']['t']['n'],z[2]['witness']['t']['d']),z[1]))
        for _,p,evidence in found:
            if p not in seen:
                out.append({'point':list(p),'edge':k,'evidence':evidence});seen.add(p)
    assert seen==U,('missing_credit',U-seen)
    return out

'''
        s=s[:a]+credit+s[b:]
        s=s.replace('credits(output,U,counts,G.hit)','credits(output,U,counts)')
        s=s.replace("'first_original':first,'first_actual':credited,'actual_order_changed':", "'locked_nominal_anchors':first,'credit_witnesses':credited,'witness_order_differs_from_locked_anchors':")
        return s
    copy('postsrc/engine.py','post/engine.py',engine)
    def observe(s):
        s=names(s).replace("engine.G.hit.__code__: 'post_hit'","engine.C.intersection.__code__: 'post_hit'")
        s=s.replace("            row = {'kind': kind,", "            if kind=='post_hit' and frame.f_locals.get('phase')!='post':\n                return None\n            row = {'kind': kind,")
        s=s.replace("kind == 'post_hit':\n                self.add", "kind == 'post_hit':\n                self.add")
        return s
    copy('observe.py','observe.py',observe)
    for name in ('_geometry.py','_h1.py','_post_geometry.py','_detect.py'):
        copy('diagonal_loop_audit_v01_20261022/'+name,'audit/'+name)
    (PKG/'audit/__init__.py').write_text('from ._audit import audit_one,audit_execution,load_auditor\n',encoding='utf-8')
    (PKG/'audit/_common.py').write_text('from ..utils import HERE\n',encoding='utf-8')
    def post_audit(s):
        s=s.replace('from . import _post_geometry as A','from . import _post_geometry as A\nfrom . import region as Z')
        s=s.replace("r['first_original']","r['locked_nominal_anchors']")
        s=s.replace("r['first_actual']","r['credit_witnesses']")
        s=s.replace("r['actual_order_changed']","r['witness_order_differs_from_locked_anchors']")
        s=s.replace("if points[0] in U:credit_candidates[points[0]]=(-1,Fraction(0))", "for p in sorted(U):\n        if Z.internal(points[0],p,counts):\n            credit_candidates[p]=(-1,Fraction(0),None)")
        a=s.index("            counts['service_intersections']+=1;t=A.hit")
        b=s.index('        sq=sum',a)
        s=s[:a]+'''            counts['service_intersections']+=1
            evidence=Z.intersection(points[k],points[k+1],q,counts)
            if evidence is not None:
                rtime=evidence['witness']['t'];when=(k,Fraction(rtime['n'],rtime['d']),evidence)
                if q not in credit_candidates or when[:2]<credit_candidates[q][:2]:
                    credit_candidates[q]=when
'''+s[b:]
        a=s.index("    actual=[{'point':");b=s.index('    def bounds(',a)
        s=s[:a]+'''    actual=[]
    for p,when in sorted(credit_candidates.items(),key=lambda z:(z[1][:2],z[0])):
        if when[0]==-1:
            actual.append({'point':list(p),'edge':-1,'collect_here':True,'witness':{'t':Z.rat(Fraction(0)),'point':Z.pt(points[0])}})
        else:
            actual.append({'point':list(p),'edge':when[0],'evidence':when[2]})
    assert actual==r['credit_witnesses']
    assert r['witness_order_differs_from_locked_anchors']==([x['point'] for x in original]!=[x['point'] for x in actual])
'''+s[b:]
        s=s.replace("'service_method':'earliest exact coordinate-parameter intersection per task'","'service_method':'independent strict-region boundary partition and interior witness per task'")
        return s
    copy('diagonal_loop_audit_v01_20261022/_post_saved.py','audit/_post_saved.py',post_audit)
    def audit(s):
        s=s.replace('from . import _detect as T','from . import _detect as T\nfrom . import region as Z')
        for a,b in [('A.collect(f)','Z.collect(f,c)'),('A.service(f,a,b,c)','Z.service(f,a,b,c)'),
                    ('A.collect(pred)','Z.collect(pred,c)'),('A.service(pred,s[\'S\'],q,c)','Z.service(pred,s[\'S\'],q,c)')]:
            s=s.replace(a,b)
        at=s.index("        c['independent_execution_commits_checked']+=1")
        publication='''        if record['kind']=='technical_publish':
            assert technical
            s['P']|=A.cellset(record['targets'])
            new=A.cellset(record['blocked'])
            truth|=new;known|=new
            s['F']=nominal-known;s['D']=s['P']-s['F']-s['H']
            ledger_snapshot_check(record['after'],s,known,last_motion,event_count,nonzero)
            assert record['status']=='published'
            tail=computed
            continue
'''
        s=s[:at]+publication+s[at:]
        a=s.index('        credits=[]',s.index('def audit_execution'))
        b=s.index('        assert credits==record',a)
        s=s[:a]+'''        end_open=record['prefix_end_open']
        assert technical or end_open==(kind=='detected')
        if record['kind']=='collect_here':
            assert a==b
            credits=[] if kind=='detected' else Z.collect(s,c)
        else:
            assert record['kind']=='move'
            credits=Z.service(s,a,stop,c,end_open)
'''+s[b:]
        s=s.replace("    assert not(s['H']&truth),'blocked_target_credited'", "    if not technical:\n        assert not(s['H']&truth),'blocked_target_credited'")
        # Added center-region post audit also supplies its distinct analytic-query ledger.
        marker="    c['independent_service_intersections']+=post_receipt['counts']['service_intersections']"
        s=s.replace(marker,marker+"\n    for key in ('independent_region_point_tests','independent_region_boundary_parameters'):\n        c[key]+=post_receipt['counts'].get(key,0)")
        return s
    copy('diagonal_loop_audit_v01_20261022/_audit.py','audit/_audit.py',audit)
    (HERE/'source_bindings.json').write_text(json.dumps(bindings,ensure_ascii=False,indent=2),encoding='utf-8')
    (HERE/'适配源码.diff').write_text('\n'.join(diffs),encoding='utf-8')
    # Lock mechanism-preserving source segments after namespace normalization.
    def segment(s,name):
        node=next(n for n in ast.parse(s).body if getattr(n,'name',None)==name)
        return ast.get_source_segment(s,node)
    checks={}
    for file,functions in [('pipeline.py',('GuardedCounter','grid','native_points','main_audit','run')),
                           ('connector.py',('select',)),('postsrc/engine.py',('first_original','split','turns'))]:
        target='post/engine.py' if file.startswith('postsrc') else file
        before=(OLD/file).read_text(encoding='utf-8')
        after=(PKG/target).read_text(encoding='utf-8')
        for name in functions:
            checks[target+':'+name]=segment(before,name)==segment(after,name)
    assert all(checks.values()),checks
    (HERE/'保留机制源码段.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
    print({'source_copies':len(bindings),'mechanism_checks':checks,'core_calls':0})

if __name__=='__main__':
    main()
