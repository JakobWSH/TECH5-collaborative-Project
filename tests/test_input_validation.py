"""Team B input validation tests extending the starter validation suite.

Each test pins one rule from the Week 1 formulation (docs/team_b_formulation.md
section 6) so that the solver only receives inputs its model can represent.
"""

import pathlib

import pytest

from app import create_app
from app.contract import contract
from app.domain import models
from app.domain import validation
from app.engine import solvers
from app.samples import demo_data


def _student(
    s_id: str,
    skills: dict[str, int] | None = None,
    prefs: list[str] | None = None,
) -> models.Student:
    """Builds a student ranking `prefs` in order."""
    return models.Student(
        id=s_id,
        display_name=s_id,
        skills=skills or {},
        preferences=[
            models.Preference(s_id, p_id, rank)
            for rank, p_id in enumerate(prefs or [], start=1)
        ],
    )


def test_non_positive_rank_rejected() -> None:
    """Ranks are 1-indexed; zero or negative ranks are rejected."""
    s1 = models.Student(
        id="S1",
        display_name="S1",
        preferences=[models.Preference("S1", "P1", 0)],
    )
    projects = [models.Project(id="P1", title="P1", max_capacity=1)]
    res = validation.validate_cohort([s1], projects)
    assert res.is_valid is False
    assert any("invalid rank 0" in err for err in res.errors)


def test_preference_owner_mismatch_rejected() -> None:
    """A preference must belong to the student that carries it."""
    s1 = models.Student(
        id="S1",
        display_name="S1",
        preferences=[models.Preference("S2", "P1", 1)],
    )
    projects = [models.Project(id="P1", title="P1", max_capacity=1)]
    res = validation.validate_cohort([s1], projects)
    assert res.is_valid is False
    assert any("belonging to student 'S2'" in err for err in res.errors)


def test_skill_level_bounds() -> None:
    """Negative levels are errors; levels above the scale are warnings."""
    projects = [models.Project(id="P1", title="P1", max_capacity=2)]
    students = [
        _student("S1", skills={"py": -1}, prefs=["P1"]),
        _student("S2", skills={"py": 7}, prefs=["P1"]),
    ]
    res = validation.validate_cohort(students, projects)
    assert res.is_valid is False
    assert any("negative level -1" in err for err in res.errors)
    assert any("level 7" in w and "S2" in w for w in res.warnings)


def test_requirement_integrity() -> None:
    """Requirement levels, duplicates and ownership are checked."""
    projects = [
        models.Project(
            id="P1",
            title="P1",
            max_capacity=2,
            requirements=[
                models.ProjectRequirement("P1", "py", minimum_level=0),
                models.ProjectRequirement("P1", "py", minimum_level=2),
                models.ProjectRequirement("P9", "sql", minimum_level=1),
            ],
        )
    ]
    res = validation.validate_cohort([_student("S1", prefs=["P1"])], projects)
    assert res.is_valid is False
    assert any("invalid level 0" in err for err in res.errors)
    assert any("'py' more than once" in err for err in res.errors)
    assert any("belonging to project 'P9'" in err for err in res.errors)


def test_repeated_identical_lock_is_not_contradictory() -> None:
    """The same lock entered twice is a warning, not a conflict."""
    projects = [models.Project(id="P1", title="P1", max_capacity=1)]
    fixed = [
        models.FixedAssignment("S1", "P1"),
        models.FixedAssignment("S1", "P1"),
    ]
    res = validation.validate_cohort(
        [_student("S1", prefs=["P1"])], projects, fixed_assignments=fixed
    )
    assert res.is_valid is True
    assert not any("Contradictory" in err for err in res.errors)
    assert any("more than once" in w for w in res.warnings)


def test_residual_minimum_after_locks() -> None:
    """Locks can starve other projects of their minimum headcount."""
    projects = [
        models.Project(id="P1", title="P1", min_capacity=0, max_capacity=2),
        models.Project(id="P2", title="P2", min_capacity=1, max_capacity=2),
    ]
    students = [
        _student("S1", prefs=["P1"]),
        _student("S2", prefs=["P1"]),
    ]
    fixed = [
        models.FixedAssignment("S1", "P1"),
        models.FixedAssignment("S2", "P1"),
    ]
    res = validation.validate_cohort(
        students, projects, fixed_assignments=fixed
    )
    assert res.is_feasible is False
    assert any("residual minimum capacity" in err for err in res.errors)


def test_unqualified_optional_project_may_stay_empty() -> None:
    """A min-0 project nobody qualifies for is a warning, not an error."""
    projects = [
        models.Project(
            id="P1",
            title="Kernel Dev",
            min_capacity=0,
            max_capacity=2,
            requirements=[
                models.ProjectRequirement(
                    "P1", "rust", minimum_level=4, is_mandatory=True
                )
            ],
        ),
        models.Project(id="P2", title="P2", min_capacity=0, max_capacity=2),
    ]
    res = validation.validate_cohort(
        [_student("S1", skills={"py": 3}, prefs=["P1", "P2"])], projects
    )
    assert res.is_valid is True
    assert res.is_feasible is True
    assert any("will stay empty" in w for w in res.warnings)

