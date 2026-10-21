# Team B — Assignment Model Formulation (Week 1)

**Team B (Assignment Engine), Group 14:** Jakob Wilhelm Stenersen Hovdenak,
Faisal Mohammad Shaik, Victor Sandberg
**Status:** Proposed. Awaiting approval of the method by the course
responsible. Implementation is scheduled for Week 2. This document is the
source for Sections 2 and 6 of the analytical note
(`docs/analytical_note_template.md`).

---

## 1. Method and justification

We propose a **binary integer linear program (ILP)**, solved with
**PuLP + CBC** (open source; CBC ships in the PuLP wheel, so no system install
is needed). Pin `pulp==2.9.0`: on 2026-10-19 we checked it on macOS / Python
3.13, and a toy binary model solved `Optimal`. The latest PuLP 4.1.0 fails on
import because it needs numpy, which it does not declare. We add the pin to
`requirements.txt` once the method is approved.

Why an ILP rather than stable matching or a heuristic:

- Every business rule (one project per student, min/max headcount, locks,
  mandatory skills) is a **linear hard constraint**. An ILP either satisfies
  all of them or proves that none can be satisfied. A heuristic can only fail
  to find a solution, and stable matching does not support minimum quotas or
  team-level skill coverage.
- **Distinct alternatives** come straight from no-good cuts (§3.6): each new
  solve is guaranteed to differ from earlier ones, or the solver proves that
  no further feasible allocation exists (edge cases 14–15).
- Each strategy differs **only in its objective weights**, so it fits the
  `AssignmentStrategy` Strategy pattern directly. All strategies share one
  `solve()` model, and subclasses override `calculate_cost_or_utility()`.
- Scale: one cohort has about 10²–10³ students × 10–10² projects, so at most
  about 10⁵ binary variables. The model is close to a transportation problem
  (its LP relaxation is integral apart from the skill and minimax side
  constraints), so CBC solves it in seconds inside the single Flask process.

## 2. Sets and parameters

| Symbol | Meaning | Source in code |
|---|---|---|
| $S$ | students, $n = \lvert S\rvert$ | `models.Student` |
| $P$ | projects, $m = \lvert P\rvert$ | `models.Project` |
| $K$ | skill catalog | `models.Skill` |
| $F \subseteq S\times P$ | fixed locks | `models.FixedAssignment` |
| $M_p \subseteq K$ | mandatory skills of $p$ | `ProjectRequirement.is_mandatory` |
| $K_p \subseteq K$ | all required skills of $p$ | `Project.requirements` |
| $l_p, u_p$ | min / max headcount, $0\le l_p\le u_p$, $u_p\ge1$ | `min_capacity`, `max_capacity` |
| $a_{s,k}\in\{0,\dots,5\}$ | proficiency of $s$ in $k$ (0 = not held) | `Student.get_skill_level` |
| $q_{p,k}\in\{1,\dots,5\}$ | required level of $k$ for $p$ | `minimum_level` |
| $r_{s,p}$ | rank of $p$ for $s$; **unranked → $R+1$** | `Student.get_preference_rank` |
| $R$ | longest preference list in cohort | `max_preferences` argument |
| $Q_{p,k}=\{s: a_{s,k}\ge q_{p,k}\}$ | students qualified for requirement $(p,k)$ | derived |

**Derived scores (both normalised to $[0,1]$, so they can be traded off on one
scale):**

- Preference utility
  $$w_{s,p}=\begin{cases}\dfrac{R+1-r_{s,p}}{R} & p \text{ ranked by } s \text{ and } R \ge 1\\[4pt] 0 & \text{otherwise}\end{cases}$$
  First choice = 1, last ranked choice = $1/R$, unranked = 0. When no student in the cohort submits any ranked preferences ($R = 0$), $w_{s,p} = 0\ \forall s,p$, avoiding division by zero; the preference objective becomes zero and the solver allocates based on the secondary tie-breaker (skill fit).
