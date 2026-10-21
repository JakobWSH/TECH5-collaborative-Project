"""Calculators for feasibility, efficiency, fairness, and trade-offs.

This module provides analytical functions to evaluate solutions according to
the requirements in Section 7 of the TECH5 specification.

Students (Team B) implement these analytical functions to compute
student-project skill fit, Gini inequality, solution indicators, and
side-by-side trade-off comparisons.
"""

from typing import Any

from app.domain import models


def calculate_assignment_skill_fit(
    student: models.Student,
    project: models.Project,
) -> tuple[float, list[str]]:
    """Calculates skill fit score and unmet requirements for a student-project pair.

    In compliance with Section 7.2 of the TECH5 specification, skill fit
    evaluates how well the candidate student satisfies the required technical
    skills of the target project.

    The score is the mean over all project requirements of
    ``min(student_level / requirement_level, 1.0)``.  A project with no
    requirements returns a perfect score of 1.0.  A student who possesses
    none of the required skills scores 0.0.

    Args:
        student: The student under evaluation.
        project: The project under evaluation.

    Returns:
        A tuple of (skill_fit_score [0.0, 1.0], list_of_unmet_skill_ids).
        The score is rounded to 4 decimal places.
    """
    if not project.requirements:
        # Edge case: project with no requirements → perfect fit, nothing unmet.
        return 1.0, []

    scores: list[float] = []
    unmet: list[str] = []

    for req in project.requirements:
        student_level = student.get_skill_level(req.skill_id)
        # Avoid division by zero (minimum_level defaults to 1, but be safe).
        if req.minimum_level <= 0:
            scores.append(1.0)
        else:
            scores.append(min(student_level / req.minimum_level, 1.0))
        if student_level < req.minimum_level:
            unmet.append(req.skill_id)

    fit = round(sum(scores) / len(scores), 4)
    return fit, unmet


def calculate_gini(values: list[float]) -> float:
    """Calculates the Gini coefficient of inequality for non-negative values.

    In compliance with Section 7.3 of the TECH5 specification, the Gini
    coefficient measures the inequality/fairness in student preference rank
    distribution (0.0 represents perfect equality, 1.0 represents extreme
    inequality).

    Uses the standard discrete formula:
        G = (2 * Σ_{i=1}^{n} i·y_i) / (n · Σ y_i) − (n+1)/n
    where y_i are the sorted (ascending) values.

    Args:
        values: Non-negative numerical series (e.g. assigned preference ranks).
            An empty list or all-zero list returns 0.0.

    Returns:
        The Gini coefficient in [0.0, 1.0].
    """
    n = len(values)
    if n == 0:
        return 0.0

    if any(v < 0 for v in values):
        raise ValueError("Gini coefficient requires non-negative values.")
    total = sum(values)
    if total == 0.0:
        # All values are zero → perfect equality.
        return 0.0

    sorted_vals = sorted(values)
    weighted_sum = sum((i + 1) * v for i, v in enumerate(sorted_vals))
    gini = (2.0 * weighted_sum) / (n * total) - (n + 1) / n
    # Clamp to [0, 1] to absorb any floating-point rounding artefacts.
    return max(0.0, min(1.0, gini))


