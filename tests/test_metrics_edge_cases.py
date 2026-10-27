"""Edge-case tests for app/engine/metrics.py.

Covers boundary conditions not exercised by test_metrics.py:
- Empty inputs (no students, no assignments, no projects)
- Projects with zero skill requirements (perfect fit)
- Students with zero / partial skills
- All-zero Gini (perfect equality) and high-inequality Gini
- Unranked students in indicators
- Infeasible solutions detected via indicators
- Capacity edge cases (over-capacity, under-minimum)
- compare_two_solutions with identical solutions and missing indicators
"""

import pytest

from app.domain import models
from app.engine import metrics


# ======================================================================== #
# calculate_assignment_skill_fit                                            #
# ======================================================================== #


class TestSkillFitEdgeCases:
    """Edge cases for calculate_assignment_skill_fit."""

    def test_no_requirements_returns_perfect_fit(self) -> None:
        """A project with no requirements → score 1.0, nothing unmet."""
        student = models.Student(id="S1", display_name="S1", skills={})
        project = models.Project(id="P1", title="P1", requirements=[])
        fit, unmet = metrics.calculate_assignment_skill_fit(student, project)
        assert fit == 1.0
        assert unmet == []

    def test_student_with_zero_skills(self) -> None:
        """Student with no skills scores 0.0 and all requirements are unmet."""
        student = models.Student(id="S1", display_name="S1", skills={})
        project = models.Project(
            id="P1",
            title="P1",
            requirements=[
                models.ProjectRequirement(
                    project_id="P1", skill_id="py", minimum_level=2
                ),
                models.ProjectRequirement(
                    project_id="P1", skill_id="sql", minimum_level=1
                ),
            ],
        )
        fit, unmet = metrics.calculate_assignment_skill_fit(student, project)
        assert fit == 0.0
        assert set(unmet) == {"py", "sql"}

    def test_student_exceeding_requirement_capped_at_1(self) -> None:
        """Skill level above the requirement is capped at 1.0 contribution."""
        student = models.Student(id="S1", display_name="S1", skills={"py": 5})
        project = models.Project(
            id="P1",
            title="P1",
            requirements=[
                models.ProjectRequirement(
                    project_id="P1", skill_id="py", minimum_level=3
                ),
            ],
        )
        fit, unmet = metrics.calculate_assignment_skill_fit(student, project)
        assert fit == 1.0
        assert unmet == []

    def test_partial_skill_match(self) -> None:
        """One skill met, one unmet → average of 1.0 and partial score."""
        student = models.Student(
            id="S1", display_name="S1", skills={"a": 3, "b": 1}
        )
        project = models.Project(
            id="P1",
            title="P1",
            requirements=[
                models.ProjectRequirement(
                    project_id="P1", skill_id="a", minimum_level=3
                ),
                models.ProjectRequirement(
                    project_id="P1", skill_id="b", minimum_level=4
                ),
            ],
        )
        fit, unmet = metrics.calculate_assignment_skill_fit(student, project)
        # a: 3/3 = 1.0, b: 1/4 = 0.25; mean = 0.625
        assert fit == 0.625
        assert unmet == ["b"]

    def test_single_requirement_exactly_met(self) -> None:
        """Score is exactly 1.0 when student level equals minimum_level."""
        student = models.Student(id="S1", display_name="S1", skills={"py": 2})
        project = models.Project(
            id="P1",
            title="P1",
            requirements=[
                models.ProjectRequirement(
                    project_id="P1", skill_id="py", minimum_level=2
                ),
            ],
        )
        fit, unmet = metrics.calculate_assignment_skill_fit(student, project)
        assert fit == 1.0
        assert unmet == []

    def test_unknown_skill_treated_as_zero(self) -> None:
        """A skill not in the student's profile is treated as level 0."""
        student = models.Student(id="S1", display_name="S1", skills={"py": 3})
        project = models.Project(
            id="P1",
            title="P1",
            requirements=[
                models.ProjectRequirement(
                    project_id="P1", skill_id="r_lang", minimum_level=2
                ),
            ],
        )
        fit, unmet = metrics.calculate_assignment_skill_fit(student, project)
        assert fit == 0.0
        assert unmet == ["r_lang"]


