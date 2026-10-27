"""Tests for Component A (Visualization & Recommendation) web workflows."""

import pathlib

from app import create_app
from app.domain import models
from app.engine import metrics
from app.engine import recommendations
from app.persistence import repositories


def test_dashboard_loads(tmp_path: pathlib.Path) -> None:
    """Verifies dashboard overview page rendering."""
    db_file = tmp_path / "test_ui_dash.db"
    app = create_app({"TESTING": True, "DATABASE_PATH": db_file})
    client = app.test_client()

    dash_res = client.get("/")
    assert dash_res.status_code == 200
    assert b"TECH5" in dash_res.data


def test_role_switcher(tmp_path: pathlib.Path) -> None:
    """Verifies role switching in session."""
    db_file = tmp_path / "test_role.db"
    app = create_app({"TESTING": True, "DATABASE_PATH": db_file})
    client = app.test_client()

    res = client.post(
        "/set-role", data={"role": "STUDENT"}, follow_redirects=True
    )
    assert res.status_code == 200
    assert b"Switched role to Student Viewer" in res.data


def test_student_and_fixed_assignment_workflow(
    tmp_path: pathlib.Path,
) -> None:
    """Verifies student and fixed-assignment creation workflows."""
    db_file = tmp_path / "test_stud_fixed.db"
    app = create_app({"TESTING": True, "DATABASE_PATH": db_file})
    client = app.test_client()

    # Seed project P1 so student preference foreign key is valid
    repositories.ProjectRepository().save(
        models.Project(
            id="P1",
            title="FinTech Risk",
            min_capacity=1,
            max_capacity=2,
        )
    )

    # Create student
    res_stud = client.post(
        "/students/new",
        data={
            "id": "S1",
            "display_name": "Alice Chen",
            "preferences_text": "P1",
        },
        follow_redirects=True,
    )
    assert res_stud.status_code == 200
    assert b"Alice Chen" in res_stud.data

    # Create fixed assignment
    res_fixed = client.post(
        "/fixed-assignments/new",
        data={
            "student_id": "S1",
            "project_id": "P1",
            "status": "APPROVED",
            "reason": "Pre-matched",
        },
        follow_redirects=True,
    )
    assert res_fixed.status_code == 200
    assert b"Pre-matched" in res_fixed.data


def test_scenario_loading_and_optimization_trigger(
    tmp_path: pathlib.Path,
) -> None:
    """Verifies benchmark scenario loading, execution, and result views."""
    db_file = tmp_path / "test_scenario_run.db"
    app = create_app({"TESTING": True, "DATABASE_PATH": db_file})
    client = app.test_client()

    # Load standard benchmark
    load_res = client.post("/load-scenario/standard", follow_redirects=True)
    assert load_res.status_code == 200
    assert b"Standard Cohort" in load_res.data

    # Trigger optimization run (falls back to mock engine if solver unimplemented)
    run_res = client.post(
        "/runs/trigger",
        data={
            "primary_strategy": "PREFERENCE",
            "max_alternatives": 3,
        },
        follow_redirects=True,
    )
    assert run_res.status_code == 200
    assert b"Optimization run completed" in run_res.data

    runs = repositories.RunRepository().list_runs(limit=1)
    assert len(runs) == 1
    run = runs[0]
    assert len(run.solutions) >= 1

    # View solution detail
    sol_id = run.solutions[0].id
    sol_res = client.get(f"/solutions/{sol_id}")
    assert sol_res.status_code == 200
    assert b"Student-to-Project Allocations" in sol_res.data

    # View recommendations
    recs_res = client.get(f"/recommendations/{run.id}")
    assert recs_res.status_code == 200
    assert b"Transparent Decision Recommendations" in recs_res.data
    assert b"Calculated Evidence" in recs_res.data
    assert b"Policy Advice" in recs_res.data


def test_create_student_preference_validation(
    tmp_path: pathlib.Path,
) -> None:
    """Verifies preference validation when creating a student."""
    db_file = tmp_path / "test_stud_pref_val.db"
    app = create_app({"TESTING": True, "DATABASE_PATH": db_file})
    client = app.test_client()

    repositories.ProjectRepository().save(
        models.Project(
            id="P1",
            title="Project One",
            min_capacity=1,
            max_capacity=2,
        )
    )

    # 1. Invalid project preference should flash error and not crash
    res_invalid = client.post(
        "/students/new",
        data={
            "id": "S10",
            "display_name": "Test Student",
            "preferences_text": "P99, P100",
        },
        follow_redirects=True,
    )
    assert res_invalid.status_code == 200
    assert b"Invalid project ID(s) in preferences" in res_invalid.data

    # 2. Case-insensitive project preference should normalize and succeed
    res_valid = client.post(
        "/students/new",
        data={
            "id": "S10",
            "display_name": "Test Student",
            "preferences_text": "p1",
        },
        follow_redirects=True,
    )
    assert res_valid.status_code == 200
    assert b"created successfully" in res_valid.data

    saved = repositories.StudentRepository().get_by_id("S10")
    assert saved is not None
    assert len(saved.preferences) == 1
    assert saved.preferences[0].project_id == "P1"