- Skill fit
  $$\sigma_{s,p}=\begin{cases}1 & K_p=\emptyset\\[2pt] \dfrac{1}{\lvert K_p\rvert}\displaystyle\sum_{k\in K_p}\min\!\Big(\frac{a_{s,k}}{q_{p,k}},1\Big) & \text{otherwise}\end{cases}$$
  A project with no requirements is a neutral fit, 1.0 (edge case 4). A student
  with no skills scores 0.0 (edge case 3). Over-qualification is capped at 1,
  so one strong skill cannot hide a missing one.

## 3. Decision variables and hard constraints

$x_{s,p}\in\{0,1\}$ is 1 if student $s$ is assigned to project $p$.
$z\in\mathbb{Z}_{\ge0}$ is the worst assigned rank, used only by the
balanced strategy.

1. **Exact allocation:** $\sum_{p} x_{s,p}=1\quad\forall s\in S$
2. **Headcount bounds:** $l_p\le\sum_{s}x_{s,p}\le u_p\quad\forall p\in P$
3. **Locks:** $x_{s,p}=1\quad\forall (s,p)\in F$
4. **Mandatory skills: at least one qualified member in any staffed project**
   $$u_p\sum_{s\in Q_{p,k}}x_{s,p}\;\ge\;\sum_{s\in S}x_{s,p}\qquad\forall p\in P,\;k\in M_p$$
   If the project is empty, both sides are 0. If it is staffed, the right-hand
   side is at most $u_p$, so the left-hand side forces at least one qualified
   member. This needs no auxiliary "project open" variable.
   *Clarification requested from the course responsible:* we read "mandatory"
   as *at least one qualified member per project*, not *every member
   qualified*. Under the stricter reading the constraint becomes
   $x_{s,p}=0\ \forall s\notin Q_{p,k}$. That is a one-line change.
5. **Worst-rank link (balanced only):** $z\ge r_{s,p}\,x_{s,p}\quad\forall s,p$
6. **No-good cut** for every earlier solution $A^{(t)}=\{(s,p):x^{(t)}_{s,p}=1\}$:
   $$\sum_{(s,p)\in A^{(t)}}x_{s,p}\;\le\;n-1$$
   Each student holds exactly one assignment, so this forces at least one
   student to move. Fixed students cannot move, so effectively the cut acts
   only on the free students. Infeasibility after a cut means "no further
   distinct alternative exists". The run then stops and reports
   `distinct_alternatives = t`. It does not fabricate duplicates.

## 4. Objectives (one per strategy key)

$\varepsilon$ serves as a secondary tie-breaker. For strict lexicographic priority
where the secondary criterion never overturns even a single rank difference in the
primary criterion, the maximum possible cohort-wide secondary contribution ($n \cdot \varepsilon$)
must be strictly less than the smallest non-zero primary step ($\min \Delta w = 1/R$).
Hence, rather than a static $\varepsilon = 10^{-3}$ (which for $n \ge 100, R \ge 10$ yields
$n \varepsilon \ge 1/R$), the solver in Week 2 will dynamically set:
$$\varepsilon = \frac{1}{2 \cdot n \cdot \max(R, 1)}$$
or solve hierarchically (optimizing primary first, then secondary subject to primary optimal value).
This makes results deterministic, explainable, and theoretically sound.

| Strategy key | Class | Objective |
|---|---|---|
| `PREFERENCE` | `PreferenceOrientedSolver` | $\max \sum_{s,p}(w_{s,p}+\varepsilon\,\sigma_{s,p})\,x_{s,p}$ |
| `SKILL_FIT` | `SkillFitOrientedSolver` | $\max \sum_{s,p}(\sigma_{s,p}+\varepsilon\,w_{s,p})\,x_{s,p}$ |
| `BALANCED` | `BalancedTradeoffSolver` | $\max \sum_{s,p}\big(\lambda w_{s,p}+(1-\lambda)\sigma_{s,p}\big)x_{s,p}-\mu\,\dfrac{z}{R+1}$ |