# ======================================================================== #
# calculate_gini                                                            #
# ======================================================================== #


class TestGiniEdgeCases:
    """Edge cases for calculate_gini."""

    def test_empty_list_returns_zero(self) -> None:
        assert metrics.calculate_gini([]) == 0.0

    def test_single_value_returns_zero(self) -> None:
        assert metrics.calculate_gini([5.0]) == 0.0

    def test_all_zeros_returns_zero(self) -> None:
        assert metrics.calculate_gini([0.0, 0.0, 0.0]) == 0.0

    def test_perfect_equality(self) -> None:
        """Identical values → Gini = 0.0."""
        assert metrics.calculate_gini([3.0, 3.0, 3.0, 3.0]) == 0.0

    def test_high_inequality(self) -> None:
        """One very large value → Gini close to 1."""
        gini = metrics.calculate_gini([1.0, 1.0, 1.0, 97.0])
        assert 0.5 < gini < 1.0

    def test_two_equal_values(self) -> None:
        assert metrics.calculate_gini([4.0, 4.0]) == 0.0

    def test_result_in_unit_interval(self) -> None:
        """Gini is always in [0, 1]."""
        for vals in [
            [1.0, 2.0, 3.0, 4.0, 5.0],
            [10.0, 0.0, 0.0, 0.0, 100.0],
            [1.0],
            [1.0, 1000.0],
        ]:
            g = metrics.calculate_gini(vals)
            assert 0.0 <= g <= 1.0, f"Gini {g} out of range for {vals}"


# ======================================================================== #
# compute_solution_indicators                                               #
# ======================================================================== #


