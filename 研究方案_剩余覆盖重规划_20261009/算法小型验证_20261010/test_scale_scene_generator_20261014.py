import json
from pathlib import Path
import tempfile
import unittest
from collections import deque
from scale_scene_generator_20261014 import (rect,layout,extension,initial_targets,
    path,scan_route,checkpoint,choose_obstacle,make_case,route_audit,generate,reflect)
from prepare_scale_design_20261014 import tables


def independent_bfs(free, start):
    result = {start:0}; todo = deque([start])
    while todo:
        x,y = todo.popleft()
        for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if p in free and p not in result:
                result[p]=result[x,y]+1;todo.append(p)
    return result


class SceneTests(unittest.TestCase):
    def setUp(self):
        maps, self.rows = tables()
        self.maps = [m for m in maps if m['split']=='development']
        self.p = self.maps[0]
        self.free,self.old,self.base = layout(self.p)
        self.route = scan_route(self.free,self.old,self.base,'H')
        self.state = checkpoint(self.old,self.route,50)
        self.rs = [s for s in self.rows if s['map_id']==self.p['map_id'] and
                   s['history']=='H' and s['progress_percent']==50]

    def test_rectangle_half_open(self):
        self.assertEqual(rect(-1,2,2,2),{(-1,2),(0,2),(-1,3),(0,3)})

    def test_canonical_shortest_paths(self):
        free=rect(0,0,6,5)-{(2,1),(2,2),(2,3)}
        for a in sorted(free):
            ds=independent_bfs(free,a)
            for b in sorted(free):
                route=path(free,a,b)
                self.assertEqual(len(route)-1,ds[b])
                self.assertEqual(route,tuple(reversed(path(free,b,a))))
                self.assertTrue(set(route)<=free)

    def test_invalid_endpoint_and_disconnected(self):
        with self.assertRaisesRegex(ValueError,'endpoint_not_free'):path({(0,0)},(0,0),(1,0))
        with self.assertRaisesRegex(ValueError,'no_path'):path({(0,0),(2,0)},(0,0),(2,0))

    def test_hand_counted_initial_shapes(self):
        for p in self.maps:
            L,W,A = p['length'],p['width'],p['arm']
            count=L*W+A*W+2*p['extra_width']*(p['widen_stop']-p['widen_start'])
            self.assertEqual(len(initial_targets(p)),count)

    def test_domain_contains_all_event_choices(self):
        for p in self.maps:
            free,old,base=layout(p)
            self.assertIn(base,free); self.assertTrue(old<=free)
            for percent in (20,40):
                for kind,turn in (('straight',None),('corner','left'),('corner','right')):
                    extra,_=extension(p,percent,kind,turn)
                    self.assertTrue(extra<=free);self.assertFalse(extra&old)

    def test_minimum_corner_clip_recorded(self):
        p=self.maps[1]  # L12 W5: nominal 20% below the minimal elbow+arm.
        extra,info=extension(p,20,'corner','left')
        self.assertTrue(info['minimum_corner_size_clipped'])
        self.assertEqual(len(extra),30)
        self.assertEqual(info['actual_fraction'],.5)

    def test_reflection_synthetic_not_holdout(self):
        p=dict(self.p,reflect_y=True)
        free,old,base=layout(p)
        self.assertEqual(old,{reflect(x,p) for x in self.old})
        self.assertEqual(free,{reflect(x,p) for x in self.free})
        self.assertEqual(base,reflect(self.base,p))

    def test_history_progress_and_suffix(self):
        for h in ('H','V'):
            route=scan_route(self.free,self.old,self.base,h)
            for percent in (25,50,75):
                state=checkpoint(self.old,route,percent)
                self.assertEqual(state['covered'],self.old&set(state['prefix']))
                self.assertEqual(state['prefix']+state['old_route'][1:],route)
                self.assertGreaterEqual(100*len(state['covered']),percent*len(self.old))
                previous=self.old&set(state['prefix'][:-1])
                self.assertLess(100*len(previous),percent*len(self.old))

    def test_reproducible_obstacle_selection(self):
        row=next(s for s in self.rs if s['event']=='obstacle')
        a=choose_obstacle(self.p,self.free,self.old,self.base,self.state,row)
        b=choose_obstacle(self.p,self.free,self.old,self.base,self.state,row)
        self.assertEqual(a,b);self.assertIsNotNone(a[0])
        self.assertFalse(a[0]&{self.base,self.state['current']})
        self.assertLessEqual(len(a[1]['attempts']),64)

    def test_shared_obstacle_and_event_bookkeeping(self):
        row=next(s for s in self.rs if s['event']=='obstacle')
        obs=choose_obstacle(self.p,self.free,self.old,self.base,self.state,row)
        seen={}
        for r in self.rs:
            entry,data=make_case(self.p,self.free,self.old,self.base,self.state,r,obs)
            self.assertEqual(entry['status'],'generated')
            s,witness=data;seen[r['event']]=s
            points=lambda key:set(map(tuple,s[key]))
            meta=s['metadata'];blocked=set(map(tuple,meta['obstacles']))
            published=set(map(tuple,meta['published_targets']));covered=points('covered')
            self.assertEqual(set(map(tuple,meta['deferred_targets'])),(published-covered)&blocked)
            self.assertEqual(points('targets'),published-blocked)
            self.assertEqual(points('free')|blocked,self.free)
            self.assertEqual(s['radius'],0)
            self.assertTrue(route_audit(points('free'),points('targets'),covered,
                tuple(s['current']),tuple(s['base']),witness,s['distance_budget'])['valid'])
        for event in ('obstacle','straight_obstacle','corner_obstacle'):
            self.assertEqual(seen[event]['metadata']['obstacles'],sorted(obs[0]))
        self.assertEqual(seen['straight']['metadata']['extension'],seen['straight_obstacle']['metadata']['extension'])
        self.assertEqual(seen['corner']['metadata']['extension'],seen['corner_obstacle']['metadata']['extension'])

    def test_generation_failure_is_preserved(self):
        row=next(s for s in self.rs if s['event']=='obstacle')
        entry,data=make_case(self.p,self.free,self.old,self.base,self.state,row,
                             (None,{'failure':'placement_attempts_exhausted'}))
        self.assertIsNone(data);self.assertEqual(entry['status'],'generation_failure')

    def test_auditor_rejects_invalid_routes(self):
        self.assertFalse(route_audit(self.free,self.old,set(),self.base,self.base,[])['valid'])
        self.assertFalse(route_audit(self.free,self.old,set(),self.base,self.base,[self.base])['valid'])
        r=(self.base,(0,0),self.base)
        self.assertIn('illegal_step',route_audit(self.free,{(0,0)},set(),self.base,self.base,r)['errors'])

    def test_empty_targets_still_return(self):
        from scale_scene_generator_20261014 import expand
        current=(1,1);base=(0,0);free=rect(0,0,3,3)
        route=expand(free,set(),set(),current,base,[])
        self.assertTrue(route_audit(free,set(),set(),current,base,route)['valid'])
        self.assertEqual(len(route)-1,2)

    def test_historical_coverage_is_not_erased_by_obstacle(self):
        row=next(s for s in self.rs if s['event']=='obstacle')
        covered=self.state['covered'];current=self.state['current']
        historical=min(covered-{current,self.base})
        unvisited=min(self.old-covered-{current,self.base})
        blocked=frozenset((historical,unvisited))
        entry,data=make_case(self.p,self.free,self.old,self.base,self.state,row,
                             (blocked,{'attempts':[]}))
        self.assertEqual(entry['status'],'generated')
        snapshot,_=data
        self.assertIn(historical,set(map(tuple,snapshot['covered'])))
        self.assertNotIn(historical,set(map(tuple,snapshot['free'])))
        self.assertEqual(snapshot['metadata']['deferred_targets'],[unvisited])

    def test_canonical_tie_matches_frozen_geometry(self):
        # Read only the stdlib model, not a planner or its native dependencies.
        import importlib.util
        import sys
        from types import SimpleNamespace
        source=Path(__file__).parent/'frozen_baselines/v2_20261012/source/model.py'
        spec=importlib.util.spec_from_file_location('_scale_frozen_reference_model',source)
        module=importlib.util.module_from_spec(spec)
        sys.modules[spec.name]=module;spec.loader.exec_module(module)
        free=rect(0,0,5,5)-{(2,1),(2,2),(2,3)}
        s=SimpleNamespace(current=(0,0),base=(0,0),targets=set(),free=free,radius=0)
        geometry=module.Geometry(s)
        for a in sorted(free):
            for b in sorted(free):
                lo,hi=sorted((a,b));reference=geometry.path(lo,hi)
                expected=reference if a==lo else tuple(reversed(reference))
                self.assertEqual(path(free,a,b),expected)

    def test_output_directory_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'existing';p.mkdir();(p/'keep.txt').write_text('keep')
            with self.assertRaises(FileExistsError):generate(p,'small')
            self.assertEqual((p/'keep.txt').read_text(),'keep')


if __name__=='__main__':unittest.main()
