"""The standalone assignment engine must initialize its own SQLite schema."""

from app.domain import models
from app.engine import solvers
from app.persistence import database, repositories


def test_execute_run_initializes_custom_database_without_flask(tmp_path) -> None:
    db = database.DatabaseManager(tmp_path / "standalone.db")
    engine = solvers.AssignmentEngine(run_repo=repositories.RunRepository(db))

    # Isolate the persistence lifecycle from the PuLP solver: this regression
    # specifically checks that execute_run() initializes the right database.
    engine.strategies["PREFERENCE"].solve = lambda students, projects, fixed_assignments, excluded_solutions: (
        "Optimal",
        [
            models.Assignment(
                student_id="S1", project_id="P1", preference_rank=1,
                skill_fit_score=1.0,
            )
        ],
        1.0,
        {"solver_status": "Optimal"},
    )
    student = models.Student(
        id="S1", display_name="Student 1",
        preferences=[models.Preference("S1", "P1", 1)],
    )
    project = models.Project(id="P1", title="Project 1", min_capacity=1, max_capacity=1)

    run = engine.run_assignment(
        students=[student], projects=[project], max_alternatives=1,
    )
    assert run.status == "COMPLETED"
    assert db.execute_query("SELECT id FROM skills") == []
    assert db.execute_query("SELECT id FROM students")[0]["id"] == "S1"
    assert engine.get_run(run.id) is not None