class TestSolutionIndicatorsEdgeCases:
    """Edge cases for compute_solution_indicators."""

    def test_empty_assignments(self) -> None:
        """No assignments → all students unassigned, feasibility fails."""
        students = [
            models.Student(id="S1", display_name="S1"),
            models.Student(id="S2", display_name="S2"),
        ]
        projects = [models.Project(id="P1", title="P1", max_capacity=2)]
        indicators = metrics.compute_solution_indicators(
            students=students, projects=projects, assignments=[]
        )
        assert indicators["feasibility"]["is_feasible"] is False
        assert indicators["capacity"]["total_assigned"] == 0
        assert indicators["efficiency"]["mean_skill_fit"] == 0.0
        assert indicators["fairness"]["unranked_count"] == 0

    def test_no_students_no_assignments(self) -> None:
        """Empty cohort with empty assignments → feasible (nothing to do)."""
        projects = [models.Project(id="P1", title="P1", max_capacity=5)]
        indicators = metrics.compute_solution_indicators(
            students=[], projects=[], assignments=[]
        )
        assert indicators["feasibility"]["is_feasible"] is True
        assert indicators["capacity"]["overall_utilization_pct"] == 0.0

    def test_unranked_students_counted(self) -> None:
        """Students assigned to projects they did not rank → unranked_count."""
        students = [
            models.Student(id="S1", display_name="S1"),  # no preferences
            models.Student(id="S2", display_name="S2"),
        ]
        projects = [models.Project(id="P1", title="P1", max_capacity=2)]
        assignments = [
            models.Assignment(
                student_id="S1",
                project_id="P1",
                preference_rank=None,  # unranked
                skill_fit_score=0.5,
            ),
            models.Assignment(
                student_id="S2",
                project_id="P1",
                preference_rank=1,
                skill_fit_score=0.8,
            ),
        ]
        indicators = metrics.compute_solution_indicators(
            students=students, projects=projects, assignments=assignments
        )
        assert indicators["fairness"]["unranked_count"] == 1
        assert indicators["fairness"]["unranked_pct"] == 50.0
        # Only S2's rank (1) contributes to mean_rank.
        assert indicators["fairness"]["mean_rank"] == 1.0

    def test_all_unranked(self) -> None:
        """All students unranked → mean_rank is 0.0, Gini is 0.0."""
        students = [models.Student(id="S1", display_name="S1")]
        projects = [models.Project(id="P1", title="P1", max_capacity=1)]
        assignments = [
            models.Assignment(
                student_id="S1",
                project_id="P1",
                preference_rank=None,
                skill_fit_score=0.6,
            )
        ]
        indicators = metrics.compute_solution_indicators(
            students=students, projects=projects, assignments=assignments
        )
        assert indicators["fairness"]["unranked_count"] == 1
        assert indicators["fairness"]["mean_rank"] == 0.0
        assert indicators["fairness"]["rank_gini"] == 0.0

    def test_over_capacity_flagged(self) -> None:
        """Assigning more students than max_capacity → infeasible."""
        students = [
            models.Student(id=f"S{i}", display_name=f"S{i}") for i in range(3)
        ]
        projects = [
            models.Project(id="P1", title="P1", max_capacity=2)
        ]  # max 2
        assignments = [
            models.Assignment(
                student_id=f"S{i}",
                project_id="P1",
                preference_rank=i + 1,
                skill_fit_score=1.0,
            )
            for i in range(3)
        ]
        indicators = metrics.compute_solution_indicators(
            students=students, projects=projects, assignments=assignments
        )
        assert indicators["feasibility"]["is_feasible"] is False
        assert any(
            "over capacity" in v
            for v in indicators["feasibility"]["violations"]
        )

    def test_fixed_assignment_violation_flagged(self) -> None:
        """A fixed assignment placed in a different project → infeasible."""
        students = [models.Student(id="S1", display_name="S1")]
        projects = [
            models.Project(id="P1", title="P1", max_capacity=1),
            models.Project(id="P2", title="P2", max_capacity=1),
        ]
        fixed = [models.FixedAssignment(student_id="S1", project_id="P1")]
        assignments = [
            models.Assignment(
                student_id="S1",
                project_id="P2",  # violates fixed assignment
                preference_rank=1,
                skill_fit_score=1.0,
            )
        ]
        indicators = metrics.compute_solution_indicators(
            students=students,
            projects=projects,
            assignments=assignments,
            fixed_assignments=fixed,
        )
        assert indicators["feasibility"]["is_feasible"] is False
        assert any(
            "Fixed assignment violated" in v
            for v in indicators["feasibility"]["violations"]
        )

    def test_utilization_per_project(self) -> None:
        """Per-project utilization is calculated correctly."""
        students = [
            models.Student(id="S1", display_name="S1"),
            models.Student(id="S2", display_name="S2"),
        ]
        projects = [
            models.Project(id="P1", title="P1", max_capacity=4),
        ]
        assignments = [
            models.Assignment(
                student_id="S1",
                project_id="P1",
                preference_rank=1,
                skill_fit_score=1.0,
            ),
            models.Assignment(
                student_id="S2",
                project_id="P1",
                preference_rank=1,
                skill_fit_score=1.0,
            ),
        ]
        indicators = metrics.compute_solution_indicators(
            students=students, projects=projects, assignments=assignments
        )
        assert (
            indicators["capacity"]["projects"]["P1"]["utilization_pct"] == 50.0
        )
        assert indicators["capacity"]["overall_utilization_pct"] == 50.0


# ======================================================================== #
# compare_two_solutions                                                     #
# ======================================================================== #


