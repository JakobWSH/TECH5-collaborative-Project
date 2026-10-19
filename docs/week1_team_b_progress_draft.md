# TECH5 Collaborative Project — Week 1 progress report (working draft)

**Development Team:** Team 3 (Groups 14 and 12)  
**Team B (Assignment Engine):** Group 14 — Jakob Wilhelm Stenersen Hovdenak, Faisal Mohammad Shaik, Victor Sandberg  
**Team A (Visualization and Recommendation):** Group 12 — Aurora Malthe-Sørenssen, Ida Kåsin Schjølberg  
**Week 1 deadline:** Tuesday, 20 October 2026, 23:59  
**Repository:** https://github.com/JakobWSH/TECH5-collaborative-Project  
**Status:** WORKING DRAFT — confirm responsibilities, test results, method approval, and Team A updates before submission.

## 1. Project understanding
The application supports an administrator who must assign students to semester projects while considering preference rankings, student skills, project skill requirements, capacity bounds, and fixed administrative assignments. It should present feasible alternatives and allow a user to understand trade-offs in fairness and quality.

The starter kit is a single Flask application backed by SQLite, with shared domain models, repository classes, an abstract Python assignment-engine contract, a mock engine, and pytest tests. Team A and Team B must produce one integrated application, not two unrelated systems.

## 2. Division of work
- **Team A — Group 12:** Project and skill management UI; mock comparison and recommendation workflows; subsequently integrate results from the real engine.
- **Team B — Group 14:** Proposed assignment algorithm; constraint and input validation; analytical indicators; subsequently implement the assignment engine and distinct alternatives.
- **Shared:** Preserve the contract in `app/contract/contract.py`, agree on data/edge-case semantics, review pull requests, and run integration tests.

### Proposed internal responsibilities — to confirm
- **Jakob:** Setup, integration, communication, method approval request, test evidence collection, and Week 1 report assembly.
- **Faisal:** Audit existing validation logic in `app/domain/validation.py`; add targeted validation tests/bug fixes where justified.
- **Victor:** Document the candidate matching model and identify solver constraints/limitations in `app/engine/solvers.py` and `docs/analytical_formulation.md`.
These are proposed assignments, not claims of completed work.

**Status 19 Oct (Victor):** the formulation document (`docs/team_b_formulation.md`) and a first set of validation additions with tests (`tests/test_input_validation.py`) are on branch `team-b/formulation-validation`. Faisal: please review the validation part against your audit before we merge.

## 3. Proposed assignment approach (pending professor approval)
**Candidate method:** Binary integer linear programming (ILP), potentially implemented with PuLP and a compatible solver, subject to course-instructor approval.

**Decision variable:** `x[s,p] = 1` if student `s` is assigned to project `p`, otherwise `0`.

**Hard constraints:**
1. A student is assigned to exactly one project when exact allocation is required and feasible.
2. Each project respects its minimum and maximum capacity.
3. Approved fixed student-project assignments must be preserved.
4. Mandatory project skill requirements must be enforced. **Clarification required:** confirm whether each mandatory skill must be represented by at least one assigned student per project (as suggested by the starter analytical-note template), or whether a different rule applies.

**Candidate objectives and output:**
- Preference-oriented: reward higher-ranked allocations, penalize unranked allocations.
- Skill-oriented: reward student/project skill alignment.
- Balanced: document an explicit trade-off of the two scores and fairness impact.
- Generate up to three distinct feasible alternatives when possible; do not fabricate alternatives if only one exists.
- Report infeasibility explicitly rather than silently relaxing constraints.

**Full formulation:** `docs/team_b_formulation.md` gives the sets, parameters, skill-fit and preference scores, the five hard constraints (the mandatory-skill rule is linearised without auxiliary variables), the no-good cut, the three objectives (`PREFERENCE`, `SKILL_FIT`, `BALANCED`), the run-status mapping and known limitations.

**Why propose ILP:** Binary decisions and hard linear constraints can be expressed directly, feasible alternatives can be made distinct through excluded-solution constraints, and the decisions can be explained to users. Final choice, precise objectives, and assumptions require professor review.

