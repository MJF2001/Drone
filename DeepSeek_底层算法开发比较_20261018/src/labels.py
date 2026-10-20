"""Uniform status labels for saved records.

One defect was found by the independent audit of LONG120: six P2_MULTI records
were saved with the engine's ``status='finished'`` while their
``termination.natural`` was already ``False`` (the engine had hit the soft
deadline but still held a valid incumbent).  The route and the timings are
correct; the *label* treats a truncated run as a natural finish.

The saved records are not rewritten.  Instead this module defines the label the
analysis must use, and the registry applies the same rule to new rows so future
batches are self-consistent.
"""

SUCCESS = ("finished", "planned", "planned_at_timeout", "complete_coverage",
           "finished_with_safety_limit")
#: labels that may describe a run which was stopped before its own termination
TRUNCATED_LABELS = ("planned_at_timeout", "deadline_before_complete_route",
                    "safety_limit_before_complete_route")


def effective_status(row):
    """The label a record must carry, given its own termination flag.

    A record that says "finished" but also says "not natural" is a truncated run
    with a valid incumbent: it is relabelled ``planned_at_timeout``.
    """
    status = row.get("status")
    natural = (row.get("termination") or {}).get("natural")
    if status in ("finished", "complete_coverage") and natural is False:
        return "planned_at_timeout"
    return status


def is_relabelled(row):
    return effective_status(row) != row.get("status")