def compute_solution_indicators(
    students: list[models.Student],
    projects: list[models.Project],
    assignments: list[models.Assignment],
    fixed_assignments: list[models.FixedAssignment] | None = None,
) -> dict[str, Any]:
    """Computes comprehensive feasibility, efficiency, and fairness indicators.

    Evaluates a solution across the four dimensions defined in the specification:
    1. Feasibility: Exact student count, capacity bounds, fixed assignments.
    2. Efficiency: Mean skill-fit score, unmet soft requirements count.
    3. Fairness: Rank distribution, mean rank, worst rank, unranked count, Gini.
    4. Capacity: Total assigned, total capacity, overall utilization, per-project.

    The function reads ``assignment.preference_rank`` and
    ``assignment.skill_fit_score`` that were set by the solver; it does NOT
    re-derive ranks from student preference lists.

    Args:
        students: Complete cohort of students.
        projects: Catalog of semester projects.
        assignments: List of student-to-project allocations.
        fixed_assignments: Optional list of locked pre-allocations.

    Returns:
        Dictionary containing structured indicators and diagnostic metrics:
        {
            "feasibility": {"is_feasible": bool, "violations": list[str], ...},
            "efficiency": {"mean_skill_fit": float, ...},
            "fairness": {"mean_rank": float, "worst_rank": int, "rank_gini": float, ...},
            "capacity": {"overall_utilization_pct": float, "projects": dict, ...}
        }
    """
    fixed_assignments = fixed_assignments or []
    violations: list[str] = []

    # ------------------------------------------------------------------ #
    # Feasibility                                                          #
    # ------------------------------------------------------------------ #
    assigned_student_ids = {a.student_id for a in assignments}
    total_students = len(students)
    assigned_count = len(assigned_student_ids)

    # An assignment must refer to exactly one known student and project.
    known_students = {s.id for s in students}
    known_projects = {p.id for p in projects}
    if len(assignments) != assigned_count:
        violations.append("Duplicate student assignments found.")
    for a in assignments:
        if a.student_id not in known_students:
            violations.append(f"Assignment references unknown student '{a.student_id}'.")
        if a.project_id not in known_projects:
            violations.append(f"Assignment references unknown project '{a.project_id}'.")

    # Every student must appear in exactly one assignment.
    unassigned = [s.id for s in students if s.id not in assigned_student_ids]
    if unassigned:
        violations.append(
            f"Unassigned students: {unassigned}"
        )

    # Fixed assignments must be honoured.
    assignment_map: dict[str, str] = {
        a.student_id: a.project_id for a in assignments
    }
    for fa in fixed_assignments:
        actual = assignment_map.get(fa.student_id)
        if actual != fa.project_id:
            violations.append(
                f"Fixed assignment violated: student '{fa.student_id}' "
                f"should be in project '{fa.project_id}' but is in "
                f"'{actual}'."
            )

    # Capacity bounds.
    project_map: dict[str, models.Project] = {p.id: p for p in projects}
    project_assignment_counts: dict[str, int] = {}
    for a in assignments:
        project_assignment_counts[a.project_id] = (
            project_assignment_counts.get(a.project_id, 0) + 1
        )

    for project in projects:
        count = project_assignment_counts.get(project.id, 0)
        if count > project.max_capacity:
            violations.append(
                f"Project '{project.id}' over capacity: "
                f"{count} assigned, max {project.max_capacity}."
            )
        if project.min_capacity > 0 and count < project.min_capacity:
            violations.append(
                f"Project '{project.id}' under minimum capacity: "
                f"{count} assigned, min {project.min_capacity}."
            )

    # Project-level mandatory skills: every staffed project must contain at
    # least one student meeting each mandatory requirement (provisional rule).
    students_by_id = {s.id: s for s in students}
    for project in projects:
        assigned = [
            students_by_id[a.student_id]
            for a in assignments
            if a.project_id == project.id and a.student_id in students_by_id
        ]
        if not assigned:
            continue
        for req in project.requirements:
            if req.is_mandatory and not any(
                student.get_skill_level(req.skill_id) >= req.minimum_level
                for student in assigned
            ):
                violations.append(
                    f"Mandatory skill '{req.skill_id}' is not covered "
                    f"in staffed project '{project.id}'."
                )

    is_feasible = len(violations) == 0

    feasibility: dict[str, Any] = {
        "is_feasible": is_feasible,
        "violations": violations,
        "assigned_count": assigned_count,
        "total_students": total_students,
    }

    # ------------------------------------------------------------------ #
    # Efficiency                                                           #
    # ------------------------------------------------------------------ #
    skill_fit_scores = [a.skill_fit_score for a in assignments]
    # Only unmet non-mandatory requirements are soft. Mandatory coverage is
    # tested above as a team-level feasibility constraint.
    unmet_count = 0
    for a in assignments:
        project = project_map.get(a.project_id)
        if project is not None:
            soft_ids = {req.skill_id for req in project.requirements if not req.is_mandatory}
            unmet_count += sum(skill in soft_ids for skill in a.unmet_requirements)

    if skill_fit_scores:
        mean_skill_fit = round(sum(skill_fit_scores) / len(skill_fit_scores), 4)
        total_skill_fit_sum = round(sum(skill_fit_scores), 4)
    else:
        mean_skill_fit = 0.0
        total_skill_fit_sum = 0.0

    efficiency: dict[str, Any] = {
        "mean_skill_fit": mean_skill_fit,
        "unmet_soft_requirements_count": unmet_count,
        "total_skill_fit_sum": total_skill_fit_sum,
    }

    # ------------------------------------------------------------------ #
    # Fairness                                                             #
    # ------------------------------------------------------------------ #
    ranks: list[int] = []
    unranked_count = 0
    rank_distribution: dict[str, int] = {}

    for a in assignments:
        if a.preference_rank is not None:
            ranks.append(a.preference_rank)
            key = f"rank_{a.preference_rank}"
            rank_distribution[key] = rank_distribution.get(key, 0) + 1
        else:
            unranked_count += 1

    unranked_pct = round(
        (unranked_count / total_students * 100) if total_students > 0 else 0.0,
        2,
    )
    worst_rank = max(ranks) if ranks else 0
    mean_rank = round(sum(ranks) / len(ranks), 4) if ranks else 0.0
    rank_variance = (
        round(
            sum((r - mean_rank) ** 2 for r in ranks) / len(ranks),
            4,
        )
        if ranks
        else 0.0
    )
    rank_gini = calculate_gini([float(r) for r in ranks]) if ranks else 0.0

    fairness: dict[str, Any] = {
        "rank_distribution": rank_distribution,
        "unranked_count": unranked_count,
        "unranked_pct": unranked_pct,
        "worst_rank": worst_rank,
        "mean_rank": mean_rank,
        "rank_variance": rank_variance,
        "rank_gini": rank_gini,
    }

    # ------------------------------------------------------------------ #
    # Capacity                                                             #
    # ------------------------------------------------------------------ #
    total_max_capacity = sum(p.max_capacity for p in projects)
    overall_utilization_pct = (
        round(assigned_count / total_max_capacity * 100, 2)
        if total_max_capacity > 0
        else 0.0
    )

    projects_capacity: dict[str, Any] = {}
    for project in projects:
        count = project_assignment_counts.get(project.id, 0)
        utilization = (
            round(count / project.max_capacity * 100, 2)
            if project.max_capacity > 0
            else 0.0
        )
        projects_capacity[project.id] = {
            "assigned_count": count,
            "min_capacity": project.min_capacity,
            "max_capacity": project.max_capacity,
            "utilization_pct": utilization,
        }

    capacity: dict[str, Any] = {
        "total_assigned": assigned_count,
        "total_capacity": total_max_capacity,
        "overall_utilization_pct": overall_utilization_pct,
        "projects": projects_capacity,
    }

    return {
        "feasibility": feasibility,
        "efficiency": efficiency,
        "fairness": fairness,
        "capacity": capacity,
    }


