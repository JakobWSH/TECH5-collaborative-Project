"""Regression tests for completed Team A features; starter test files remain unchanged."""

import pathlib
from app import create_app
from app.persistence import repositories

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

