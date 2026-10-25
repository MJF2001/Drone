"""Infrastructure-only successor; absolute offline audit module loading."""
import environment
from support import *
environment.audit=load('local_offline_audit_for_seal',H/'audit.py')
if __name__=='__main__':environment.main()
