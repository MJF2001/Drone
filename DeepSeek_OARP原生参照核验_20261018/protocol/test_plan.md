# Test and call plan (frozen)

| Category | Cap | Content |
|---|---:|---|
| Initial native preparation | 3 | rectangle, vertical line, sparse line |
| Event responses | 32 | 8 cases x (1 rank0 + 3 replan2 caps) |
| Interface boundary tests | 24 | fake clock, audit injection, empty Q, ledger faults (mock flagged) |
| Defect localisation / minimal re-check | 16 | only affected items, new run_id |
| Full-entry total | 75 | every attempt registered, including failed ones |
| Independent strip subproblems | 56 | 40 with certification on + 2 strict diagnostics + up to 14 re-checks |
| Independent exact GTSP | 8 | 1-6 service groups |

Micro calls: public soft deadline 5.0s, subprocess hard cap 10.0s.
Math subproblems: at most 6 cells, 5.0s soft deadline. Exact GTSP: at most 6 groups.

Pure tests (structures, normalisation, serialisation) do not run a solver and are
not counted; anything that reaches a solver is registered.