def test_skills_crud_workflow(tmp_path: pathlib.Path) -> None:
    """Creating and deleting a skill updates both the UI and database."""
    db_file = tmp_path / "test_skill.db"
    app = create_app({"TESTING": True, "DATABASE_PATH": db_file})
    client = app.test_client()

    created = client.post(
        "/skills/new",
        data={"id": "py", "name": "Python", "description": "Python Programming"},
        follow_redirects=True,
    )
    assert created.status_code == 200
    assert b"created successfully" in created.data
    saved = repositories.SkillRepository().get_by_id("py")
    assert saved is not None
    assert saved.name == "Python"
    assert saved.description == "Python Programming"

    duplicate = client.post(
        "/skills/new", data={"id": "py", "name": "Duplicate"}, follow_redirects=True
    )
    assert duplicate.status_code == 200
    assert b"already exists" in duplicate.data
    assert repositories.SkillRepository().get_by_id("py").name == "Python"

    deleted = client.post("/skills/py/delete", follow_redirects=True)
    assert deleted.status_code == 200
    assert b"removed" in deleted.data
    assert repositories.SkillRepository().get_by_id("py") is None


def test_projects_crud_workflow(tmp_path: pathlib.Path) -> None:
    """Creating, updating, and deleting a project persist correct capacities."""
    db_file = tmp_path / "test_proj.db"
    app = create_app({"TESTING": True, "DATABASE_PATH": db_file})
    client = app.test_client()

    created = client.post(
        "/projects/new",
        data={
            "id": "P1",
            "title": "FinTech Risk",
            "description": "Risk analytics",
            "min_capacity": 1,
            "max_capacity": 2,
        },
        follow_redirects=True,
    )
    assert created.status_code == 200
    assert b"created successfully" in created.data
    saved = repositories.ProjectRepository().get_by_id("P1")
    assert saved is not None
    assert saved.title == "FinTech Risk"
    assert saved.min_capacity == 1
    assert saved.max_capacity == 2

    updated = client.post(
        "/projects/P1/edit",
        data={
            "title": "Updated Risk Project",
            "description": "Updated description",
            "min_capacity": 0,
            "max_capacity": 3,
        },
        follow_redirects=True,
    )
    assert updated.status_code == 200
    assert b"updated" in updated.data
    saved = repositories.ProjectRepository().get_by_id("P1")
    assert saved is not None
    assert saved.title == "Updated Risk Project"
    assert saved.min_capacity == 0
    assert saved.max_capacity == 3

    deleted = client.post("/projects/P1/delete", follow_redirects=True)
    assert deleted.status_code == 200
    assert b"removed" in deleted.data
    assert repositories.ProjectRepository().get_by_id("P1") is None


def test_compare_solutions_view(tmp_path: pathlib.Path) -> None:
    """A populated comparison page renders two real engine alternatives."""
    db_file = tmp_path / "test_comp.db"
    app = create_app({"TESTING": True, "DATABASE_PATH": db_file})
    client = app.test_client()

    loaded = client.post("/load-scenario/standard", follow_redirects=True)
    assert loaded.status_code == 200
    triggered = client.post(
        "/runs/trigger",
        data={"primary_strategy": "PREFERENCE", "max_alternatives": 3},
        follow_redirects=True,
    )
    assert triggered.status_code == 200
    assert b"Optimization run completed" in triggered.data

    runs = repositories.RunRepository().list_runs(limit=1)
    assert len(runs) == 1
    assert len(runs[0].solutions) >= 2
    first, second = runs[0].solutions[:2]

    result = client.get(f"/compare?sol1={first.id}&sol2={second.id}")
    assert result.status_code == 200
    assert b"Side-by-Side Solution Comparison" in result.data
    assert b"Trade-off Findings" in result.data
    assert b"Detailed Allocation Shifts" in result.data
    assert b"Team A Starter Carcass" not in result.data


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

