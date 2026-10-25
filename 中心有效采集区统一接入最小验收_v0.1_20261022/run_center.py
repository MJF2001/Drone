"""Unique dispatcher; importing this file does not execute a task."""
import sys

def main():
    mode=sys.argv[1]
    if mode=='gates':
        from center_credit_v01_20261022.gates import main as run
        run(int(sys.argv[2]))
    elif mode=='worker':
        from center_credit_v01_20261022.worker import main as run
        run(sys.argv[2])
    elif mode=='verify':
        from center_credit_v01_20261022.verify import main as run
        run()
    elif mode=='prepare':
        from center_credit_v01_20261022.prepare import main as run
        run()
    else:
        from center_credit_v01_20261022 import control
        {'freeze_technical':control.freeze_technical,'freeze_real':control.freeze_real,'real':control.real}[mode]()

if __name__=='__main__':
    main()
