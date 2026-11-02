"""Completed-engine regression tests kept separate from instructor starter tests."""

import pathlib
import pytest
from app import create_app
from app.contract import contract, mocks
from app.domain import models
from app.engine import solvers
from app.samples import demo_data

def test_contract_execute_and_retrieval(tmp_path: pathlib.Path) -> None:
    """Tests execute_run, get_run, get_solution, and list_runs via contract."""
    db_file = tmp_path / "test_exec_contract.db"
    create_app({"TESTING": True, "DATABASE_PATH": db_file})

    scenario = demo_data.get_standard_scenario()
    request = contract.RunRequest(
        students=scenario["students"],
        projects=scenario["projects"],
        skills=scenario["skills"],
        fixed_assignments=scenario["fixed_assignments"],
        strategy_key="PREFERENCE",
        max_alternatives=2,
    )

    # 1. Week 2 real engine fulfills the contract and persists valid runs.
    engine: contract.AssignmentEngineContract = solvers.AssignmentEngine()
    real_run = engine.execute_run(request)
    assert real_run.status == "COMPLETED"
    assert engine.get_run(real_run.id) is not None
    assert all(sol.indicators["feasibility"]["is_feasible"] for sol in real_run.solutions)

    # 2. MockAssignmentEngine still fulfills contract for demonstrations
    mock_engine: contract.AssignmentEngineContract = (
        mocks.MockAssignmentEngine()
    )
    run = mock_engine.execute_run(request)
    assert run.status == "COMPLETED"
    assert len(run.solutions) >= 1

    # Verify retrieval of run
    fetched_run = mock_engine.get_run(run.id)
    assert fetched_run is not None
    assert fetched_run.id == run.id
    assert len(fetched_run.solutions) == len(run.solutions)

    # Verify list_runs
    runs_list = mock_engine.list_runs(limit=10)
    assert any(r.id == run.id for r in runs_list)

    # Verify get_solution
    sol_id = run.solutions[0].id
    solution = mock_engine.get_solution(sol_id)
    assert solution is not None
    assert solution.id == sol_id
    assert len(solution.assignments) == len(scenario["students"])

def test_contract_compare_solutions(tmp_path: pathlib.Path) -> None:
    """Tests compare_solutions via contract."""
    db_file = tmp_path / "test_comp_contract.db"
    create_app({"TESTING": True, "DATABASE_PATH": db_file})

    scenario = demo_data.get_standard_scenario()
    request = contract.RunRequest(
        students=scenario["students"],
        projects=scenario["projects"],
        skills=scenario["skills"],
        fixed_assignments=scenario["fixed_assignments"],
        strategy_key="PREFERENCE",
        max_alternatives=2,
    )

    mock_engine: contract.AssignmentEngineContract = (
        mocks.MockAssignmentEngine()
    )
    run = mock_engine.execute_run(request)
    assert len(run.solutions) >= 2

    sol_a = run.solutions[0]
    sol_b = run.solutions[1]

    # Mock engine performs valid comparison
    comparison = mock_engine.compare_solutions(sol_a.id, sol_b.id)
    assert isinstance(comparison, models.RunComparison)
    assert comparison.solution_a_id == sol_a.id
    assert comparison.solution_b_id == sol_b.id
    assert isinstance(comparison.changed_assignments, list)
    assert isinstance(comparison.delta_metrics, dict)

    # Test non-existent solution raises KeyError
    with pytest.raises(KeyError):
        mock_engine.compare_solutions(sol_a.id, "non_existent_id")

    # Real engine reads the same persisted solutions and compares indicators.
    engine: contract.AssignmentEngineContract = solvers.AssignmentEngine()
    real_comparison = engine.compare_solutions(sol_a.id, sol_b.id)
    assert isinstance(real_comparison, models.RunComparison)
    assert real_comparison.solution_a_id == sol_a.id
    assert real_comparison.solution_b_id == sol_b.id

def test_assignment_engine_initialization() -> None:
    """Verifies that AssignmentEngine initializes cleanly with empty strategies."""
    engine = solvers.AssignmentEngine()
    assert isinstance(engine, contract.AssignmentEngineContract)
    assert isinstance(engine.strategies, dict)
    assert set(engine.strategies) == {"PREFERENCE", "SKILL_FIT", "BALANCED"}

def test_assignment_engine_executes_real_solver() -> None:
    """Week 2 replaces the deliberately unimplemented starter engine."""
    engine = solvers.AssignmentEngine()
    scenario = demo_data.get_standard_scenario()
    run = engine.run_assignment(
        students=scenario["students"], projects=scenario["projects"],
        skills=scenario["skills"], fixed_assignments=scenario["fixed_assignments"],
        max_alternatives=2,
    )
    assert run.status == "COMPLETED"
    assert len(run.solutions) >= 1
    assert all(sol.indicators["feasibility"]["is_feasible"] for sol in run.solutions)

def test_distinct_alternatives_generation() -> None:
    """Verifies AssignmentEngine produces distinct alternatives."""
    benchmark = demo_data.get_standard_scenario()
    engine = solvers.AssignmentEngine()

    run = engine.run_assignment(
        students=benchmark["students"],
        projects=benchmark["projects"],
        skills=benchmark["skills"],
        max_alternatives=3,
    )

    assert run.status == "COMPLETED"
    assert len(run.solutions) >= 2

    # Check distinctness: verify that each pair of solutions differs
    for i in range(len(run.solutions)):
        for j in range(i + 1, len(run.solutions)):
            pairs_i = {
                (a.student_id, a.project_id)
                for a in run.solutions[i].assignments
            }
            pairs_j = {
                (a.student_id, a.project_id)
                for a in run.solutions[j].assignments
            }
            assert (
                pairs_i != pairs_j
            ), f"Solution {i+1} and {j+1} are duplicate allocations!"