def compare_two_solutions(
    solution_a: models.Solution,
    solution_b: models.Solution,
) -> dict[str, Any]:
    """Performs detailed trade-off comparison between two alternative solutions.

    In compliance with Section 7.4 of the specification, identifies:
    - Changed student allocations between solutions A and B.
    - Improved and worsened student preference ranks.
    - Deltas in mean skill-fit, mean rank, and Gini coefficient.
    - Human-readable trade-off summary statements.

    Skill-fit and rank deltas are read directly from each solution's stored
    ``indicators`` dictionary so that the comparison reflects the same values
    that were persisted with the solution (rather than recomputing from
    assignments, which may use a different cohort context).

    Args:
        solution_a: Baseline solution.
        solution_b: Alternative solution to compare against A.

    Returns:
        Dictionary documenting differences, changed assignments, and trade-offs.
        Includes both top-level convenience keys and a nested ``delta_metrics``
        sub-dictionary for structured consumption by Team A's UI.
    """
    # Build per-student assignment lookup for both solutions.
    map_a: dict[str, models.Assignment] = {
        a.student_id: a for a in solution_a.assignments
    }
    map_b: dict[str, models.Assignment] = {
        a.student_id: a for a in solution_b.assignments
    }

    all_student_ids = set(map_a) | set(map_b)

    changed_assignments: list[dict[str, Any]] = []
    rank_improved_count = 0
    rank_worsened_count = 0

    for sid in sorted(all_student_ids):
        a_assign = map_a.get(sid)
        b_assign = map_b.get(sid)

        # Determine whether the project changed.
        proj_a = a_assign.project_id if a_assign else None
        proj_b = b_assign.project_id if b_assign else None

        if proj_a == proj_b:
            continue  # No change for this student.

        rank_a = a_assign.preference_rank if a_assign else None
        rank_b = b_assign.preference_rank if b_assign else None

        # Rank direction: lower rank number = better.
        if rank_a is None and rank_b is not None:
            rank_improved_count += 1
        elif rank_b is None and rank_a is not None:
            rank_worsened_count += 1
        elif rank_a is not None and rank_b is not None:
            if rank_b < rank_a:
                rank_improved_count += 1
            elif rank_b > rank_a:
                rank_worsened_count += 1

        changed_assignments.append(
            {
                "student_id": sid,
                "project_a": proj_a,
                "project_b": proj_b,
                "rank_a": rank_a,
                "rank_b": rank_b,
                "skill_fit_a": (
                    a_assign.skill_fit_score if a_assign else None
                ),
                "skill_fit_b": (
                    b_assign.skill_fit_score if b_assign else None
                ),
            }
        )

    changed_students_count = len(changed_assignments)
    is_distinct = changed_students_count > 0

    # ------------------------------------------------------------------ #
    # Delta metrics — read from stored indicators to stay consistent with #
    # whatever values were computed and persisted for each solution.       #
    # ------------------------------------------------------------------ #
    eff_a = solution_a.indicators.get("efficiency", {})
    eff_b = solution_b.indicators.get("efficiency", {})
    fair_a = solution_a.indicators.get("fairness", {})
    fair_b = solution_b.indicators.get("fairness", {})

    mean_fit_a = float(eff_a.get("mean_skill_fit", 0.0))
    mean_fit_b = float(eff_b.get("mean_skill_fit", 0.0))
    delta_mean_skill_fit = round(mean_fit_b - mean_fit_a, 4)

    mean_rank_a = float(fair_a.get("mean_rank", 0.0))
    mean_rank_b = float(fair_b.get("mean_rank", 0.0))
    delta_mean_rank = round(mean_rank_b - mean_rank_a, 2)

    gini_a = float(fair_a.get("rank_gini", 0.0))
    gini_b = float(fair_b.get("rank_gini", 0.0))
    gini_delta = round(gini_b - gini_a, 4)

    unranked_a = int(fair_a.get("unranked_count", 0))
    unranked_b = int(fair_b.get("unranked_count", 0))
    delta_unranked_count = unranked_b - unranked_a

    delta_metrics: dict[str, Any] = {
        "mean_skill_fit_delta": delta_mean_skill_fit,
        "mean_rank_delta": delta_mean_rank,
        "gini_delta": gini_delta,
        "delta_unranked_count": delta_unranked_count,
    }

    # ------------------------------------------------------------------ #
    # Trade-off summary — human-readable sentences for decision makers.   #
    # ------------------------------------------------------------------ #
    trade_off_summary: list[str] = []

    if not is_distinct:
        trade_off_summary.append(
            "Solutions A and B are identical; no trade-offs to report."
        )
    else:
        if delta_mean_skill_fit > 0:
            trade_off_summary.append(
                f"Solution B improves mean skill fit by "
                f"{delta_mean_skill_fit:+.4f} (B: {mean_fit_b:.4f} vs "
                f"A: {mean_fit_a:.4f})."
            )
        elif delta_mean_skill_fit < 0:
            trade_off_summary.append(
                f"Solution B reduces mean skill fit by "
                f"{delta_mean_skill_fit:+.4f} (B: {mean_fit_b:.4f} vs "
                f"A: {mean_fit_a:.4f})."
            )

        if delta_mean_rank > 0:
            trade_off_summary.append(
                f"Solution B worsens mean preference rank by "
                f"{delta_mean_rank:+.2f} (B: {mean_rank_b:.2f} vs "
                f"A: {mean_rank_a:.2f}; higher = worse)."
            )
        elif delta_mean_rank < 0:
            trade_off_summary.append(
                f"Solution B improves mean preference rank by "
                f"{delta_mean_rank:+.2f} (B: {mean_rank_b:.2f} vs "
                f"A: {mean_rank_a:.2f}; lower = better)."
            )

        if rank_improved_count > 0:
            trade_off_summary.append(
                f"{rank_improved_count} student(s) receive a better rank "
                f"in solution B."
            )
        if rank_worsened_count > 0:
            trade_off_summary.append(
                f"{rank_worsened_count} student(s) receive a worse rank "
                f"in solution B."
            )

        if delta_unranked_count > 0:
            trade_off_summary.append(
                f"Solution B has {delta_unranked_count} more unranked "
                f"student(s) than solution A."
            )
        elif delta_unranked_count < 0:
            trade_off_summary.append(
                f"Solution B has {abs(delta_unranked_count)} fewer unranked "
                f"student(s) than solution A."
            )

    return {
        # Top-level convenience keys (consumed directly by tests and UI).
        "solution_a_id": solution_a.id,
        "solution_a_alt": solution_a.alternative_number,
        "solution_b_id": solution_b.id,
        "solution_b_alt": solution_b.alternative_number,
        "total_students": len(all_student_ids),
        "is_distinct": is_distinct,
        "changed_students_count": changed_students_count,
        "changed_assignments": changed_assignments,
        "rank_improved_count": rank_improved_count,
        "rank_worsened_count": rank_worsened_count,
        "delta_mean_skill_fit": delta_mean_skill_fit,
        "delta_mean_rank": delta_mean_rank,
        "delta_unranked_count": delta_unranked_count,
        # Nested delta_metrics sub-dictionary for Team A's UI.
        "delta_metrics": delta_metrics,
        "trade_off_summary": trade_off_summary,
    }