def test_unusable_project_capacity() -> None:
    """Checks that an unstaffable project is not counted as available capacity."""
    projects = [
        models.Project(
            id="P1",
            title="Kernel Dev",
            min_capacity=0,
            max_capacity=2,
            requirements=[
                models.ProjectRequirement(
                    "P1",
                    "rust",
                    minimum_level=4,
                    is_mandatory=True,
                )
            ],
        ),
        models.Project(
            id="P2",
            title="P2",
            min_capacity=0,
            max_capacity=1,
        ),
    ]

    students = [
        _student("S1", skills={"py": 3}, prefs=["P1", "P2"]),
        _student("S2", skills={"py": 3}, prefs=["P2", "P1"]),
    ]

    res = validation.validate_cohort(students, projects)

    assert res.is_feasible is False

def test_lock_forces_open_unqualified_project() -> None:
    """Locking a student into an unstaffable project is infeasible."""
    projects = [
        models.Project(
            id="P1",
            title="Kernel Dev",
            min_capacity=0,
            max_capacity=2,
            requirements=[
                models.ProjectRequirement(
                    "P1", "rust", minimum_level=4, is_mandatory=True
                )
            ],
        )
    ]
    res = validation.validate_cohort(
        [_student("S1", skills={"py": 3}, prefs=["P1"])],
        projects,
        fixed_assignments=[models.FixedAssignment("S1", "P1")],
    )
    assert res.is_feasible is False
    assert any("Mandatory requirement impossible" in e for e in res.errors)


def test_locks_fill_project_without_qualified_member() -> None:
    """Full lock set with no qualified member violates a mandatory skill."""
    projects = [
        models.Project(
            id="P1",
            title="Kernel Dev",
            min_capacity=1,
            max_capacity=1,
            requirements=[
                models.ProjectRequirement(
                    "P1", "rust", minimum_level=3, is_mandatory=True
                )
            ],
        ),
        models.Project(id="P2", title="P2", min_capacity=0, max_capacity=1),
    ]
    students = [
        _student("S1", skills={"py": 3}, prefs=["P1"]),
        _student("S2", skills={"rust": 4}, prefs=["P1"]),
    ]
    res = validation.validate_cohort(
        students,
        projects,
        fixed_assignments=[models.FixedAssignment("S1", "P1")],
    )
    assert res.is_feasible is False
    assert any("filled by fixed assignments" in e for e in res.errors)


@pytest.fixture(name="standard_request_kwargs")
def fixture_standard_request_kwargs(
    tmp_path: pathlib.Path,
) -> dict[str, object]:
    """Provides a valid standard scenario backed by a temporary database."""
    create_app({"TESTING": True, "DATABASE_PATH": tmp_path / "val.db"})
    scenario = demo_data.get_standard_scenario()
    return {
        "students": scenario["students"],
        "projects": scenario["projects"],
        "skills": scenario["skills"],
        "fixed_assignments": scenario["fixed_assignments"],
    }


@pytest.mark.parametrize("strategy_key", solvers.SUPPORTED_STRATEGY_KEYS)
def test_engine_accepts_supported_strategies(
    standard_request_kwargs: dict[str, object], strategy_key: str
) -> None:
    """Every dashboard strategy key passes request validation."""
    engine = solvers.AssignmentEngine()
    outcome = engine.validate_inputs(
        contract.RunRequest(
            strategy_key=strategy_key, **standard_request_kwargs
        )
    )
    assert outcome.is_valid, outcome.errors


def test_engine_rejects_unknown_strategy(
    standard_request_kwargs: dict[str, object],
) -> None:
    """Unknown strategy keys are rejected before any solve."""
    engine = solvers.AssignmentEngine()
    outcome = engine.validate_inputs(
        contract.RunRequest(strategy_key="RANDOM", **standard_request_kwargs)
    )
    assert outcome.is_valid is False
    assert any("Unknown strategy 'RANDOM'" in e for e in outcome.errors)


@pytest.mark.parametrize("max_alternatives", [0, -1, 11])
def test_engine_rejects_out_of_range_alternatives(
    standard_request_kwargs: dict[str, object], max_alternatives: int
) -> None:
    """Alternative counts outside [1, 10] are rejected."""
    engine = solvers.AssignmentEngine()
    outcome = engine.validate_inputs(
        contract.RunRequest(
            max_alternatives=max_alternatives, **standard_request_kwargs
        )
    )
    assert outcome.is_valid is False
    assert any("Requested alternatives" in e for e in outcome.errors)
