# TECH5 Collaborative Project — Week 3 Analytical Note (WORKING DRAFT)
## Deliverable 6: Analytical Note & Mathematical Formulation

**Development Team 3 — NHH, Autumn 2026**  
**Team B / Group 14:** Jakob Wilhelm Stenersen Hovdenak, Faisal Mohammad Shaik, Victor Sandberg  
**Team A / Group 12:** Aurora Malthe-Sørenssen, Ida Kåsin Schjølberg  
**Deadline:** Monday, 2 November 2026 at 23:59  
**Status:** **Draft for cross-team review — not yet a Canvas submission.** The mathematical model and metrics are drafted from the current tested code; the recommendation section, source citation, and live demonstration need final review.

**Code reference:** [Tested Week 2 integration branch](https://github.com/JakobWSH/TECH5-collaborative-Project/tree/integration/week2); [draft integration PR #4](https://github.com/JakobWSH/TECH5-collaborative-Project/pull/4). Team A also maintains an additional \`team-a/week2-polish\` branch that has **not yet been integrated and retested** with this baseline.

---

## 1. Problem Definition & Mathematical Modeling Approach

### 1.1 Business context and decision dilemma

Academic coordinators must assign each student to exactly one project while balancing ranked student preferences, individual skills relative to project requirements, minimum and maximum team sizes, and any approved administrative pre-allocations. Maximizing student preference satisfaction can conflict with staffing technically demanding projects; maximizing skill fit may in turn place some students on lower-ranked or unranked projects. A useful decision-support system therefore presents multiple feasible assignments and evidence about their trade-offs rather than one unexplained answer.

This is a constrained allocation problem, rather than a purely preference-based ranking task. An allocation with high student satisfaction is not acceptable if it violates capacity or fixed-assignment rules. Distinct candidate solutions allow the coordinator to compare individual outcomes, project capability, fairness and operational feasibility.

**Source/research check (owner: Team B):** The instructor's analytical-note template requests a contextual discussion of Rezaeinia et al. (2022). A verified bibliographic reference and an accurately paraphrased, relevant comparison should be supplied before submission; do not imply that this implementation reproduces their algorithm.

### 1.2 Selected assignment methodology

The engine uses **binary integer linear programming (ILP)**, implemented with **PuLP 2.9.0** and solved by CBC within the single-process Python/Flask application (\`app/engine/solvers.py\`). Exact assignment, capacity, fixed locks, and the present interpretation of mandatory skill coverage are modeled as linear constraints. Changing the objective produces preference-oriented, skill-fit-oriented or balanced alternatives without changing the underlying admissibility rules.

**Course approval:** Julio Goez replied on **22 October 2026** that the proposed ILP approach was good, mentioning Pyomo as an optional alternative to PuLP. His response **did not explicitly decide** between team-level mandatory-skill coverage and requiring every assigned student to be individually qualified.

ILP is appropriate for this discrete allocation model because it expresses admissibility explicitly and lets the solver find an optimum for the chosen linear objective, or report mathematical infeasibility if proven. Computation grows with the number of student-project pairs; no large-scale performance benchmark has yet been documented, so we make **no** unverified claim about solving hundreds or thousands of students within a fixed runtime.

---

## 2. Mathematical Formulation

### 2.1 Sets and dimensions

- \(S\): set of students, \(n=|S|\).
- \(P\): set of projects, \(m=|P|\).
- \(K\): skill catalog; \(K_p\subseteq K\) is the set of skills required by project \(p\).
- \(M_p\subseteq K_p\): mandatory skills for project \(p\).
- \(F\subseteq S\times P\): approved fixed assignment pairs.
- \(Q_{p,k}=\{s\in S:a_{s,k}\ge q_{p,k}\}\): students qualified for skill \(k\) at project \(p\)'s threshold.

### 2.2 Parameters and scoring rules

- \(l_p,u_p\): minimum and maximum project headcount, with \(0\le l_p\le u_p\) and \(u_p\ge1\).
- \(a_{s,k}\): recorded proficiency of student \(s\) in skill \(k\) (missing skill means level 0).
- \(q_{p,k}\): required proficiency level of skill \(k\) at project \(p\) (positive for a stored requirement).
- \(r_{s,p}\): student \(s\)'s recorded rank for project \(p\), when listed; smaller ranks are better.
- \(R=\max\{r_{s,p}:r_{s,p}\text{ is recorded}\}\), or \(0\) if no preferences exist. **This is the maximum recorded rank in the cohort, not necessarily each student's list length or the number of projects.**
- \(w_{s,p}\): normalized preference score:
  \[
  w_{s,p}=\begin{cases}
  \max(0,(R+1-r_{s,p})/R), & R\ge1 \text{ and }p\text{ is ranked by }s,\\
  0, & \text{otherwise.}
  \end{cases}
  \]
  Unranked project assignments have preference utility \(0\). For worst-rank comparison, they are given penalty \(R+1\).
- \(\sigma_{s,p}\): normalized individual skill fit:
  \[
  \sigma_{s,p}=\begin{cases}
  1,&K_p=\varnothing,\\
  \displaystyle\frac1{|K_p|}\sum_{k\in K_p}\min(a_{s,k}/q_{p,k},1),&K_p\neq\varnothing.
  \end{cases}
  \]
  The code averages **all** project requirements, including mandatory ones, and caps overqualification at 1. These values are computed by \`calculate_assignment_skill_fit()\`.

### 2.3 Decision variables

- \(x_{s,p}\in\{0,1\}\): equals 1 when student \(s\) receives project \(p\).
- \(z\ge0\), integer: an auxiliary upper bound on the worst allocated preference rank in the balanced strategy.

### 2.4 Hard constraints

**Exact allocation:**
\[
\sum_{p\in P}x_{s,p}=1\qquad\forall s\in S.
\]

**Project minimum and maximum capacities:**
\[
l_p\le\sum_{s\in S}x_{s,p}\le u_p\qquad\forall p\in P.
\]
A project with \(l_p=0\) is allowed to stay empty.

**Approved fixed allocations:**
\[
x_{s,p}=1\qquad\forall(s,p)\in F.
\]

**Mandatory qualification — current TEAM-LEVEL assumption:**
\[
u_p\sum_{s\in Q_{p,k}}x_{s,p}\ \ge\ \sum_{s\in S}x_{s,p}
\qquad\forall p\in P,\ k\in M_p.
\]
If a project has any assigned students, it must have **at least one qualified student for every mandatory skill** (not necessarily the same student for all skills). If nobody is assigned, both sides are zero. This interpretation follows our implemented solver and validation, but remains subject to clarification because Julio's approval email did not explicitly settle the question. The stricter individual-level alternative would forbid \(x_{s,p}=1\) for students missing any mandatory threshold.

**Worst-rank linkage (balanced strategy):**
\[
z\ge \tilde r_{s,p}x_{s,p}\qquad\forall s\in S,p\in P,
\quad \tilde r_{s,p}=\begin{cases}r_{s,p},&p\text{ ranked}\\R+1,&p\text{ unranked}.\end{cases}
\]
When minimizing \(z\) within the maximization objective, it becomes the worst assigned rank.

**Distinct alternatives (no-good cuts):** after each previous allocation \(A^{(t)}=\{(s,p):x_{s,p}^{(t)}=1\}\), constrain
\[
\sum_{(s,p)\in A^{(t)}}x_{s,p}\le n-1.
\]
Thus at least one student's project changes. If a later solve is infeasible, the engine retains the earlier valid alternatives. **No-good cuts establish distinctness, not Pareto-optimality.**

### 2.5 Implemented objectives and generation procedure

Let
\[
\varepsilon=\frac{1}{2n\max(R,1)}\quad(n>0).
\]
This small coefficient supplies a tie-breaker, while giving the primary preference or skill-fit objective priority. In the code, the requested primary strategy is attempted first; subsequent alternatives cycle through the other two strategies while excluding previous allocations. \`max_alternatives\` is constrained to 1–10.

**Preference-oriented:**
\[
\max Z_{\mathrm{pref}}=\sum_{s,p}(w_{s,p}+\varepsilon\sigma_{s,p})x_{s,p}.
\]

**Skill-fit-oriented:**
\[
\max Z_{\mathrm{skill}}=\sum_{s,p}(\sigma_{s,p}+\varepsilon w_{s,p})x_{s,p}.
\]

**Balanced compromise:**
\[
\max Z_{\mathrm{bal}}=\sum_{s,p}(0.5w_{s,p}+0.5\sigma_{s,p})x_{s,p}
-\frac{z}{\max(R+1,1)}.
\]

The objectives are **sums** over students and are evaluated only over allocations satisfying all hard constraints. The balanced strategy penalizes the worst assigned rank, but it does not directly optimize the Gini coefficient. The CBC solver has a **30-second time limit per solve** in the current code. A timeout or non-optimal status must not be described as proven infeasibility.

---

## 3. Evaluation Indicators & Analytical Metrics

Metrics are implemented in \`app/engine/metrics.py\`, with their computed values stored as solution indicators in SQLite.

### 3.1 Feasibility

The engine verifies that every known student has exactly one assignment; no assignment references an unknown student or project; each project's total lies within \([l_p,u_p]\); every approved fixed lock is honored; and the staffed-team mandatory coverage rule holds. \`compute_solution_indicators()\` returns an \`is_feasible\` Boolean together with named violations. Structural input validation also checks duplicate identifiers, capacities, preference references and impossible locks before optimization.

### 3.2 Efficiency

For assignments \(A\) actually returned, the implementation reports
\[
\overline\sigma=\frac1{|A|}\sum_{(s,p)\in A}\sigma_{s,p}.
\]
In a valid full allocation \(|A|=n\). \`unmet_soft_requirements_count\` counts deficient **non-mandatory** skill requirements. Mandatory coverage is a separate feasibility condition.

**Preference mean:** The implemented \`fairness.mean_rank\` is the average among **ranked** assignments only:
\[
\overline r_{\rm ranked}
=\frac{\sum_{(s,p)\in A,\ r_{s,p}\ne\varnothing}r_{s,p}}
{\#\{(s,p)\in A:r_{s,p}\ne\varnothing\}},
\]
with a zero fallback when no ranked assignments exist. This is **not** the mean over all students in the template: unranked students are represented separately by \`unranked_count\` and \`unranked_pct\`. Report both figures whenever comparing solutions.

### 3.3 Fairness

- **Rank distribution:** count assigned students at each recorded rank \(1,2,\ldots\).
- **Unranked count and percentage:** assignments outside a student's ranked list.
- **Worst recorded assigned rank:** maximum over **ranked** assignments, or zero if none. Unranked outcomes must be interpreted using their separate count.
- **Rank variance:** average squared deviation of recorded assigned ranks from \(\overline r_{\rm ranked}\).
- **Gini coefficient:** for the \(h\) positive, recorded allocated ranks ordered \(y_1\le\cdots\le y_h\):
  \[
  G=\frac{2\sum_{i=1}^{h}iy_i}{h\sum_{i=1}^{h}y_i}-\frac{h+1}{h},
  \]
  with \(G=0\) for empty or all-zero inputs. Smaller \(G\) means less inequality among recorded ranks. **Caveat:** because the current implementation excludes unranked assignments from Gini and rank variance, a low Gini is not by itself evidence that all students received acceptable projects.

### 3.4 Capacity utilization

For project \(p\), \(N_p=\sum_sx_{s,p}\) and
\[
\mathrm{Util}_p=100N_p/u_p\%.
\]
Overall utilization is \(100n/\sum_pu_p\%\) for a valid full allocation. \`capacity.projects\` reports the assigned headcount, minimum, maximum, and utilization per project; \`capacity.total_capacity\` and \`overall_utilization_pct\` report the aggregate.

---

## 4. Trade-Off Analysis & Solution Comparison

### 4.1 Comparative deltas

For two stored alternatives A and B:
\[
\Delta\overline\sigma=\overline\sigma_B-\overline\sigma_A,\quad
\Delta\overline r=\overline r_B-\overline r_A,\quad
\Delta G=G_B-G_A.
\]

Positive skill-fit delta signals greater average technical fit. Negative rank delta signals a better average **recorded** preference rank; negative Gini signals less rank inequality among ranked outcomes. The implementation also reports \(\Delta U=U_B-U_A\), the change in unranked assignments. The template proposes a worst-rank delta; **the current comparison object does not expose this as a separate delta**, so the final note should not claim it does unless it is added and tested.

### 4.2 Allocation differences and affected students

A student's allocation is marked changed when \(p_A(s)\ne p_B(s)\). For students ranked in both solutions, \(\Delta r_s=r_B(s)-r_A(s)\): negative is improved and positive is worsened. A change from unranked to ranked counts as an improvement; ranked to unranked is a deterioration. Both unranked counts and changed project IDs are displayed in the integration comparison UI. The output includes \`changed_students_count\`, \`rank_improved_count\`, \`rank_worsened_count\`, and plain-language trade-off statements.

---

## 5. Transparent Recommendation Rules — Team A to verify and finalize

**Owner: Team A (Group 12).** The current tested integration baseline contains \`app/engine/recommendations.py\`; however, Team A has subsequent unmerged changes on \`team-a/week2-polish\`. Confirm that the final policy rules below match whichever version is integrated, update the evidence/advice wording, and retest before signing off.

### 5.1 Student preference priority

**Tested-baseline criterion:** lexicographically minimize unranked count, then mean recorded rank, then worst recorded rank. Evidence includes these indicators and average skill fit. The advice identifies when a coordinator prioritizing student satisfaction might select the candidate.

**TODO Team A:** Verify priority order against updated recommendation code; explain why the ranking uses unranked count separately from mean rank.

### 5.2 Project delivery and technical quality

**Tested-baseline criterion:** maximize mean skill fit; use fewer unmet soft skill requirements as a tie-breaker. Evidence lists mean fit, unmet soft requirements and average recorded preference rank. Advice concerns technical project quality.

**TODO Team A:** Confirm the exact criteria/evidence in the polished branch and add an explicit warning about preference outcomes and mandatory project skill coverage.

### 5.3 Balanced and egalitarian priority

**Tested-baseline criterion:** lexicographically minimize rank Gini, then rank variance, then mean recorded rank. Evidence includes rank inequality, variance, mean skill fit and mean rank. Advice concerns fairness.

**TODO Team A:** Explain the limitation of a Gini computed over ranked allocations only, especially if unranked outcomes differ. Do not claim that recommendations prove Pareto-optimality.

**Transparency principle:** Quantitative evidence (computed metrics and the ranking rule) must remain distinct from administrative advice (value-dependent recommendation). A coordinator may reasonably choose different alternatives under different priorities.

---

## 6. Assumptions, Boundary Conditions & Edge Cases

1. **Incomplete preferences:** a student is still assignable to an unranked project; its preference utility is zero and its worst-rank penalty is \(R+1\).
2. **Ties across students:** multiple students can favor the same project; capacity constraints and the objective resolve competition.
3. **Empty skill declarations:** missing skill levels count as zero. A project with no required skills receives fit score 1.
4. **Optional unstaffable projects:** a project with minimum 0 and unmet mandatory requirements can remain empty. Feasibility prechecks subtract its unusable capacity when assessing whether the whole cohort still fits; this check originated in Faisal's validation audit.
5. **Locks and capacity:** contradictory student locks, locks exceeding a project's maximum, and locks that fill a project without mandatory qualified students are diagnosed.
6. **Aggregate infeasibility:** if \(n>\sum_pu_p\) or \(n<\sum_pl_p\), full allocation cannot exist. These are necessary checks, not a complete substitute for CBC's proof.
7. **Only one feasible allocation:** the engine stops after the next no-good cut makes the model infeasible; it must not invent duplicates.
8. **Solver status:** only proven \`Optimal\` solutions are accepted. \`INFEASIBLE\`, \`INVALID_INPUT\`, and \`FAILED\` are separate statuses.

**Verification baseline:** On **21 October 2026**, the combined \`integration/week2\` branch passed \`python -m pytest -q\`: **104 passed, zero failed, zero XFAIL/XPASS** in 95.32 seconds on the user's macOS/Python 3.13 setup. This is a verified historical result, **not** a claim that Team A's subsequent \`team-a/week2-polish\` commits have passed integration tests.

**TODO both teams:** Run the full tests after merging new changes. Verify the instructor-provided 50-test baseline separately if tests in the starter repository must remain unchanged; several original test files were modified during Week 2, so do not assume the policy was satisfied without checking the exact course instruction. Document a real Flask demo for standard, locked and infeasible cases.

---

## 7. Limitations & Analytical Deficiencies

1. **Complexity and scalability:** the binary-variable count is \(n\cdot m\), plus auxiliary variables and constraints. Repeated optimization for alternatives multiplies work. The time-limited CBC approach is not supported by a formal scale benchmark.
2. **Linear/additive utilities:** the preference score treats each rank step linearly and the objective sums scores across students. This can trade a large loss for one student against modest gains for others. The balanced worst-rank penalty mitigates but does not eliminate that risk.
3. **Incomplete preferences and fairness:** all unranked projects receive the same utility. Mean rank and rank Gini exclude unranked outcomes, so compare them with \`unranked_count\`, never on their own.
4. **Individual versus team capability:** skill fit is computed individually while mandatory coverage is checked collectively at team level. Team synergy, diversity and coordination benefits are not independently optimized.
5. **Fixed/static allocations:** approved locks are hard constraints and can reduce feasible choice; the model does not account for mid-semester changes, scheduling conflicts, or changing skill profiles.
6. **Distinctness is not Pareto efficiency:** no-good cuts avoid duplicate allocations but do not ensure all alternatives lie on a Pareto frontier.
7. **Ambiguous qualification policy:** Julio approved ILP/PuLP as an approach but did not explicitly resolve whether mandatory skills apply collectively or per student. The currently implemented rule must be confirmed before final acceptance.
8. **Test and release scope:** passing automated tests supports correctness of tested cases, not proof of all possible user interactions or requirements. The merged product needs a reproducible browser demonstration and review of destructive project/skill deletion behavior.

---

## Finalization checklist (not submission content)

- [ ] **Team B:** Verify formulas and references against the actual \`solvers.py\` and \`metrics.py\`; obtain a verified citation for Rezaeinia et al. (2022) or document its absence transparently.
- [ ] **Team A:** Reconcile \`team-a/week2-polish\` with the integration branch; finalize Section 5 using the actual recommendation criteria and review the comparison UI.
- [ ] **Both teams:** Resolve the mandatory-skill interpretation if possible and identify all original starter test modifications versus any instructor restriction.
- [ ] **Both teams:** Rerun \`pytest -v\` on the **final integrated branch** and record the date, commit and results; do not reuse an old result as new evidence.
- [ ] **Both teams:** Execute and document a reproducible demonstration covering data entry, optimization, alternatives, comparisons, recommendations, fixed assignments and infeasibility.
- [ ] **Group 14 / Group 12:** Review authorship and document claims, then export the final analytical note to PDF/DOC for the **2 November 2026** Canvas submission.
