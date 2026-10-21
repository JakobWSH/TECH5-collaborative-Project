# TECH5 Collaborative Project — Week 2 progress report (WORKING DRAFT)

**Development Team 3:** Group 14, Team B (Jakob Wilhelm Stenersen Hovdenak, Faisal Mohammad Shaik, Victor Sandberg) and Group 12, Team A (Aurora Malthe-Sørenssen, Ida Kåsin Schjølberg).  
**Canvas deadline:** Tuesday, 27 October 2026 at 23:59.  
**Repository:** https://github.com/JakobWSH/TECH5-collaborative-Project  
**Integration branch:** https://github.com/JakobWSH/TECH5-collaborative-Project/tree/integration/week2  
**Status:** Both teams' work merged on integration branch; combined testing, peer review, instructor approval, and final report still pending.

## 1. Work division and implementation decisions

**Team B — Assignment engine and metrics (Group 14).**
- Developed the provisional binary integer linear programming (ILP) assignment engine in `app/engine/solvers.py`, using the open-source PuLP/CBC solver (`pulp==2.9.0`).
- Implemented the `PREFERENCE`, `SKILL_FIT`, and `BALANCED` strategy objectives; one assignment per student, project minimum/maximum capacity limits, fixed allocations, and integer no-good cuts to produce distinct feasible alternatives.
- Currently assumes a staffed project must include at least one student who meets each mandatory skill requirement. **This interpretation and use of ILP remain subject to professor approval.** Alternatives are distinct, not claimed to all be Pareto-efficient.
- Implemented skill-fit scoring, Gini inequality, solution feasibility/efficiency/fairness/capacity indicators, and comparisons in `app/engine/metrics.py`.
- Integrated input-validation enhancements and regression tests. In particular, Faisal's audit identified that an optional project with no qualified student must be excluded from usable capacity before deciding whether exact allocation is feasible.
- Added direct engine database initialization, allowing the engine to run independently of Flask initialization, and registered concrete solver strategies.
- Updated old Week 1 tests that had intentionally expected `NotImplementedError` from unfinished engine methods.

**Team A — Visualization, comparison, and recommendation (Group 12).**
- On their `team-a/week1-create-project-skills-comparisons` branch, implemented project/skill create-update-delete workflows and multi-solution comparison features in `app/visualization/routes.py`, with a corresponding project delete control in `app/visualization/templates/projects.html`.
- Existing routes invoke the assignment engine through the shared `AssignmentEngineContract`. Previously they used a mock fallback for unfinished engine methods; the Week 2 integration branch now contains the real engine implementation.
- **Team A should review these statements and add their verified Week 2 recommendation/UI changes, if any, before submission.** Do not claim complete recommendation work without test evidence.

## 2. Verification and progress evidence

**Team B standalone branch:** `team-b/week2`, commit `6dcdd99` (2026-10-21). On Jakob's macOS / Python 3.13 virtual environment, after resolving a PuLP linear-expression incompatibility and SQLite schema initialization, the full command `python -m pytest -q` returned:

```
99 passed, 3 xfailed in 16.01s
```

The three expected failures refer to Team A UI functions not yet integrated into that branch. This result verifies **Team B's standalone branch**, not the combined application.

**GitHub integration work (2026-10-21):**
- Faisal's PR #2 was closed as superseded **without merging**, because its validation fix and regression test were already included in Team B's commit `6dcdd99`. His contribution is acknowledged in the PR comment.
- Created `integration/week2` from `team-b/week2`, then merged Team A's `team-a/week1-create-project-skills-comparisons` branch via PR #3. Integration merge commit: `b26031c`.
- The original `main`, Team A branch, and Team B branch were not changed by this merge.

**Required before treating integration as verified:** On the new `integration/week2` branch, install dependencies and run `python -m pytest -q`; test a standard scenario, an infeasible scenario, fixed assignments, and distinct alternatives through the Flask UI. Inspect create/update/delete project and skill behavior, comparing solutions and recommendation explanations. Record the actual outcomes and any fixes. **No combined-branch test result is claimed yet.**

## 3. Issues, limitations, and decisions to resolve

1. **Instructor approval:** ILP/PuLP method approval and whether mandatory skills are required at the project-team or individual-student level are still awaiting a response from Julio. The relevant constraint is isolated for adjustment.
2. **Fairness interpretation:** The mean preference rank covers ranked allocations; unranked allocations are counted separately. Consider both when evaluating student outcomes.
3. **Alternative quality:** No-good cuts guarantee different feasible allocations; they do not by themselves guarantee the full Pareto frontier.
4. **Integration validation:** The combined Flask UI and engine need local automated tests and a reproducible manual demonstration. Existing three UI `xfail` marks need to be reassessed against the merged Team A branch.
5. **Data integrity and CRUD:** Team A noted that deleting linked projects/skills can remove related preferences, requirements, or fixed allocations; review warning/confirmation behavior before final demonstration.

## 4. Next actions and Week 3 outlook

Before the Week 2 deadline: both groups review integrated changes; run and document combined tests; fix any regressions on `integration/week2`; decide whether to merge reviewed code into `main`; finalize a concise joint PDF report explaining implementation decisions and evidence.

Week 3 (2 November): complete all project edge cases, finish the analytical note, verify automated tests after integration, and rehearse a reproducible full demo.

---

**REPORT EDITOR NOTE: DRAFT ONLY.** Add Team A's confirmed work, actual integrated test results, instructor response if received, and submission decisions before converting this into the Canvas PDF.
