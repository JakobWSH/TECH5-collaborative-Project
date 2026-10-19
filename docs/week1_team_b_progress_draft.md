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

**Why propose ILP:** Binary decisions and hard linear constraints can be expressed directly, feasible alternatives can be made distinct through excluded-solution constraints, and the decisions can be explained to users. Final choice, precise objectives, and assumptions require professor review.

## 4. Week 1 technical activities and verification
- [ ] Both groups agree to preserve `app/contract/contract.py` for initial integration.
- [ ] Each student checks out the shared repository; Team B works on `team-b/week1` or topic branches created from it.
- [ ] Run `python -m pytest -v` on the unmodified starter and record the exact summary.
- [ ] Inspect `app/persistence/schema.sql`, `app/domain/models.py`, `app/contract/contract.py`, `app/contract/mocks.py`.
- [ ] Review `app/domain/validation.py` with `tests/test_validation.py` and validation-related edge-case tests. Preserve existing correct behavior, add targeted tests for gaps.
- [ ] Document the method proposal and ask the instructor for approval. Do not present the model as approved until confirmed.
- [ ] Team A demonstrates creating projects/skills and comparing mock solutions, if completed; request evidence from Group 12.
- [ ] Record test execution output after changes, including unexpected failures, expected failures, and any unresolved issues.

**Baseline caveat:** The README says 50 tests with 35 passes and 15 expected failures. A source-file count found 51 `test_...` functions and 15 explicit `xfail` decorators. These claims must be reconciled against an actual local `pytest` run; do not claim either historical summary as your own run.

### Insert verified progress here before submission
- **Commit/branch:** [GitHub link to work]
- **Environment:** [Python version, OS]
- **Initial pytest result:** [Exact terminal summary]
- **Files changed and why:** [List]
- **Final pytest result:** [Exact terminal summary]
- **Mock workflow observed:** [What ran and what was displayed]
- **Solver method approval status:** [Pending/Approved; date if confirmed]
- **Issues to carry into Week 2:** [List]
- **Team A progress confirmed by:** [Name and evidence]

## 5. Work plan for remaining weeks
**Week 2 — 27 October:** After instructor approval, implement the assignment solver, distinct feasible alternatives, analytical indicators, and the Team A comparison view. Run integration tests on real results rather than only the mock engine.

**Week 3 — 2 November:** Resolve infeasibility/edge-case behavior, verify all supplied automated tests without unexpected failures or regressions, finish the analytical note using `docs/analytical_note_template.md`, and rehearse a reproducible demonstration.

## 6. Submission check
- [ ] Confirm whether Canvas expects one combined report for Team 3 or separate group uploads.
- [ ] All work and claims checked by a group member.
- [ ] Instructor approval request documented.
- [ ] Export finalized report to PDF or DOC according to the Canvas upload specification.
