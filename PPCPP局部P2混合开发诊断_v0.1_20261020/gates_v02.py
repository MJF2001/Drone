"""Resolve frozen/offline audit name collision only in gate process."""
import environment
from support import *
sys.modules['audit']=load('local_offline_audit_for_gates',H/'audit.py')
gate=load('local_gates_original',H/'gates.py')
if __name__=='__main__':gate.main()
