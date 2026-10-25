"""Handwritten fixed fixtures. Building this table runs no geometry or selector."""
from fractions import Fraction
from copy import deepcopy

def r(v):
    q = Fraction(v)
    return {'n': q.numerator, 'd': q.denominator}
def p(x, y):
    return [r(x), r(y)]
def e(n=0, radical=None):
    terms = [] if not n else [{'r': 1, 'c': r(n)}]
    for root, coeff in (radical or {}).items():
        terms.append({'r': root, 'c': r(coeff)})
    return {'terms': terms}

LINE = [[0, 0], [1, 0], [2, 0]]
SQUARE = [[0, 0], [0, 1], [1, 0], [1, 1]]
NINE = [[x, y] for x in range(3) for y in range(3)]

def state(S=None, h=None, F=None, P=None, H=None, base=None, E=None, M=None):
    F = deepcopy(LINE if F is None else F)
    P = deepcopy([[0, 0], [1, 0]] if P is None else P)
    H = deepcopy([] if H is None else H)
    D = sorted(set(map(tuple, P))-set(map(tuple, F))-set(map(tuple, H)))
    return {'S': p('1/4', 0) if S is None else S, 'h': p(1, 0) if h is None else h,
            'F': F, 'P': P, 'H': H, 'D': [list(v) for v in D], 'base': [0, 0] if base is None else base,
            'E': e(10) if E is None else E, 'M': e(3) if M is None else M}

def response(points=None, kind='native_grid'):
    return {'stub': 'HANDWRITTEN_FIXED_RESPONSE', 'kind': kind,
            'points': [[0, 0], [1, 0], [0, 0]] if points is None else points}

def move(i, x, y):
    return {'id': i, 'kind': 'move', 'to': p(x, y)}
def collect(i):
    return {'id': i, 'kind': 'collect_here'}
def primitive(a, b, legal, hits):
    return {'a': a, 'b': b, 'expect_legal': legal, 'expect_hits': hits,
            'role': 'standalone_predicate_not_selected_gamma'}