class TestCompareTwoSolutionsEdgeCases:
    """Edge cases for compare_two_solutions."""

    def _make_solution(
        self,
        sol_id: str,
        assignments: list[models.Assignment],
        indicators: dict | None = None,
    ) -> models.Solution:
        return models.Solution(
            id=sol_id,
            run_id="run-1",
            alternative_number=1,
            strategy_name="PREFERENCE",
            assignments=assignments,
            indicators=indicators or {},
        )

    def test_identical_solutions_not_distinct(self) -> None:
        """Two solutions with the same assignments → is_distinct False."""
        a1 = models.Assignment(
            student_id="S1", project_id="P1", preference_rank=1
        )
        sol_a = self._make_solution("A", [a1])
        sol_b = self._make_solution("B", [a1])
        comp = metrics.compare_two_solutions(sol_a, sol_b)
        assert comp["is_distinct"] is False
        assert comp["changed_students_count"] == 0

    def test_all_students_moved(self) -> None:
        """Every student swaps project → changed_students_count = total."""
        sol_a = self._make_solution(
            "A",
            [
                models.Assignment(
                    student_id="S1", project_id="P1", preference_rank=1
                ),
                models.Assignment(
                    student_id="S2", project_id="P2", preference_rank=1
                ),
            ],
            indicators={
                "efficiency": {"mean_skill_fit": 0.5},
                "fairness": {"mean_rank": 1.0, "unranked_count": 0},
            },
        )
        sol_b = self._make_solution(
            "B",
            [
                models.Assignment(
                    student_id="S1", project_id="P2", preference_rank=2
                ),
                models.Assignment(
                    student_id="S2", project_id="P1", preference_rank=2
                ),
            ],
            indicators={
                "efficiency": {"mean_skill_fit": 0.7},
                "fairness": {"mean_rank": 2.0, "unranked_count": 0},
            },
        )
        comp = metrics.compare_two_solutions(sol_a, sol_b)
        assert comp["is_distinct"] is True
        assert comp["changed_students_count"] == 2

    def test_delta_metrics_present(self) -> None:
        """The delta_metrics sub-dict is always present in the result."""
        sol_a = self._make_solution("A", [])
        sol_b = self._make_solution("B", [])
        comp = metrics.compare_two_solutions(sol_a, sol_b)
        assert "delta_metrics" in comp
        assert "mean_skill_fit_delta" in comp["delta_metrics"]
        assert "mean_rank_delta" in comp["delta_metrics"]
        assert "gini_delta" in comp["delta_metrics"]

    def test_missing_indicators_treated_as_zero(self) -> None:
        """Solutions without stored indicators → deltas computed as 0.0."""
        sol_a = self._make_solution("A", [])
        sol_b = self._make_solution("B", [])
        comp = metrics.compare_two_solutions(sol_a, sol_b)
        assert comp["delta_mean_skill_fit"] == 0.0
        assert comp["delta_mean_rank"] == 0.0

    def test_rank_improved_and_worsened_counts(self) -> None:
        """Mixed rank changes are counted correctly."""
        sol_a = self._make_solution(
            "A",
            [
                models.Assignment(
                    student_id="S1", project_id="P1", preference_rank=3
                ),
                models.Assignment(
                    student_id="S2", project_id="P2", preference_rank=1
                ),
            ],
        )
        sol_b = self._make_solution(
            "B",
            [
                models.Assignment(
                    student_id="S1", project_id="P2", preference_rank=1
                ),  # improved
                models.Assignment(
                    student_id="S2", project_id="P3", preference_rank=4
                ),  # worsened
            ],
        )
        comp = metrics.compare_two_solutions(sol_a, sol_b)
        assert comp["rank_improved_count"] == 1
        assert comp["rank_worsened_count"] == 1

    def test_trade_off_summary_not_empty_when_distinct(self) -> None:
        """Trade-off summary has at least one statement for distinct solutions."""
        sol_a = self._make_solution(
            "A",
            [
                models.Assignment(
                    student_id="S1", project_id="P1", preference_rank=1
                )
            ],
            indicators={
                "efficiency": {"mean_skill_fit": 0.5},
                "fairness": {"mean_rank": 1.0, "unranked_count": 0},
            },
        )
        sol_b = self._make_solution(
            "B",
            [
                models.Assignment(
                    student_id="S1", project_id="P2", preference_rank=2
                )
            ],
            indicators={
                "efficiency": {"mean_skill_fit": 0.9},
                "fairness": {"mean_rank": 2.0, "unranked_count": 0},
            },
        )
        comp = metrics.compare_two_solutions(sol_a, sol_b)
        assert len(comp["trade_off_summary"]) > 0

    def test_unranked_count_delta_tracked(self) -> None:
        """Delta in unranked count is exposed in both top-level and delta_metrics."""
        sol_a = self._make_solution(
            "A",
            [],
            indicators={
                "efficiency": {"mean_skill_fit": 0.5},
                "fairness": {"mean_rank": 1.0, "unranked_count": 0},
            },
        )
        sol_b = self._make_solution(
            "B",
            [],
            indicators={
                "efficiency": {"mean_skill_fit": 0.5},
                "fairness": {"mean_rank": 1.0, "unranked_count": 2},
            },
        )
        comp = metrics.compare_two_solutions(sol_a, sol_b)
        assert comp["delta_unranked_count"] == 2
        assert comp["delta_metrics"]["delta_unranked_count"] == 2
