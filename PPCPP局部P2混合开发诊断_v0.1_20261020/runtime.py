"""Frozen native PPCPP and shared input contract; no LAST/ORIENT policy."""
import sys
from support import *
sys.path.insert(0,str(R));sys.path.insert(0,str(R/'基线复现准备_20261019'))
native=load('local_native',R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py')
validate=load('local_validate',R/'PPCPP结构候选新开发验证_v0.1_20261020/validation.py').validate
from model import Snapshot,DeadlineExceeded,NoPath
def snapshot(c):return Snapshot(c['name'],frozenset(pts(c['free'])),frozenset(pts(c['targets'])),frozenset(pts(c['covered'])),tuple(c['current']),tuple(c['base']),tuple(map(tuple,c['old_route'])),0,c['distance_budget'])
