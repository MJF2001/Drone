"""Small regression fixtures for the two B-stage semantic corrections."""
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from build_semantic_correction_v0_2 import (deferred_goal_set, first_hits,
    old_route_role_at_index, pre_event_service_hits)


def test_covered_obstructed_goal_is_not_deferred():
    covered_obstructed=(1,0)
    uncompleted_obstructed=(2,0)
    published={covered_obstructed,uncompleted_obstructed,(3,0)}
    covered={covered_obstructed}
    free={(3,0)}
    deferred=deferred_goal_set(published,covered,free)
    assert deferred=={uncompleted_obstructed}
    assert covered_obstructed not in deferred
    assert deferred== (published-covered)-free


def test_blocked_first_service_uses_pre_event_task_set():
    current=(0,0); first_task=(1,0); later_task=(2,0); base=(3,0)
    route=[current,first_task,later_task,base]
    initial={first_task,later_task};covered=set()
    event_free={current,later_task,base}
    current_inspectable={later_task}
    post_event_pending=current_inspectable-covered-{current}
    assert first_hits(route,post_event_pending).get(first_task) is None
    old_hits=pre_event_service_hits(route,initial,covered,current)
    assert old_hits[first_task]==1
    assert old_route_role_at_index(route,1,old_hits)=="first_service"
    assert first_task not in current_inspectable and first_task not in event_free


if __name__=="__main__":
    test_covered_obstructed_goal_is_not_deferred()
    test_blocked_first_service_uses_pre_event_task_set()
    print("PASS: 2 semantic regression fixtures")
