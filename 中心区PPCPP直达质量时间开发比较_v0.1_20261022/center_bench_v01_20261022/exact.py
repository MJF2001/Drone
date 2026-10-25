"""Bounded exact radical arithmetic. No floats, numerical epsilon or planners."""
from fractions import Fraction as Q
from math import isqrt

class Refusal(ValueError):
    pass
class Uncertain(Refusal):
    pass

def rational(x):
    if not isinstance(x, dict) or set(x) != {'n', 'd'}:
        raise Refusal('rational_schema')
    if type(x['n']) is not int or type(x['d']) is not int or x['d'] <= 0:
        raise Refusal('rational_value')
    if max(abs(x['n']).bit_length(), x['d'].bit_length()) > 40:
        raise Refusal('rational_size_limit_40_bits')
    return Q(x['n'], x['d'])

def rat(x):
    x = Q(x)
    return {'n': x.numerator, 'd': x.denominator}

def point(x, grid=False):
    if not isinstance(x, (list, tuple)) or len(x) != 2:
        raise Refusal('coordinate_schema')
    if grid:
        if any(type(y) is not int for y in x):
            raise Refusal('grid_coordinate_value')
        return tuple(Q(y) for y in x)
    return tuple(rational(y) for y in x)

def pt(x):
    return [rat(v) for v in x]

def squarefree(n):
    if type(n) is not int or n < 1:
        raise Refusal('radicand')
    # Finite factor work; unsupported large factors are uncertain, never guessed.
    outside, inside, p, work = 1, 1, 2, 0
    while p*p <= n:
        work += 1
        if work > 100000:
            raise Uncertain('factor_work_limit')
        power = 0
        while n % p == 0:
            n //= p
            power += 1
        outside *= p ** (power//2)
        if power % 2:
            inside *= p
        p += 1
    return outside, inside*n

class Expr:
    def __init__(self, terms=None):
        self.terms = {k: Q(v) for k, v in (terms or {}).items() if v}

    @staticmethod
    def number(x):
        return Expr({1: Q(x)})

    @staticmethod
    def sqrt(q):
        q = Q(q)
        if q < 0:
            raise Refusal('negative_square_length')
        if not q:
            return Expr()
        a, r = squarefree(q.numerator*q.denominator)
        return Expr({r: Q(a, q.denominator)})

    @staticmethod
    def load(x):
        if not isinstance(x, dict) or set(x) != {'terms'} or not isinstance(x['terms'], list):
            raise Refusal('expression_schema')
        z = Expr()
        for t in x['terms']:
            if not isinstance(t, dict) or set(t) != {'r', 'c'}:
                raise Refusal('term_schema')
            a, r = squarefree(t['r'])
            z = z + Expr({r: rational(t['c'])*a})
        return z

    def save(self):
        return {'terms': [{'r': r, 'c': rat(c)} for r, c in sorted(self.terms.items())]}

    def __add__(self, other):
        z = dict(self.terms)
        for r, c in other.terms.items():
            z[r] = z.get(r, Q(0)) + c
        return Expr(z)

    def __sub__(self, other):
        return self + Expr({r: -c for r, c in other.terms.items()})

    def interval(self, bits=64):
        scale = 1 << bits
        low = high = Q(0)
        for r, c in self.terms.items():
            k = isqrt(r*scale*scale)
            l = Q(k, scale)
            u = l if k*k == r*scale*scale else Q(k+1, scale)
            low += c*(l if c >= 0 else u)
            high += c*(u if c >= 0 else l)
        return low, high

    def sign(self):
        if not self.terms:
            return 0
        for bits in (16, 32, 64, 128, 256, 512):
            l, u = self.interval(bits)
            if l > 0:
                return 1
            if u < 0:
                return -1
        raise Uncertain('radical_sign_not_certified')

    def floor(self):
        if set(self.terms) <= {1}:
            return self.terms.get(1, Q(0)) // 1
        for bits in (16, 32, 64, 128, 256, 512):
            l, u = self.interval(bits)
            if l//1 == u//1:
                return l//1
        raise Uncertain('radical_floor_not_certified')

def squared(a, b):
    return sum((v-w)**2 for v, w in zip(a, b))

def distance(a, b, counts, phase):
    counts[phase+'_distance'] += 1
    n = squared(a, b)
    return Expr.sqrt(n), rat(n)

def certificate(expr):
    l, u = expr.interval()
    return {'exact': expr.save(), 'interval_bits': 64, 'low': rat(l), 'high': rat(u)}
