"""Independent targeted tests for the recovered Week 2 metrics work."""

import pytest
from app.domain import models
from app.engine import metrics


def test_duplicate_student_allocation_is_not_feasible():
    students = [models.Student(id="S1", display_name="Student 1")]
    projects = [models.Project(id="P1", title="P1", max_capacity=2)]
    assignments = [models.Assignment(student_id="S1", project_id="P1")] * 2
    result = metrics.compute_solution_indicators(students, projects, assignments)
    assert result["feasibility"]["is_feasible"] is False
    assert any("Duplicate" in error for error in result["feasibility"]["violations"])


def test_unknown_project_allocation_is_not_feasible():
    students = [models.Student(id="S1", display_name="Student 1")]
    projects = [models.Project(id="P1", title="P1", max_capacity=2)]
    result = metrics.compute_solution_indicators(
        students, projects, [models.Assignment(student_id="S1", project_id="OTHER")]
    )
    assert not result["feasibility"]["is_feasible"]


def test_missing_mandatory_skill_is_not_feasible():
    students = [models.Student(id="S1", display_name="Student 1", skills={})]
    projects = [models.Project(id="P1", title="P1", max_capacity=1,
                               requirements=[models.ProjectRequirement("P1", "python", 3, True)])]
    result = metrics.compute_solution_indicators(
        students, projects, [models.Assignment(student_id="S1", project_id="P1")]
    )
    assert not result["feasibility"]["is_feasible"]
    assert any("Mandatory" in error for error in result["feasibility"]["violations"])


def test_soft_requirement_count_excludes_mandatory():
    students = [models.Student(id="S1", display_name="S1", skills={"py": 3})]
    projects = [models.Project(id="P1", title="P1", max_capacity=1,
                    requirements=[models.ProjectRequirement("P1", "py", 2, True),
                                  models.ProjectRequirement("P1", "sql", 3, False)])]
    assignments = [models.Assignment(student_id="S1", project_id="P1", unmet_requirements=["sql"])]
    result = metrics.compute_solution_indicators(students, projects, assignments)
    assert result["feasibility"]["is_feasible"] is True
    assert result["efficiency"]["unmet_soft_requirements_count"] == 1


def test_comparison_treats_unranked_to_ranked_as_improvement():
    first = models.Solution(id="A", run_id="r", alternative_number=1, strategy_name="PREFERENCE",
                            assignments=[models.Assignment("S1", "P1", preference_rank=None)])
    second = models.Solution(id="B", run_id="r", alternative_number=2, strategy_name="SKILL_FIT",
                             assignments=[models.Assignment("S1", "P2", preference_rank=2)])
    result = metrics.compare_two_solutions(first, second)
    assert result["rank_improved_count"] == 1
    assert result["rank_worsened_count"] == 0


def test_gini_rejects_negative_numbers():
    with pytest.raises(ValueError):
        metrics.calculate_gini([1.0, -2.0])


def test_comparison_supplies_project_ids_and_numeric_rank_delta():
    first = models.Solution(
        id="A", run_id="r", alternative_number=1, strategy_name="PREFERENCE",
        assignments=[models.Assignment("S1", "P1", preference_rank=3)],
    )
    second = models.Solution(
        id="B", run_id="r", alternative_number=2, strategy_name="SKILL_FIT",
        assignments=[models.Assignment("S1", "P2", preference_rank=1)],
    )
    changed = metrics.compare_two_solutions(first, second)["changed_assignments"][0]
    assert changed["project_a_id"] == "P1"
    assert changed["project_b_id"] == "P2"
    assert changed["rank_delta"] == -2


def test_comparison_uses_none_rank_delta_for_unranked_change():
    first = models.Solution(
        id="A", run_id="r", alternative_number=1, strategy_name="PREFERENCE",
        assignments=[models.Assignment("S1", "P1", preference_rank=None)],
    )
    second = models.Solution(
        id="B", run_id="r", alternative_number=2, strategy_name="SKILL_FIT",
        assignments=[models.Assignment("S1", "P2", preference_rank=1)],
    )
    result = metrics.compare_two_solutions(first, second)
    assert result["changed_assignments"][0]["rank_delta"] is None
    assert result["rank_improved_count"] == 1