## 4. Week 1 technical activities and verification
- [ ] Both groups agree to preserve `app/contract/contract.py` for initial integration.
- [ ] Each student checks out the shared repository; Team B works on `team-b/week1` or topic branches created from it.
- [x] Run `python -m pytest -v` on the unmodified starter and record the exact summary.
- [x] Inspect `app/persistence/schema.sql`, `app/domain/models.py`, `app/contract/contract.py`, `app/contract/mocks.py`.
- [x] Review `app/domain/validation.py` with `tests/test_validation.py` and validation-related edge-case tests. Preserve existing correct behavior, add targeted tests for gaps.
- [ ] Document the method proposal and ask the instructor for approval. Do not present the model as approved until confirmed.
- [ ] Team A demonstrates creating projects/skills and comparing mock solutions, if completed; request evidence from Group 12.
- [ ] Record test execution output after changes, including unexpected failures, expected failures, and any unresolved issues.

**Baseline caveat resolved:** The README says 50 tests (35 passed, 15 xfail). An actual run of the unmodified starter gives **51 tests: 36 passed, 15 xfailed**. The README is off by one, and the 15 xfails match: 3 for Team A and 12 for Team B.

### Insert verified progress here before submission
- **Commit/branch:** `team-b/formulation-validation` (from `team-b/week1`) [add GitHub link once pushed]
- **Environment:** Python 3.13.0, macOS 26.6.2, Flask/pytest from `requirements.txt`
- **Initial pytest result:** `36 passed, 15 xfailed in 0.80s`
- **Files changed and why:**
  - `app/domain/validation.py`: New rules for gaps found in the audit: rank ≥ 1, preference/requirement ownership, skill-level bounds, duplicate requirements, residual minimum capacity after locks, a lock that forces an unqualified project open, and locks that fill a project without a qualified member. Two false errors fixed: an identical lock entered twice was reported as "contradictory", and an optional (min 0) project with an unmet mandatory skill was reported as infeasible when it can simply stay empty. All existing error messages kept.
  - `app/engine/solvers.py`: `validate_inputs` now rejects unknown strategy keys and `max_alternatives` outside 1–10. Constants `SUPPORTED_STRATEGY_KEYS` and `MAX_ALTERNATIVES_LIMIT` added.
  - `tests/test_input_validation.py`: 16 tests, one per new rule.
  - `docs/team_b_formulation.md`: the proposed ILP model and the mapping from each validation rule to a model constraint.
- **Final pytest result:** `52 passed, 15 xfailed in 0.67s`. No regressions. The 12 Team B xfails are solver/metrics work planned for Week 2. All four demo scenarios give the same validation verdicts as before.
- **Mock workflow observed:** [What ran and what was displayed]
- **Solver method approval status:** [Pending/Approved; date if confirmed]
- **Issues to carry into Week 2:**
  - Instructor clarification: does "mandatory skill" mean at least one qualified member per project (our assumption), or every member qualified?
  - Pin `pulp==2.9.0`. PuLP 4.1.0 fails on import because it needs numpy, which it does not declare.
  - `test_assignment_engine_initialization` asserts `len(engine.strategies) == 0` and `test_assignment_engine_raises_not_implemented` expects `NotImplementedError`. Both must be updated when the strategies are registered; agree this with the instructor and Team A.
- **Team A progress confirmed by:** [Name and evidence]

## 5. Work plan for remaining weeks
**Week 2 — 27 October:** After instructor approval, implement the assignment solver, distinct feasible alternatives, analytical indicators, and the Team A comparison view. Run integration tests on real results rather than only the mock engine.

**Week 3 — 2 November:** Resolve infeasibility/edge-case behavior, verify all supplied automated tests without unexpected failures or regressions, finish the analytical note using `docs/analytical_note_template.md`, and rehearse a reproducible demonstration.

## 6. Submission check
- [ ] Confirm whether Canvas expects one combined report for Team 3 or separate group uploads.
- [ ] All work and claims checked by a group member.
- [ ] Instructor approval request documented.
- [ ] Export finalized report to PDF or DOC according to the Canvas upload specification.