def build():
    cases = []
    names = ['轴向非格心', '斜向非格心', '原格心零接入', '等距方向平局', '安全端点穿障碍',
             '边界擦角', '自由共享边', '无合法可负担直连', '途中格心采集原语', '穿格不经中心',
             '显式采集及发布', '预测实际隔离', '首段中断', '无任务返航', '精确资源及整数额度',
             '后缀拒绝不改入口', '真实来向更新', '容器及输入拒绝']
    def add(group, label, raw=None, suffix=None, status='accepted', q=(0, 0), reason=None, **extra):
        expect = {'status': status}
        if q is not None:
            expect['q'] = list(q)
        if reason:
            expect['reason'] = reason
        expect.update(extra.pop('expect', {}))
        cases.append(dict(id=f'{group:02d}_{sum(x["group"] == group for x in cases)+1}', group=group,
                          group_name=names[group-1], label=label, input=state() if raw is None else raw,
                          suffix=response() if suffix is None else suffix, expect=expect, **extra))
    add(1, '右侧1/4到0', expect={'h_entry': p('-1/4', 0)})
    add(1, '1右侧1/4到1', state(S=p('5/4', 0)), response([[1, 0], [0, 0]]), q=(1, 0))
    add(2, '斜向靠近0', state(S=p('1/4', '1/4'), F=SQUARE), expect={'h_entry': p('-1/4', '-1/4')})
    add(2, '斜向靠近1', state(S=p('3/4', '1/4'), F=SQUARE), response([[1, 0], [0, 0]]), q=(1, 0))
    add(3, '格心零段保留2,3', state(S=p(0, 0), h=p(2, 3)), expect={'h_entry': p(2, 3), 'gamma_H': [[0, 0]]})
    add(3, '格心1显式预测采集', state(S=p(1, 0), h=p(-2, 1)), response([[1, 0], [0, 0]]), q=(1, 0),
        expect={'h_entry': p(-2, 1), 'gamma_H': [[1, 0]]})
    add(4, '等距随正来向', state(S=p('1/2', 0)), response([[1, 0], [0, 0]]), q=(1, 0))
    add(4, '等距随负来向', state(S=p('1/2', 0), h=p(-1, 0)))
    add(4, '等距等角按坐标', state(S=p('1/2', 0), h=p(0, 1)))
    bent = [[0, 0], [0, 1], [1, 1], [2, 1], [2, 0]]
    path = [[0, 0], [0, 1], [1, 1], [2, 1], [2, 0], [2, 1], [1, 1], [0, 1], [0, 0]]
    add(5, '候选安全端点中间障碍', state(F=bent, P=[[0, 0], [2, 0]]), response(path),
        expect={'candidate_reject': [2, 0]})
    hole = [v for v in NINE if v != [1, 1]]
    add(5, '手写斜后缀穿中央障碍拒绝', state(S=p(0, 0), F=hole, P=[[0, 0]]),
        response([[0, 0], [2, 2], [0, 0]], 'manual_polyline'), status='rejected_suffix', reason='suffix_geometry',
        expect={'candidate_reject': [2, 2]})
    add(6, '给定停止点在外边界拒绝', state(S=p('-1/2', 0)), status='invalid_input', q=None, reason='unsafe_given_stop')
    add(6, '两自由格仅接角不可穿', state(S=p(0, 0), F=[[0, 0], [1, 1]], P=[[0, 0]]), response([[0, 0]]),
        expect={'candidate_reject': [1, 1]}, primitives=[primitive(p(0, 0), p(1, 1), False, [[1, 1]])])
    # Hits are geometric intersections; the primitive's P below is just (0,0), so the
    # forbidden endpoint (1,1) is not a service target. Freeze the correct expected list.
    cases[-1]['primitives'][0]['expect_hits'] = []
    add(7, '共享边内点及沿边原语', state(S=p('1/2', 0), h=p(0, 1), F=[[0, 0], [1, 0]]),
        primitives=[primitive(p('1/2', '-1/4'), p('1/2', '1/4'), True, [])])
    add(7, '四自由格共享顶点可过', state(S=p('1/2', '1/2'), h=p(1, 1), F=SQUARE, P=[[0, 0]]),
        response([[1, 1], [1, 0], [0, 0]]), q=(1, 1),
        primitives=[primitive(p('1/2', 0), p('1/2', 1), True, [])])
    add(8, '非格心E为0无入口', state(E=e()), status='no_entry', q=None)
    add(8, 'E为0.24小于最短0.25', state(E=e('6/25')), status='no_entry', q=None)
    add(9, '手写长直段途中服务与重复提交', state(P=[[1, 0], [2, 0]]),
        response([[0, 0], [1, 0], [2, 0], [1, 0], [0, 0]]),
        primitives=[primitive(p('1/4', 0), p(2, 0), True, [[1, 0], [2, 0]])],
        actions=[move('m9', 2, 0), move('m9', 2, 0)], actions_role='standalone_manual_prefix_not_selected_gamma',
        expect={'final_H': [[1, 0], [2, 0]], 'final_E': e('33/4'), 'final_M': e('19/4')})
    add(9, '手写斜线过两个任务中心', state(S=p('1/4', '1/4'), F=NINE, P=[[1, 1], [2, 2]], E=e(20)),
        response([[0, 0], [2, 2], [0, 0]], 'manual_polyline'),
        primitives=[primitive(p('1/4', '1/4'), p(2, 2), True, [[1, 1], [2, 2]])],
        actions=[move('diag9', 2, 2)], actions_role='standalone_manual_prefix_not_selected_gamma',
        expect={'final_H': [[1, 1], [2, 2]], 'final_E': e(20, {2: '-7/4'}), 'final_M': e(3, {2: '7/4'})})
    add(10, '水平穿两格但偏离中心', state(S=p('-1/4', '1/4')),
        primitives=[primitive(p('-1/4', '1/4'), p('5/4', '1/4'), True, [])],
        actions=[move('off10', '5/4', '1/4')], actions_role='standalone_manual_prefix_not_selected_gamma', expect={'final_H': []})
    add(10, '斜穿任务格不经过中心', state(S=p('1/10', '1/5'), F=SQUARE, P=[[1, 1]]),
        response([[0, 0], [1, 0], [1, 1], [1, 0], [0, 0]]),
        primitives=[primitive(p('1/10', '1/5'), p('6/5', '13/10'), True, [])],
        actions=[move('offdiag10', '6/5', '13/10')], actions_role='standalone_manual_prefix_not_selected_gamma', expect={'final_H': []})
    add(11, '发布及等候无信用随后显式采集', state(S=p(0, 0), P=[]), response([[0, 0]]),
        actions=[{'id': 'pub', 'kind': 'publish', 'P': [[0, 0], [1, 0]]}, move('wait', 0, 0),
                 collect('c0'), collect('c0again'), move('arrive1', 1, 0), collect('c1')],
        expect={'action_H': [[], [], [[0, 0]], [[0, 0]], [[0, 0], [1, 0]], [[0, 0], [1, 0]]],
                'final_H': [[0, 0], [1, 0]], 'final_E': e(9), 'final_M': e(4)})
    add(11, '初始任务中心显式采集不离开', state(S=p(0, 0), P=[[0, 0]], F=[[0, 0]]), response([[0, 0]]),
        actions=[collect('c'), collect('c'), move('wait', 0, 0), collect('again')],
        expect={'final_H': [[0, 0]], 'final_E': e(10), 'final_M': e(3), 'final_h': p(1, 0)})
    add(12, '预测有采集实际不动', expect={'gamma_H': [[0, 0]], 'actual_H': []})
    add(12, '历史受遮挡信用及根式实际M保留', state(P=[[0, 0], [1, 0], [4, 4]], H=[[4, 4]],
        E=e(10, {2: 1}), M=e(3, {3: '1/2'})), expect={'actual_H': [[4, 4]], 'gamma_H': [[0, 0], [4, 4]]})
    add(13, '半程停住未到q', state(S=p('1/4', '1/4'), F=SQUARE, P=[[0, 0]]), response([[0, 0]]),
        actions=[move('half', '1/8', '1/8')], actions_role='selected_gamma_prefix',
        expect={'final_S': p('1/8', '1/8'), 'final_h': p('-1/8', '-1/8'), 'final_H': [],
                'final_E': e(10, {2: '-1/8'}), 'final_M': e(3, {2: '1/8'})})
    add(13, '半程等候再到达q不重复扣费', state(S=p('1/4', '1/4'), F=SQUARE, P=[[0, 0]]), response([[0, 0]]),
        actions=[move('half', '1/8', '1/8'), move('wait', '1/8', '1/8'), move('end', 0, 0), collect('qcollect')],
        actions_role='selected_gamma_prefix', expect={'final_S': p(0, 0), 'final_h': p('-1/8', '-1/8'),
        'action_H': [[], [], [[0, 0]], [[0, 0]]], 'final_H': [[0, 0]], 'final_E': e(10, {2: '-1/4'}), 'final_M': e(3, {2: '1/4'})})
    add(14, '任务空也从q回基地', state(S=p('5/4', 0), P=[]), response([[1, 0], [0, 0]]), q=(1, 0))
    add(14, '只剩遮挡任务暂缓仍返航', state(S=p('5/4', 0), P=[[4, 4]]), response([[1, 0], [0, 0]]), q=(1, 0),
        expect={'deferred': [[4, 4]]})
    add(15, '距离恰好等于9/4', state(E=e('9/4')), expect={'allowance': 2, 'final_plan_E': e()})
    add(15, '总距离少0.01且floor为1', state(E=e('56/25')), status='rejected_suffix', reason='suffix_overbudget', expect={'allowance': 1})
    add(15, '根式相消后额度精确为整数2', state(S=p('1/4', '1/4'), F=SQUARE, E=e(2, {2: '1/4'})),
        expect={'allowance': 2, 'final_plan_E': e()})
    add(16, '后缀首点错误不选第二入口', suffix=response([[1, 0], [0, 0]]), status='rejected_suffix', reason='suffix_endpoints')
    add(16, '后缀遗漏1号任务', suffix=response([[0, 0]]), status='rejected_suffix', reason='suffix_missing_service')
    add(16, '后缀超额且第二入口存在也不重选', raw=state(E=e(1)), status='rejected_suffix', reason='suffix_overbudget')
    add(17, '有理真实来向零段继承', state(S=p(0, 0), h=p('1/3', '-2/5'), P=[[0, 0]]), response([[0, 0]]),
        actions=[move('wait', 0, 0), collect('here')], expect={'h_entry': p('1/3', '-2/5'), 'final_h': p('1/3', '-2/5')})
    add(17, '非零进入后等候仍保留斜来向', state(S=p('1/4', '1/4'), h=p(2, 3), F=SQUARE, P=[[0, 0]]), response([[0, 0]]),
        actions=[move('entry', 0, 0), move('wait', 0, 0)], expect={'h_entry': p('-1/4', '-1/4'), 'final_h': p('-1/4', '-1/4')})
    add(18, '运行时tuple与保存JSON list等值', runtime_tuple=True)
    missing = state()
    del missing['h']
    add(18, '缺少真实h拒绝', missing, status='invalid_input', q=None, reason='missing_field')
    invalid = state()
    invalid['h'][0]['n'] = 0.5
    add(18, '浮点分子拒绝不得默转有理', invalid, status='invalid_input', q=None, reason='rational_value')
    return cases
