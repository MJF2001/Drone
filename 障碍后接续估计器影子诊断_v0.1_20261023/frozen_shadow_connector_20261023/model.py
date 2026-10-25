"""Shared, discrete geometry. No vision, dynamics, or physical energy claims."""
from dataclasses import dataclass
from collections import deque
import heapq
import time

Point = tuple[int, int]


def adjacent(p):
    x, y = p
    return ((x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1))


def footprint(p, targets, radius=1):
    x, y = p
    return {(a, b) for a in range(x-radius, x+radius+1)
            for b in range(y-radius, y+radius+1) if (a, b) in targets}


@dataclass(frozen=True)
class Snapshot:
    name: str
    free: frozenset[Point]
    targets: frozenset[Point]
    covered: frozenset[Point]
    current: Point
    base: Point
    old_route: tuple[Point, ...]
    radius: int = 1
    distance_budget: int = 100000


class NoPath(Exception):
    pass


class DeadlineExceeded(Exception):
    pass


class Geometry:
    def __init__(self, snapshot, deadline=float('inf')):
        self.s = snapshot
        self.deadline = deadline
        self.cache = {}
        self.searches = 0
        self.check_time()
        if snapshot.current not in snapshot.free:
            raise NoPath('current_not_free')
        self.reachable = {snapshot.current}
        queue = deque([snapshot.current])
        while queue:
            self.check_time()
            for q in adjacent(queue.popleft()):
                if q in snapshot.free and q not in self.reachable:
                    self.reachable.add(q)
                    queue.append(q)
        self.views = {}
        for p in sorted(self.reachable):
            self.check_time()
            self.views[p] = footprint(p, snapshot.targets, snapshot.radius)

    def check_time(self):
        if time.perf_counter() > self.deadline:
            raise DeadlineExceeded()

    def precheck(self):
        if self.s.base not in self.reachable:
            return 'base_unreachable'
        visible = set().union(*self.views.values()) if self.views else set()
        if self.s.targets - self.s.covered - visible:
            return 'target_unobservable'
        return None

    def path(self, start, goal):
        self.check_time()
        if (start, goal) in self.cache:
            return self.cache[start, goal]
        if start not in self.reachable or goal not in self.reachable:
            raise NoPath('endpoint_unreachable')
        self.searches += 1
        h = lambda p: abs(p[0]-goal[0]) + abs(p[1]-goal[1])
        queue = [(h(start), 0, start)]
        cost, parent = {start: 0}, {}
        while queue:
            self.check_time()
            _, distance, p = heapq.heappop(queue)
            if distance != cost[p]:
                continue
            if p == goal:
                route = [goal]
                while route[-1] != start:
                    route.append(parent[route[-1]])
                route = tuple(reversed(route))
                self.cache[start, goal] = route
                self.cache[goal, start] = tuple(reversed(route))
                return route
            for q in adjacent(p):
                if q in self.s.free and distance+1 < cost.get(q, float('inf')):
                    cost[q], parent[q] = distance+1, p
                    heapq.heappush(queue, (distance+1+h(q), distance+1, q))
        raise NoPath('no_path')

    def distance(self, a, b):
        return len(self.path(a, b))-1

    def expand(self, visits):
        """Skip a visit only if its full assigned footprint is already covered."""
        route = [self.s.current]
        covered = set(self.s.covered) | self.views[self.s.current]
        for p in visits:
            self.check_time()
            if not self.views[p] - covered:
                continue
            extension = self.path(route[-1], p)
            route.extend(extension[1:])
            for q in extension:
                covered.update(self.views[q])
        route.extend(self.path(route[-1], self.s.base)[1:])
        return tuple(route)


def capture_route(route, targets, radius=1):
    covered = set()
    for p in route:
        covered.update(footprint(p, targets, radius))
    return frozenset(covered)
