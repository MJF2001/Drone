"""Dynamic public state adapter; approved arithmetic and known-heading selector reused."""
from fractions import Fraction as Q
from exact import Expr,Refusal,point,pt,rat,certificate
from connector import parse as known_parse,select as known_select,cellset,cells
import geometry

def state_save(s):
    return {'S':pt(s['S']),'h':None if s['h'] is None else pt(s['h']),
            'F':cells(s['F']),'P':cells(s['P']),'H':cells(s['H']),'D':cells(s['D']),
            'base':[int(v) for v in s['base']],'E':certificate(s['E']),'M':certificate(s['M'])}

def parse(raw,c):
    if raw.get('h') is not None:
        if raw.get('heading_status')!='KNOWN':
            raise Refusal('known_heading_status')
        return known_parse(raw,c)
    c['parse']+=1
    if not {'S','h','F','P','H','D','base','E','M','heading_status'}<=set(raw):
        raise Refusal('missing_field')
    s={name:cellset(raw[name]) for name in ('F','P','H','D')}
    s.update(S=point(raw['S']),h=None,base=point(raw['base'],True),E=Expr.load(raw['E']),M=Expr.load(raw['M']))
    if raw['heading_status']!='NO_PRIOR_MOTION' or s['S']!=s['base']:
        raise Refusal('no_motion_requires_initial_grid_base')
    if not s['F'] or len(s['F'])>25 or len(s['P'])>12 or not s['base'] in s['F']:
        raise Refusal('public_state_bound')
    if any(abs(v)>100 for p in s['F']|s['P'] for v in p) or not s['H']<=s['P']:
        raise Refusal('public_state_values')
    if s['D']!=s['P']-s['F']-s['H'] or s['E'].sign()<0 or s['M'].sign()<0:
        raise Refusal('public_state_ledger')
    if not geometry.legal(s['F'],s['S'],s['S'],c,'input'):
        raise Refusal('public_stop_not_in_open_domain')
    return s

def select(s,c):
    if s['h'] is not None:
        return known_select(s,c)
    # A zero-distance initial grid entry is uniquely nearest without inventing h.
    q=s['S']
    assert q==s['base'] and q in s['F'] and all(v.denominator==1 for v in q)
    c['initial_zero_entry']+=1
    c['candidate_checks']+=1
    zero=Expr()
    row={'q':[int(v) for v in q],'squared':rat(0),'dot':None,'legal':True,'affordable':True,
         'length':certificate(zero),'squared_source':rat(0),'initial_zero_entry':True}
    return (q,Q(0),None,zero),[row]

def heading(pred,s,case,input_sha):
    if pred['h'] is None:
        assert s['h'] is None and pred['S']==s['base']
        return {'status':'NO_PRIOR_MOTION','vector':None,
                'source':{'kind':'initialization_no_motion','execution_log_tail':case['metadata']['execution_log_tail']}}
    vector=[v.numerator if v.denominator==1 else str(v) for v in pred['h']]
    # Frozen H1 supports this technical-source enum. Vector provenance is actual
    # committed simulation motion, not a made-up previous grid neighbor.
    return {'status':'KNOWN','vector':vector,
        'source':{'kind':'synthetic_direction_fixture','scope':'technical_world_executed_prefix',
                  'snapshot_id':case['id'],'snapshot_sha256':input_sha,
                  'meaning':'paid_predicted_gamma_direction' if pred['S']!=s['S'] else 'last_committed_nonzero_direction',
                  'executed_heading':None if s['h'] is None else pt(s['h']),
                  'execution_evidence':case['metadata']['heading_source'],
                  'execution_log_tail':case['metadata']['execution_log_tail']}}
