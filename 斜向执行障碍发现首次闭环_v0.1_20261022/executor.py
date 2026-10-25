"""Commit only flown prefixes. Truth is confined to this execution environment."""
from fractions import Fraction as Q
from copy import deepcopy
from collections import Counter
import json,hashlib
from exact import Expr,point,pt,rat,distance,certificate
from connector import cellset,cells
from public_contract import state_save
import geometry,detector

def digest(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()

class Executor:
    def __init__(self,public,private,writer=None,initial=None):
        self.nominal=cellset(public['F_nominal'])
        self.truth=cellset(private['O_truth'])
        assert len(self.truth)==1 and self.truth<=self.nominal
        self.writer=writer
        self.counts=Counter()
        self.records=[]
        self.tail='0'*64
        self.event_count=0
        self.nonzero_segments=0
        self.last_motion=None
        self.known=set()
        s={'S':tuple(Q(v) for v in public['start']),'h':None,'base':tuple(Q(v) for v in public['base']),
           'P':cellset(public['P']),'H':set(),'F':set(self.nominal),'D':set(),
           'E':Expr.number(public['E']),'M':Expr()}
        if initial:
            s['S']=point(initial['S'])
            s['h']=None if initial['h'] is None else point(initial['h'])
            s['H']=cellset(initial.get('H',[]))
            s['E']=Expr.load(initial.get('E',Expr.number(public['E']).save()))
            s['M']=Expr.load(initial.get('M',Expr().save()))
            self.known=cellset(initial.get('known',[]))
            self.event_count=int(bool(self.known))
        self.s=s
        self.refresh()
        self.initial=self.snapshot()

    def refresh(self):
        self.s['F']=self.nominal-self.known
        self.s['D']=self.s['P']-self.s['F']-self.s['H']

    def snapshot(self):
        return dict(state_save(self.s),known=cells(self.known),last_motion=deepcopy(self.last_motion),
                    event_count=self.event_count,nonzero_segments=self.nonzero_segments)

    def append(self,record):
        record=dict(index=len(self.records),previous_hash=self.tail,**record)
        record['record_hash']=digest(record)
        self.tail=record['record_hash']
        self.records.append(record)
        if self.writer:
            self.writer(record)
        return record

    def public_case(self,ident):
        s=self.s
        raw={'S':pt(s['S']),'h':None if s['h'] is None else pt(s['h']),
             'heading_status':'NO_PRIOR_MOTION' if s['h'] is None else 'KNOWN',
             'F':cells(s['F']),'P':cells(s['P']),'H':cells(s['H']),'D':cells(s['D']),
             'base':[int(v) for v in s['base']],'E':s['E'].save(),'M':s['M'].save()}
        return {'id':ident,'input':raw,'metadata':{'initial_targets':cells(s['P']),'predator':[-3,-3],
                  'old_route':[],'heading_source':deepcopy(self.last_motion) if self.last_motion else {'kind':'initialization_no_motion'},
                  'execution_log_tail':self.tail,'known_obstacles':cells(self.known),
                  'scope':'public_execution_state_only'}}

    def wait_plan(self,plan_id,route,source_hash,stub=False):
        self.counts['planning_wait_records']+=1
        before=self.snapshot()
        return self.append({'kind':'plan_wait','plan_id':plan_id,'before':before,'after':self.snapshot(),
              'predicted_route':route,'plan_output_sha256':source_hash,'fixed_stub':stub})

    def action(self,kind,to=None):
        self.counts['execution_action_calls']+=1
        if self.counts['execution_action_calls']>204:
            raise RuntimeError('execution_action_cap')
        before=self.snapshot()
        a=self.s['S']
        b=a if kind=='collect_here' else point(to)
        probe=detector.probe(a,b,self.truth,self.known,self.counts)
        sensor={'kind':probe['kind'],'t':rat(probe['t']),
                'cell':None if probe['cell'] is None else list(map(int,probe['cell']))}
        record={'kind':kind,'before':before,'proposed':[pt(a),pt(b)],'sensor':sensor,'credits':[]}
        if probe['kind'].startswith('unsafe'):
            self.counts['unsafe_refusals']+=1
            record.update(status=probe['kind'],after=self.snapshot(),distance=certificate(Expr()),squared_source=rat(0))
            return self.append(record)
        t=probe['t'] if probe['kind']=='detected' else Q(1)
        stop=tuple(a[k]+t*(b[k]-a[k]) for k in (0,1))
        length,square=distance(a,stop,self.counts,'execution')
        if (self.s['E']-length).sign()<0:
            self.counts['resource_refusals']+=1
            record.update(status='resource_refused',after=self.snapshot(),distance=certificate(Expr()),squared_source=rat(0))
            return self.append(record)
        if a!=stop and self.nonzero_segments>=1000:
            raise RuntimeError('nonzero_execution_segment_cap')
        if not geometry.legal(self.nominal-self.truth,a,stop,self.counts,'execution_truth'):
            raise RuntimeError('actual_prefix_not_truth_safe')
        credits=[]
        if kind=='collect_here':
            self.counts['explicit_collect_checks']+=1
            if probe['kind']!='detected' and a in self.s['P']&self.s['F']-self.s['H']:
                credits=[{'kind':'collect_here','cell':list(map(int,a)),'t':rat(0)}]
        else:
            for cell in sorted(self.s['P']&self.s['F']-self.s['H']):
                hit=geometry.hit(a,b,cell,self.counts,'execution')
                if hit is not None and hit>0 and (hit<t if probe['kind']=='detected' else hit<=t):
                    credits.append({'kind':'arrival','cell':list(map(int,cell)),'t':rat(hit)})
            credits.sort(key=lambda x:(Q(x['t']['n'],x['t']['d']),x['cell']))
        for credit in credits:
            self.s['H'].add(tuple(credit['cell']))
        if a!=stop:
            self.nonzero_segments+=1
            self.s['h']=tuple(v-w for v,w in zip(stop,a))
            self.last_motion={'action_index':len(self.records),'a':pt(a),'b':pt(stop),'vector':pt(self.s['h'])}
        self.s['S'],self.s['E'],self.s['M']=stop,self.s['E']-length,self.s['M']+length
        if probe['kind']=='detected':
            assert probe['cell'] not in self.known and self.event_count<1
            self.known.add(probe['cell'])
            self.event_count+=1
            self.counts['first_discoveries']+=1
        self.refresh()
        record.update(status='detected' if probe['kind']=='detected' else 'committed',
                      actual=[pt(a),pt(stop)],stop_parameter=rat(t),credits=credits,
                      distance=certificate(length),squared_source=square,after=self.snapshot())
        return self.append(record)

    def execute(self,route):
        points=[point(p) for p in route]
        assert points and points[0]==self.s['S']
        for endpoint in points[1:]:
            record=self.action('move',pt(endpoint))
            if record['status']!='committed':
                return record['status']
        return 'completed_route'

    def completed(self):
        return self.s['S']==self.s['base'] and not(self.s['P']&self.s['F']-self.s['H'])
