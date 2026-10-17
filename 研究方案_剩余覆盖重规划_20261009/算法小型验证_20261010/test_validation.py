import unittest
from dataclasses import replace
from model import Snapshot, Geometry, NoPath, DeadlineExceeded, capture_route
from audit import audit, environment_check
from planners import solve, two_opt, sequence_cost, components, old_packets, orient_blocks, block_cost
from itertools import product
from scenarios import build_case, rectangle, flight_domain, serialize, deserialize


class GeometryTests(unittest.TestCase):
    def test_astar_must_detour(self):
        s = Snapshot('detour', frozenset(rectangle(0, 0, 5, 3)-{(2, 1)}),
                     frozenset(), frozenset(), (0, 1), (4, 1), ())
        path = Geometry(s).path(s.current, s.base)
        self.assertEqual(len(path)-1, 6)
        self.assertNotIn((2, 1), path)

    def test_version_change_cannot_reuse_old_connection(self):
        s = Snapshot('version', frozenset(rectangle(0, 0, 5, 3)),
                     frozenset(), frozenset(), (0, 1), (4, 1), ())
        self.assertEqual(Geometry(s).distance(s.current, s.base), 4)
        s2 = replace(s, free=s.free-{(2, 1)})
        self.assertEqual(Geometry(s2).distance(s2.current, s2.base), 6)

    def test_target_under_no_fly_cell_not_automatically_deleted(self):
        free = frozenset(rectangle(0, 0, 3, 3)-{(1, 1)})
        s = Snapshot('observe_adjacent', free, frozenset({(1, 1)}), frozenset(),
                     (0, 1), (0, 1), ())
        self.assertIsNone(environment_check(s))
        for name in ('P1', 'P2', 'P3', 'P4'):
            result = solve(s, name)
            self.assertTrue(audit(s, result.route)['valid'])
            self.assertEqual(s.targets, frozenset({(1, 1)}))


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.s = Snapshot('audit', frozenset(rectangle(0, 0, 4, 3)),
                          frozenset({(2, 1)}), frozenset(), (0, 1), (0, 1), (), radius=0)

    def test_illegal_jump(self):
        report = audit(self.s, ((0, 1), (2, 1), (0, 1)))
        self.assertIn('illegal_step', report['errors'])

    def test_omission_and_no_return(self):
        report = audit(self.s, ((0, 1), (1, 1)))
        self.assertIn('coverage_omission', report['errors'])
        self.assertIn('missing_return', report['errors'])

    def test_budget_failure_is_not_environment_infeasibility(self):
        s = replace(self.s, distance_budget=1)
        self.assertIsNone(environment_check(s))
        report = audit(s, ((0, 1), (1, 1), (2, 1), (1, 1), (0, 1)))
        self.assertIn('distance_budget_exceeded', report['errors'])

    def test_physical_capture_includes_transit_and_return(self):
        report = audit(self.s, ((0, 1), (1, 1), (2, 1), (1, 1), (0, 1)))
        self.assertTrue(report['valid'])
        self.assertEqual(report['length'], 4)