Defaults: $\lambda=0.5$, $\mu=1$. The $\mu$ term is the fairness lever. It
lowers the worst-off student's rank at a cost of at most about one unit of
total utility. Both values are module constants, so the analytical note can
report a sensitivity check.

## 5. Run status mapping (contract `RunStatus`)

| Condition | Status |
|---|---|
| validation reports `is_feasible = False` | `INFEASIBLE` (edge case 13), with reasons copied into diagnostics |
| validation reports other errors | `INVALID_INPUT` |
| CBC returns *Infeasible* on the first solve | `INFEASIBLE`, solver diagnostics attached |
| ≥1 solution found | `COMPLETED`, `diagnostics.distinct_alternatives` = number found |
| solver exception / time limit with no incumbent | `FAILED` |

## 6. Input validation: rules that protect the model

Every check in `app/domain/validation.py` corresponds to a model assumption.
A **✚** marks rules added in Week 1. Each has a test in
`tests/test_input_validation.py`.

| Rule | Severity | Protects |
|---|---|---|
| Non-empty cohort and catalog, unique IDs | error | index sets well-defined |
| $0\le l_p\le u_p$, $u_p\ge1$ | error | constraint 2 |
| Preference references a known project | error | $r_{s,p}$ defined |
| ✚ Rank $\ge 1$ | error | $w_{s,p}\le 1$ |
| ✚ Preference belongs to the student carrying it | error | data integrity (DB PK) |
| Duplicate rank / project in one list | warning | $w$ still computable |
| ✚ Skill level $<0$ | error | $\sigma\ge0$ |
| ✚ Skill level $>5$ / requirement level $>5$ | warning | scale assumption |
| ✚ Requirement level $<1$ | error | division by $q_{p,k}$ in $\sigma$ |
| ✚ Same skill required twice by one project | error | $K_p$ is a set (DB PK) |
| ✚ Requirement belongs to its project | error | data integrity |
| Uncatalogued skill IDs | warning | treated as level 0 |
| Lock references a known student / project | error | constraint 3 |
| Student locked to ≥2 *different* projects | error | 1 vs 3 contradiction |
| ✚ Identical lock entered twice | warning (was a false "contradictory" error) | idempotent locks |
| Locks on $p$ exceed $u_p$ | infeasible | 2 vs 3 |
| $n>\sum u_p$ or $n<\sum l_p$ | infeasible | 1 vs 2 aggregate |
| ✚ Unlocked students $<\sum_p\max(l_p-\lvert F_p\rvert,0)$ | infeasible | 1+2+3 jointly |
| Mandatory skill with $Q_{p,k}=\emptyset$ and project forced open ($l_p\ge1$ **or ✚ locked**) | infeasible | constraint 4 |
| ✚ Mandatory skill with $Q_{p,k}=\emptyset$ but $l_p=0$, no lock | warning, as the project simply stays empty | constraint 4 (previously a false error) |
| ✚ Locks fill $p$ to $u_p$ with no qualified member | infeasible | 3 vs 4 |
| ✚ Strategy key ∉ {PREFERENCE, SKILL_FIT, BALANCED} | error | objective selection |
| ✚ `max_alternatives` ∉ [1, 10] | error | cut loop bound |

Validation is a set of **necessary conditions only**. Some infeasible cases
remain for CBC to prove, for example two $l_p\ge1$ projects that both need
the single rust-qualified student. The solver then reports `INFEASIBLE` with
its own diagnostics.

## 7. Known limitations (carried into the analytical note §7)

- Additive utility: one student's gain offsets another's loss. Only the
  balanced strategy's $z$ term protects the worst-off student.
- Unranked projects all share rank $R+1$, so the model cannot tell an
  "acceptable" unranked project from an "unwanted" one.
- Skill fit is individual. Team complementarity (covering *different* skills
  across members) is modelled only through the mandatory constraint.
- No-good cuts list alternatives in objective order. They are distinct but not
  necessarily Pareto-diverse, and alternatives may differ by a single swap.
