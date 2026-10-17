from pathlib import Path

d=Path(__file__).parent
text=(d/'structure_candidates.py').read_text(encoding='utf-8')
text=text.replace('from audit import audit','from unified_geometry import UnifiedGeometry, single_cell_audit as audit')
text=text.replace('geometry_class=Geometry','geometry_class=UnifiedGeometry')
start=text.index('        ds = {current:0}')
end=text.index('            if candidate < best[p]:',start)
text=text[:start]+'''        for p in sorted(remaining):
            candidate = g.distance(current,p),current
'''+text[end:]
old="""        if route and audit(s,route)['valid'] and (best is None or len(route)<len(best)):
            best,source=tuple(route),label"""
new="""        valid=route and audit(s,route)['valid']
        g.check_time()
        if valid and (best is None or len(route)<len(best)):
            best,source=tuple(route),label
            detail.setdefault('improvements',[]).append({'elapsed':time.perf_counter()-begin,
                'steps':len(route)-1,'source':label})"""
assert old in text
text=text.replace(old,new)
(d/'unified_candidates.py').write_text(text,encoding='utf-8')
