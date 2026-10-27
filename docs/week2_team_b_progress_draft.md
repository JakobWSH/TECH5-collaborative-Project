# TECH5 Collaborative Project — Week 2 progress report (WORKING DRAFT)

**Development Team 3:** Group 14, Team B (Jakob Wilhelm Stenersen Hovdenak, Faisal Mohammad Shaik, Victor Sandberg) and Group 12, Team A (Aurora Malthe-Sørenssen, Ida Kåsin Schjølberg).  
**Canvas deadline:** Tuesday, 27 October 2026 at 23:59.  
**Repository:** https://github.com/JakobWSH/TECH5-collaborative-Project  
**Integration branch:** https://github.com/JakobWSH/TECH5-collaborative-Project/tree/integration/week2  
**Status:** Both teams' work merged; 104 integrated tests passed; the ILP/PuLP method was approved by Julio Goez on 22 October 2026. Manual walkthrough and peer review remain pending. The mandatory-skill interpretation was not explicitly resolved.

## 1. Work division and implementation decisions

**Team B — Assignment engine and metrics (Group 14).**
- Developed the instructor-approved binary integer linear programming (ILP) assignment engine in `app/engine/solvers.py`, using the open-source PuLP/CBC solver (`pulp==2.9.0`).
- Implemented the `PREFERENCE`, `SKILL_FIT`, and `BALANCED` strategy objectives; one assignment per student, project minimum/maximum capacity limits, fixed allocations, and integer no-good cuts to produce distinct feasible alternatives.
- Currently assumes a staffed project must include at least one student who meets each mandatory skill requirement. **Julio approved the proposed ILP approach on 22 October 2026; his reply did not explicitly decide whether mandatory skills apply per student or per staffed project team.** Alternatives are distinct, not claimed to all be Pareto-efficient.
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

**Combined-branch verification on Jakob's Mac (2026-10-21):** `integration/week2` at commit `cdfb9a3`, with Flask 3.1.3, pytest 9.1.1 and PuLP 2.9.0 installed. The full command `python -m pytest -q` returned:

```
101 passed, 3 xpassed in 1.12s
```

All active tests passed and no failures remained. The three `xpassed` tests were old Team A starter tests still marked `xfail`; inspection found they had no assertions and therefore did not establish behavior. A follow-up test-only change removed these obsolete markers and added assertions for skill create/delete, project create/edit/delete, and rendering two real solution alternatives. **The strengthened tests have now been verified successfully on Jakob's Mac.**

The earlier combined run had failed in the side-by-side comparison template because per-student allocation changes did not include `rank_delta` and matching project ID aliases. The integration branch now supplies these fields, handles unranked allocations explicitly, and has added comparison regressions. A focused subsequent run completed with `10 passed`.

**Final strengthened integration-suite result (21 October 2026):** After updating to `integration/week2` commit `a6b2f4b` and running `python -m pytest -q` in Jakob's macOS Python 3.13 virtual environment:

```
104 passed in 95.32s (0:01:35)
```

This run has **zero failed, zero xfailed, and zero xpassed tests**. It covers the integrated code and the strengthened Team A workflows, including real solver output used in the comparison view. The previous `101 passed, 3 xpassed` result above is retained to document the progression of the tests.

**Still to verify manually with both teams:** End-to-end Flask UI walkthrough of real alternatives, recommendations, project/skill CRUD, preference and capacity handling, and meaningful comparison labels. Automated checks alone do not confirm the user experience.

## 3. Issues, limitations, and decisions to resolve

1. **Instructor method approval:** Julio Goez replied on **22 October 2026** that the proposed ILP approach is good, adding that Pyomo may be used instead of PuLP if preferred; switching is **not required**. His reply did **not explicitly clarify** the mandatory-skill interpretation. The current solver requires at least one qualified team member for each mandatory project skill, and the relevant constraint remains isolated for adjustment.
2. **Fairness interpretation:** The mean preference rank covers ranked allocations; unranked allocations are counted separately. Consider both when evaluating student outcomes.
3. **Alternative quality:** No-good cuts guarantee different feasible allocations; they do not by themselves guarantee the full Pareto frontier.
4. **Integration validation:** All 104 automated tests pass on the combined branch. A reproducible manual Flask UI demonstration and both teams' peer review remain outstanding.
5. **Data integrity and CRUD:** Team A noted that deleting linked projects/skills can remove related preferences, requirements, or fixed allocations; review warning/confirmation behavior before final demonstration.

## 4. Next actions and Week 3 outlook

Before the Week 2 deadline: both groups review integrated changes; run and document combined tests; fix any regressions on `integration/week2`; decide whether to merge reviewed code into `main`; finalize a concise joint PDF report explaining implementation decisions and evidence.

Week 3 (2 November): complete all project edge cases, finish the analytical note, verify automated tests after integration, and rehearse a reproducible full demo.

---

**REPORT EDITOR NOTE:** The technical decisions, 104-test evidence and instructor's ILP approval are documented. Team A should confirm its stated contribution and the groups should review any remaining manual UI checks before treating the integration PR as final. The Week 2 Canvas report itself may be submitted with those limitations transparently disclosed.
