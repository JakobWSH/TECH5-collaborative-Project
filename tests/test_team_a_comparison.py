"""Team A (Group 12) tests for the multi-solution comparison view and
trade-off recommendations.

Kept in a separate file so the supplied starter tests stay unchanged.
"""

import pathlib

from app import create_app
from app.domain import models
from app.persistence import repositories
from app.engine import metrics
from app.engine import recommendations


def test_multi_solution_comparison_matrix_and_tradeoff_recommendations(
    tmp_path: pathlib.Path,
) -> None:
    """Verifies multi-solution matrix and recommendation trade-off logic."""
    db_file = tmp_path / "test_multi_comp.db"
    app = create_app({"TESTING": True, "DATABASE_PATH": db_file})
    client = app.test_client()

    # Seed benchmark cohort and trigger 3-alternative run
    client.post("/load-scenario/standard", follow_redirects=True)
    trigger_res = client.post(
        "/runs/trigger",
        data={"primary_strategy": "PREFERENCE", "max_alternatives": 3},
        follow_redirects=True,
    )
    assert trigger_res.status_code == 200

    runs = repositories.RunRepository().list_runs(limit=1)
    assert len(runs) == 1
    run = runs[0]
    assert len(run.solutions) == 3

    # 1. Visiting /compare without query params auto-selects latest solutions
    auto_res = client.get("/compare")
    assert auto_res.status_code == 200
    assert b"Side-by-Side Solution Comparison" in auto_res.data
    assert b"Cohort Solutions Comparison Matrix" in auto_res.data
    assert b"Alternative #1" in auto_res.data
    assert b"Alternative #2" in auto_res.data
    assert b"Alternative #3" in auto_res.data

    # 2. Verify all four Section 6 questions are directly answered in the UI
    assert b"What Improves in Solution B?" in auto_res.data
    assert b"What Becomes Worse in Solution B?" in auto_res.data
    assert b"Which Alternative Would We Recommend, and Why?" in auto_res.data
    assert b"Detailed Allocation Shifts" in auto_res.data

    # 3. Verify transparent recommendation evidence and advice
    assert b"Calculated Evidence" in auto_res.data
    assert b"Policy Advice" in auto_res.data

    # 4. Verify run_detail contains the link to compare all alternatives
    run_detail_res = client.get(f"/runs/{run.id}")
    assert run_detail_res.status_code == 200
    assert b"Compare All Alternatives" in run_detail_res.data


def test_single_solution_honest_reporting(tmp_path: pathlib.Path) -> None:
    """If only 1 solution exists, report honestly without manufacturing."""
    db_file = tmp_path / "test_single_sol.db"
    app = create_app({"TESTING": True, "DATABASE_PATH": db_file})
    client = app.test_client()

    client.post("/load-scenario/standard", follow_redirects=True)
    client.post(
        "/runs/trigger",
        data={"primary_strategy": "PREFERENCE", "max_alternatives": 1},
        follow_redirects=True,
    )

    runs = repositories.RunRepository().list_runs(limit=1)
    assert len(runs) == 1
    assert len(runs[0].solutions) == 1
    sol = runs[0].solutions[0]

    # Load comparison for the single solution
    res = client.get(f"/compare?sol1={sol.id}&run_id={runs[0].id}")
    assert res.status_code == 200
    assert b"Single Feasible Solution" in res.data
    assert b"no artificial alternatives have been manufactured" in res.data


def test_explain_tradeoff_recommendation_unit() -> None:
    """Verifies unit logic of explain_tradeoff with evidence and advice."""
    # Build two mock solutions with clear trade-offs
    sol_pref = models.Solution(
        id="SOL_PREF",
        run_id="RUN_1",
        alternative_number=1,
        strategy_name="PREFERENCE",
        objective_value=9.5,
        assignments=[
            models.Assignment(
                student_id="S1",
                project_id="P1",
                preference_rank=1,
                skill_fit_score=0.6,
            ),
            models.Assignment(
                student_id="S2",
                project_id="P2",
                preference_rank=2,
                skill_fit_score=0.7,
            ),
        ],
        indicators={
            "efficiency": {
                "mean_skill_fit": 0.65,
                "unmet_soft_requirements_count": 2,
            },
            "fairness": {
                "mean_rank": 1.5,
                "worst_rank": 2,
                "unranked_count": 0,
                "rank_gini": 0.1667,
                "rank_variance": 0.25,
            },
        },
    )

    sol_skill = models.Solution(
        id="SOL_SKILL",
        run_id="RUN_1",
        alternative_number=2,
        strategy_name="SKILL_FIT",
        objective_value=8.0,
        assignments=[
            models.Assignment(
                student_id="S1",
                project_id="P2",
                preference_rank=3,
                skill_fit_score=0.95,
            ),
            models.Assignment(
                student_id="S2",
                project_id="P1",
                preference_rank=1,
                skill_fit_score=0.90,
            ),
        ],
        indicators={
            "efficiency": {
                "mean_skill_fit": 0.925,
                "unmet_soft_requirements_count": 0,
            },
            "fairness": {
                "mean_rank": 2.0,
                "worst_rank": 3,
                "unranked_count": 0,
                "rank_gini": 0.25,
                "rank_variance": 1.0,
            },
        },
    )

    comparison_dict = metrics.compare_two_solutions(sol_pref, sol_skill)
    comparison = models.RunComparison.from_dict(comparison_dict)

    tradeoff = recommendations.explain_tradeoff(sol_pref, sol_skill, comparison)

    # Solution B improves skill fit
    assert any("skill fit increases" in s for s in tradeoff.what_improves)
    # Solution B worsens mean rank
    assert any("rank worsens" in s for s in tradeoff.what_becomes_worse)
    # Student priority favors Alt 1, Skill priority favors Alt 2
    assert tradeoff.recommended_for_student_satisfaction == 1
    assert tradeoff.recommended_for_skill_delivery == 2
    rec_choice = tradeoff.recommended_choice
    assert "Alternative #1 for Student Satisfaction" in rec_choice
    assert "Alternative #2 for Technical Skill Delivery" in rec_choice
    assert len(tradeoff.evidence) >= 2
    assert len(tradeoff.advice) > 0

    # Serialization test
    d = tradeoff.to_dict()
    assert d["recommended_choice"] == tradeoff.recommended_choice
    assert isinstance(d["what_improves"], list)
    assert isinstance(d["what_becomes_worse"], list)

    # Identical solutions test
    identical_comp_dict = metrics.compare_two_solutions(sol_pref, sol_pref)
    identical_comp = models.RunComparison.from_dict(identical_comp_dict)
    identical_tradeoff = recommendations.explain_tradeoff(
        sol_pref, sol_pref, identical_comp
    )
    assert "Identical" in identical_tradeoff.recommended_choice