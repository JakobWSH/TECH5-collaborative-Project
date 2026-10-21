# TECH5 Development Team 3 — Week 2 progress (working draft)

**Team B (Group 14):** Jakob, Faisal, Victor. **Team A:** Aurora and Ida.
**Due:** 27 October 2026 at 23:59.
**Status:** PROVISIONAL WORK — full CBC and Flask tests still required on a Mac before accepting or merging.

## Implemented locally in recovery snapshot (21 October)

- Recovered unfinished Antigravity modifications to `app/engine/metrics.py` and `tests/test_metrics_edge_cases.py`.
- Incorporated Faisal's unusable-project-capacity validation check and its regression test from the snapshot. **PR #2 remains separately open on GitHub; coordinate closure/merging so it is not applied twice.**
- Implemented and hardened four analytical functions in `metrics.py`: skill fit, Gini, feasibility/fairness/efficiency/capacity indicators, and two-solution comparison. Detects unknown and duplicate allocations, mandatory-skill coverage failures, and tracks unranked-to-ranked changes.
- Developed a **provisional** ILP engine in `solvers.py`, using PuLP/CBC; includes preference, skill-fit, balanced objectives, capacity constraints, fixed assignments, team-level mandatory skills (pending approval), no-good cuts, solution metrics, statuses, and SQLite persistence.
- Updated obsolete Week 1 skeleton assertions to reflect the expected Week 2 implementation. Original test logic covering substantive behavior is preserved.

## Verification actually executed in the recovery environment

- **64 passing isolated model, validation, and metrics tests**, using a narrow bootstrap because Flask is not installed here. This is *not* a full test-suite pass.
- **Provisional orchestration smoke test passed** with a *mocked solve method*, exercising `execute_run`, status handling, SQLite persistence, retrieval, and comparisons.
- All Python application and test modules passed syntax compilation.
- **Not tested here:** the real PuLP/CBC optimizer or the Flask web interface, because external package installation was unavailable in this environment.

## Required verification on the Mac before submitting the Week 2 report

1. Confirm Julio's method approval status. Until approved, mark ILP and the team-level mandatory-skill interpretation as provisional.
2. Install dependencies: `python -m pip install -r requirements.txt`.
3. Run `python -m pytest -v` and inspect every failure; do not claim full coverage until green. Solver behavior, integration, and replaced Week 1 skeleton tests particularly require review.
4. Run benchmark scenarios: standard, fixed locks, infeasible capacity, 1-only feasible solution, and distinct multiple solutions; inspect allocations and diagnostics.
5. Test end-to-end integration with Team A's current branch **without overwriting their work**.
6. Review code with Group 14 and Team A, then make a pull request to integrate tested work. Final combined report must include Team A's verified work.

## Technical decisions requiring explanation

- Exact assignment, project minimum and maximum bounds, and approved fixed locks are hard constraints.
- Provisional mandatory-skill rule: each staffed project has at least one member qualified in each mandatory skill. Change if Julio specifies individual qualification instead.
- Alternatives are **distinct**, not necessarily Pareto-optimal. The model cycles the requested primary strategy then other strategy priorities, excluding earlier allocations.
- Mean rank currently describes ranked allocations and separately reports the number of unranked allocations; compare the two indicators together when assessing fairness.
- `pulp==2.9.0` pinned as proposed, pending instructor approval and installation verification.
