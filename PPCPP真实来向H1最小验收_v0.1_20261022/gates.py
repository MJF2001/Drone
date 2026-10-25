"""Preregistered pure scoring and hand-written edge tests; never import planners."""
from pathlib import Path
import json,sys,traceback,hashlib
from fractions import Fraction

HERE=Path(__file__).resolve().parent
CASES={
 'G01':['east','north','west','south'],
 'G02':['NE','SE','NW','SW'],
 'G03':['integer_scale','rational_scale','non_equal_components'],
 'G04':['axial_reverse','diagonal_reverse'],
 'G05':['symmetric_exact_tie','sub_float_non_tie','whole_score_before_heading','square_norm_tie'],
 'G06':['no_motion','unknown','invalid_vectors','missing_evidence'],
 'G07':['known_zero_edge','no_motion_zero_edge','rational_wait'],
 'G08':['bend_with_zero','recovery_then_score'],
}

def preregister():
    p=HERE/'技术门槛预登记.json'
    assert not p.exists()
    data=dict(classes=CASES,cases=sum(map(len,CASES.values())),max_cases_per_class=4,max_rounds=3,
      expected='G01 exact axis 1/.5/0; G02 diagonal B=sign component,N=2; G03 canonical direction/score/winner invariant; G04 rs(h)+rs(-h)=1; G05 exact ties use coordinate and distinct sub-float scores do not tie, full score priority and square norm; G06 no-motion rs0, UNKNOWN/invalid/no source rejected; G07 zero edge preserves state; G08 last nonzero edge controls next score.',
      real_planner_calls=0)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def main():
    prereg=json.loads((HERE/'技术门槛预登记.json').read_text(encoding='utf8'));assert prereg['classes']==CASES
    attempt=1+len(list((HERE/'tech').glob('attempt_*_result.json')));assert attempt<=3
    snapshot={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in ('h1_direction.py','h1_rewards.py','gates.py','independent_audit.py')}
    for name in snapshot:(HERE/'tech'/('attempt_'+str(attempt)+'_'+name)).write_bytes((HERE/name).read_bytes())
    rows=[];counts={};failure=None
    try:
        import h1_direction as H
        import h1_rewards as R
        from independent_audit import certified_winner
        tracked={H.parse_heading.__code__:'parse_heading',H.after_edge.__code__:'after_edge',R.reward_options.__code__:'reward_options',R.choose_neighbor.__code__:'choose_neighbor',R.compare_certificates.__code__:'exact_comparisons'}
        def profile(frame,event,arg):
            if event=='call' and frame.f_code in tracked:
                key=tracked[frame.f_code];counts[key]=counts.get(key,0)+1
        sys.setprofile(profile)
        cells={(1,0),(0,1),(-1,0),(0,-1)};free=cells|{(0,0)}
        def state(v):return H.parse_heading(dict(status='KNOWN',vector=v,source=dict(kind='handwritten_technical')))
        def opts(v):return R.reward_options((0,0),state(v),cells,free,(-3,0),(2.,.5))
        def check(g,c,fn):
            fn();rows.append(dict(group=g,case=c,passed=True))
        def rejects(obj):
            try:H.parse_heading(obj)
            except H.HeadingError:return
            raise AssertionError('invalid heading accepted')
        for label,v in zip(CASES['G01'],([1,0],[0,1],[-1,0],[0,-1])):
            def test(v=v):
                for z in opts(v):
                    d=z['cell'];assert z['straight_reward']==(v[0]*d[0]+v[1]*d[1]+1)/2 and 'h1_certificate' not in z
            check('G01',label,test)
        for label,v in zip(CASES['G02'],([1,1],[1,-1],[-1,1],[-1,-1])):
            def test(v=v):
                rows0=opts(v)
                for z in rows0:assert z['h1_certificate']['N']==2 and z['h1_certificate']['B']==sum(a*b for a,b in zip(v,z['cell']))
                assert tuple(R.choose_neighbor(rows0))==certified_winner(rows0)[0]
            check('G02',label,test)
        for label,a,b in zip(CASES['G03'],([1,1],[1,1],[1,2]),([2,2],['1/3','1/3'],['2/7','4/7'])):
            check('G03',label,lambda a=a,b=b: equality(opts(a),opts(b),R))
        for label,v in zip(CASES['G04'],([1,0],[1,1])):
            def test(v=v):
                a,b=opts(v),opts([-x for x in v])
                for x,y in zip(a,b):
                    if 'h1_certificate' in x:assert x['h1_certificate']['B']==-y['h1_certificate']['B']
                    else:assert x['straight_reward']+y['straight_reward']==1
            check('G04',label,test)
        fixtures=[
          [dict(cell=(0,1),h1_certificate=dict(A='1',B=1,N=2)),dict(cell=(1,0),h1_certificate=dict(A='1',B=1,N=2))],
          [dict(cell=(0,1),h1_certificate=dict(A='1',B=1,N=2)),dict(cell=(1,0),h1_certificate=dict(A=str(1+Fraction(1,2**60)),B=1,N=2))],
          [dict(cell=(0,1),h1_certificate=dict(A='10',B=-1,N=2)),dict(cell=(1,0),h1_certificate=dict(A='0',B=1,N=2))],
          [dict(cell=(0,1),h1_certificate=dict(A='1',B=0,N=25)),dict(cell=(1,0),h1_certificate=dict(A='0',B=5,N=25))],
        ]
        for label,data,goal in zip(CASES['G05'],fixtures,((0,1),(1,0),(0,1),(0,1))):
            def test(data=data,goal=goal):assert R.choose_neighbor(data)==goal==certified_winner(data)[0]
            check('G05',label,test)
        no_motion=dict(status='NO_PRIOR_MOTION',vector=None,source=dict(kind='initialization_no_motion'))
        def none_test():
            s=H.parse_heading(no_motion);o=R.reward_options((0,0),s,cells,free,(-3,0),(2.,.5));assert all(z['straight_reward']==0.0 for z in o)
        check('G06','no_motion',none_test)
        check('G06','unknown',lambda:rejects(dict(status='UNKNOWN',source=dict(kind='handwritten_technical'))))
        def bad_vectors():
            for v in ([0,0],[float('nan'),1],[float('inf'),1],['1/0',1]):rejects(dict(status='KNOWN',vector=v,source=dict(kind='handwritten_technical')))
        check('G06','invalid_vectors',bad_vectors)
        check('G06','missing_evidence',lambda:rejects(dict(status='KNOWN',vector=[1,1])))
        for label,s in zip(CASES['G07'],(state([1,1]),H.parse_heading(no_motion),state(['2/3','1/3']))):
            def test(s=s):assert H.after_edge(s,(0,0),(0,0),0)==s
            check('G07',label,test)
        def bend():
            s=state([1,1]);path=[(0,0),(0,1),(1,1),(1,1),(1,2)]
            for i,(a,b) in enumerate(zip(path,path[1:]),1):s=H.after_edge(s,a,b,i)
            assert s['primitive']==[0,1] and s['source']==dict(kind='predicted_route_edge',start=[1,1],end=[1,2],end_index=4)
        check('G08','bend_with_zero',bend)
        def recovery_score():
            s=state([1,1])
            for i,(a,b) in enumerate(zip(((0,0),(0,1)),((0,1),(1,1))),1):s=H.after_edge(s,a,b,i)
            f={(1,1),(2,1),(1,2)};o=R.reward_options((1,1),s,f-{(1,1)},f,(-3,0),(2.,.5))
            assert s['primitive']==[1,0] and next(x for x in o if x['cell']==(2,1))['straight_reward']==1
        check('G08','recovery_then_score',recovery_score)
    except BaseException as ex:failure=dict(reason=repr(ex),traceback=traceback.format_exc())
    finally:sys.setprofile(None)
    result=dict(attempt=attempt,passed=failure is None and len(rows)==prereg['cases'],cases=rows,failure=failure,
      source_hashes=snapshot,pure_function_calls=counts,real_entries=0,core_calls=0,graph_calls=0)
    (HERE/'tech'/f'attempt_{attempt}_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(attempt=attempt,passed=result['passed'],cases=len(rows),failure=failure,pure_function_calls=counts),ensure_ascii=False))
    if not result['passed']:raise SystemExit(1)

def equality(a,b,R):
    assert a==b and R.choose_neighbor(a)==R.choose_neighbor(b)

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='register':preregister()
    else:main()