class ScenarioTests(unittest.TestCase):
    def test_new_targets_not_retroactively_covered(self):
        s, meta = build_case(18, 6, .8, 'corner')
        initial_targets = set(map(tuple, meta['initial_targets']))
        self.assertTrue(s.covered <= initial_targets)
        self.assertTrue(s.targets-initial_targets)
        self.assertFalse((s.targets-initial_targets) & s.covered)
        self.assertEqual(deserialize(serialize(s, meta)), s)

    def test_infeasible_cases_preserve_all_targets(self):
        for family, reason in [('closed_channel', 'target_unobservable'),
                               ('unobservable_target', 'target_unobservable')]:
            s, _ = build_case(18, 6, .2, family)
            self.assertEqual(environment_check(s), reason)
            for name in ('P1', 'P2', 'P3', 'P4'):
                result = solve(s, name)
                self.assertEqual(result.status, 'environment_infeasible')
                self.assertEqual(len(s.targets), 108)

    def test_all_five_families_both_algorithms(self):
        for family in ('no_change', 'straight', 'corner', 'local_obstacle', 'channel_obstacle'):
            s, _ = build_case(18, 6, .5, family)
            self.assertIsNone(environment_check(s), family)
            for name in ('P1', 'P2', 'P3', 'P4'):
                with self.subTest(family=family, algorithm=name):
                    result = solve(s, name)
                    report = audit(s, result.route)
                    self.assertTrue(report['valid'], (result, report))

    def test_timeout_does_not_claim_completion(self):
        s, _ = build_case(18, 6, .2, 'corner')
        result = solve(s, 'P2', time_limit=0)
        self.assertEqual(result.status, 'timeout')
        self.assertFalse(result.route)
        self.assertFalse(audit(s, result.route)['valid'])

    def test_stronger_initial_route_is_shared_and_valid(self):
        s, _ = build_case(24, 9, .5, 'no_change', initial_policy='optimized')
        self.assertTrue(audit(s, s.old_route)['valid'])
        for name in ('P1', 'P2'):
            self.assertTrue(audit(s, solve(s, name).route)['valid'])

    def test_valid_old_suffix_is_common_no_regression_candidate(self):
        for policy in ('snake', 'optimized'):
            s, _ = build_case(24, 9, .5, 'no_change', initial_policy=policy)
            for name in ('P1', 'P2'):
                result = solve(s, name)
                self.assertTrue(audit(s, result.route)['valid'])
                self.assertLessEqual(len(result.route), len(s.old_route))

    def test_no_budget_feasible_incumbent_is_not_claimed_completed(self):
        s = replace(self_small_snapshot(), distance_budget=1)
        for name in ('P1', 'P2'):
            result = solve(s, name)
            self.assertEqual(result.status, 'planning_failure')
            self.assertFalse(result.route)

    def test_grouping_uses_target_adjacency(self):
        groups = components({(0, 0), (1, 0), (3, 0), (3, 1)})
        self.assertEqual({frozenset(x) for x in groups},
                         {frozenset({(0, 0), (1, 0)}), frozenset({(3, 0), (3, 1)})})

    def test_orientation_dp_matches_exhaustive_binary_choices(self):
        s = self_small_snapshot()
        g = Geometry(s)
        blocks = [((1, 0), (2, 0)), ((3, 1), (3, 2)), ((0, 2), (1, 2))]
        exact = min(block_cost(g, [tuple(reversed(b)) if reverse else b
                                  for b, reverse in zip(blocks, flags)])
                    for flags in product((False, True), repeat=len(blocks)))
        self.assertEqual(block_cost(g, orient_blocks(g, blocks)), exact)

    def test_packets_do_not_include_blocked_pose_or_cross_turns(self):
        s, _ = build_case(24, 9, .2, 'channel_obstacle')
        g = Geometry(s)
        packets, left = old_packets(g)
        covered = set(g.views[s.current]) | set(s.covered)
        for block in packets:
            self.assertTrue(set(block) <= s.free)
            steps = {(b[0]-a[0], b[1]-a[1]) for a, b in zip(block, block[1:])}
            self.assertLessEqual(len(steps), 1)
            for p in block:
                covered.update(g.views[p])
        self.assertEqual(left, s.targets-covered)

    def test_new_prototypes_empty_and_budget_and_timeout(self):
        for name in ('P3', 'P4'):
            s = self_small_snapshot()
            self.assertEqual(solve(s, name, 0).status, 'timeout')
            self.assertEqual(solve(replace(s, distance_budget=1), name).status, 'planning_failure')
            done = replace(s, covered=s.targets)
            self.assertTrue(audit(done, solve(done, name).route)['valid'])


def self_small_snapshot():
    return Snapshot('budget', frozenset(rectangle(0, 0, 4, 3)),
                    frozenset({(3, 1)}), frozenset(), (0, 1), (0, 1), (), radius=0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
