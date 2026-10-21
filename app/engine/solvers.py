"""Mathematical optimization solvers and Strategy Pattern skeleton for TECH5.

In compliance with Section 5 and Section 8 of the TECH5 specification,
Team B is responsible for proposing and implementing an approved assignment
method (e.g. Integer Linear Programming, heuristic search, or stable matching).

This module defines the abstract strategy base class and the AssignmentEngine
that implements AssignmentEngineContract.
"""

import abc
import logging
from typing import Any
import uuid
import time
import dataclasses
import sqlite3

from app.contract import contract
from app.domain import models
from app.domain import validation
from app.engine import metrics
from app.persistence import repositories

# Strategy keys offered by the dashboard (Component A) to the engine.
SUPPORTED_STRATEGY_KEYS = ("PREFERENCE", "SKILL_FIT", "BALANCED")
# Upper bound on requested alternatives, keeping the cut loop small.
MAX_ALTERNATIVES_LIMIT = 10


class AssignmentStrategy(abc.ABC):
    """Abstract Base Class for student-to-project allocation strategies.

    Team B should derive concrete strategy subclasses implementing specific
    objective functions (e.g. preference satisfaction, skill fit, balanced).
    """

    def __init__(self, name: str, description: str) -> None:
        """Initializes the strategy with descriptive metadata.

        Args:
            name: Machine-readable identifier for the strategy.
            description: Human-readable explanation of the objective function.
        """
        self.name = name
        self.description = description

    @abc.abstractmethod
    def calculate_cost_or_utility(
        self,
        student: models.Student,
        project: models.Project,
        max_preferences: int,
    ) -> float:
        """Computes objective utility or cost weight for assigning student to project.

        Args:
            student: The candidate student.
            project: The target semester project.
            max_preferences: Maximum number of preferences ranked in cohort.

        Returns:
            Numerical weight reflecting desirability in optimization objective.
        """

    def solve(
        self,
        students: list[models.Student],
        projects: list[models.Project],
        fixed_assignments: list[models.FixedAssignment] | None = None,
        excluded_solutions: list[list[tuple[str, str]]] | None = None,
    ) -> tuple[str, list[models.Assignment], float | None, dict[str, Any]]:
        """Solve the integer program with CBC; excluded allocations use no-good cuts.

        The team-level interpretation of mandatory skills is PROVISIONAL until
        the instructor confirms it. It is isolated in the marked constraint.
        """
        import pulp  # Installed through requirements.txt on the student's Mac.

        started = time.monotonic()
        problem = pulp.LpProblem("TECH5_Assignment", pulp.LpMaximize)
        student_ids = [s.id for s in students]
        project_ids = [p.id for p in projects]
        by_project = {p.id: p for p in projects}
        assignment = {
            (sid, pid): pulp.LpVariable(f"x_{i}_{j}", cat="Binary")
            for i, sid in enumerate(student_ids)
            for j, pid in enumerate(project_ids)
        }
        # Exactly one project per student.
        for sid in student_ids:
            problem += pulp.lpSum(assignment[sid, p] for p in project_ids) == 1
        # Lower/upper project capacity, even when minimum is zero.
        for p in projects:
            headcount = pulp.lpSum(assignment[sid, p.id] for sid in student_ids)
            problem += headcount >= p.min_capacity
            problem += headcount <= p.max_capacity
            # PROVISIONAL mandatory-skill interpretation: if staffed, at least
            # one student on the project satisfies EACH mandatory requirement.
            for req in p.requirements:
                if not req.is_mandatory:
                    continue
                qualified = [
                    s.id for s in students
                    if s.get_skill_level(req.skill_id) >= req.minimum_level
                ]
                problem += (
                    p.max_capacity * pulp.lpSum(assignment[sid, p.id] for sid in qualified)
                    >= headcount
                )
        for lock in fixed_assignments or []:
            problem += assignment[lock.student_id, lock.project_id] == 1
        # No-good cuts exclude exact earlier assignments, NOT guarantee Pareto optimality.
        for previous in excluded_solutions or []:
            problem += pulp.lpSum(assignment[s, p] for s, p in previous) <= len(students) - 1

        rank_limit = max((pr.rank for s in students for pr in s.preferences), default=0)
        # The secondary weight is too small to outweigh a discrete preference
        # step in preference-first runs (for SKILL_FIT it is a soft tie-breaker).
        epsilon = 1.0 / (2 * len(students) * max(rank_limit, 1))
        def utility(s: models.Student, p: models.Project) -> float:
            primary = self.calculate_cost_or_utility(s, p, rank_limit)
            if self.name == "PREFERENCE":
                return primary + epsilon * _skill_score(s, p)
            if self.name == "SKILL_FIT":
                return primary + epsilon * _preference_score(s, p, rank_limit)
            return primary
        objective = pulp.lpSum(
            utility(s, p) * assignment[s.id, p.id]
            for s in students for p in projects
        )
        if self.name == "BALANCED":
            worst = pulp.LpVariable("worst_rank", lowBound=0, cat="Integer")
            for s in students:
                for p in projects:
                    rank = s.get_preference_rank(p.id) or (rank_limit + 1)
                    problem += worst >= rank * assignment[s.id, p.id]
            objective -= (1.0 / max(rank_limit + 1, 1)) * worst
        problem += objective

        try:
            problem.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=30))
        except Exception as exc:
            return "ERROR", [], None, {"message": str(exc), "solve_time_seconds": time.monotonic() - started}
        status = pulp.LpStatus[problem.status]
        info = {
            "solver_status": status,
            "solve_time_seconds": round(time.monotonic() - started, 4),
            "constraints_count": len(problem.constraints),
            "variables_count": len(problem.variables()),
        }
        # Only return proven optimal allocations. A time limit without an
        # optimality certificate is not the same as mathematical infeasibility.
        if status != "Optimal":
            return status, [], None, info
        fixed_pairs = {(fa.student_id, fa.project_id) for fa in fixed_assignments or []}
        allocations: list[models.Assignment] = []
        for student in students:
            selected = [p for p in projects if pulp.value(assignment[student.id, p.id]) > 0.5]
            if len(selected) != 1:
                return "ERROR", [], None, {**info, "message": "Solver returned incomplete allocation."}
            project = selected[0]
            fit, unmet = metrics.calculate_assignment_skill_fit(student, project)
            allocations.append(
                models.Assignment(
                    student_id=student.id,
                    project_id=project.id,
                    is_fixed=(student.id, project.id) in fixed_pairs,
                    preference_rank=student.get_preference_rank(project.id),
                    skill_fit_score=fit,
                    unmet_requirements=unmet,
                )
            )
        return status, allocations, float(pulp.value(problem.objective) or 0.0), info


def _preference_score(student: models.Student, project: models.Project, max_preferences: int) -> float:
    rank = student.get_preference_rank(project.id)
    if rank is None or max_preferences < 1:
        return 0.0
    return max(0.0, (max_preferences + 1 - rank) / max_preferences)


def _skill_score(student: models.Student, project: models.Project) -> float:
    fit, _ = metrics.calculate_assignment_skill_fit(student, project)
    return fit


class PreferenceOrientedSolver(AssignmentStrategy):
    def __init__(self) -> None:
        super().__init__("PREFERENCE", "Prioritize student preference rankings")

    def calculate_cost_or_utility(self, student: models.Student, project: models.Project, max_preferences: int) -> float:
        return _preference_score(student, project, max_preferences)


class SkillFitOrientedSolver(AssignmentStrategy):
    def __init__(self) -> None:
        super().__init__("SKILL_FIT", "Prioritize project skill alignment")

    def calculate_cost_or_utility(self, student: models.Student, project: models.Project, max_preferences: int) -> float:
        return _skill_score(student, project)


class BalancedTradeoffSolver(AssignmentStrategy):
    def __init__(self) -> None:
        super().__init__("BALANCED", "Balance preferences, skills and worst rank")

    def calculate_cost_or_utility(self, student: models.Student, project: models.Project, max_preferences: int) -> float:
        return 0.5 * _preference_score(student, project, max_preferences) + 0.5 * _skill_score(student, project)


class AssignmentEngine(contract.AssignmentEngineContract):
    """Main Assignment Engine orchestrating validation, execution, and persistence.

    Implements the internal component contract (AssignmentEngineContract)
    connecting Component B to Component A.
    """

    def __init__(
        self, run_repo: repositories.RunRepository | None = None
    ) -> None:
        """Initializes the AssignmentEngine with persistence repositories.

        Args:
            run_repo: Optional repository for persisting runs and solutions.
        """
        self.run_repo = (
            run_repo if run_repo is not None else repositories.RunRepository()
        )
        self.strategies: dict[str, AssignmentStrategy] = {
            "PREFERENCE": PreferenceOrientedSolver(),
            "SKILL_FIT": SkillFitOrientedSolver(),
            "BALANCED": BalancedTradeoffSolver(),
        }

    def validate_inputs(
        self, request: contract.RunRequest
    ) -> contract.ValidationOutcome:
        """Validates cohort and constraints before attempting optimization.

        Args:
            request: The run request containing students, projects, etc.

        Returns:
            ValidationOutcome with validity, feasibility, errors, and warnings.
        """
        val_result = validation.validate_cohort(
            students=request.students,
            projects=request.projects,
            skills=request.skills,
            fixed_assignments=request.fixed_assignments,
        )
        errors = list(val_result.errors)
        if request.strategy_key not in SUPPORTED_STRATEGY_KEYS:
            errors.append(
                f"Unknown strategy '{request.strategy_key}'; expected one "
                f"of {', '.join(SUPPORTED_STRATEGY_KEYS)}."
            )
        if not 1 <= request.max_alternatives <= MAX_ALTERNATIVES_LIMIT:
            errors.append(
                f"Requested alternatives ({request.max_alternatives}) must "
                f"be between 1 and {MAX_ALTERNATIVES_LIMIT}."
            )
        return contract.ValidationOutcome(
            is_valid=not errors,
            is_feasible=val_result.is_feasible,
            errors=errors,
            warnings=list(val_result.warnings),
            infeasibility_reasons=list(val_result.infeasibility_reasons),
        )

    def execute_run(self, request: contract.RunRequest) -> models.AssignmentRun:
        """Validate, solve for alternatives, compute indicators and persist run.

        Implementation is provisional pending instructor approval of ILP/CBC
        and the interpretation of mandatory skills.
        """
        # Direct engine use (e.g., unit tests) does not call Flask's create_app().
        # Initialize the same database used by this engine before persisting data.
        db = self.run_repo.db
        db.initialize_schema()

        run = models.AssignmentRun(
            id=str(uuid.uuid4()),
            configuration={
                "primary_strategy": request.strategy_key,
                "max_alternatives": request.max_alternatives,
                "notes": request.notes,
                "engine": "ILP_CBC_PROVISIONAL",
            },
        )
        outcome = self.validate_inputs(request)
        if not outcome.is_feasible:
            run.status = contract.RunStatus.INFEASIBLE.value
            run.diagnostics = {"solver_status": "PRECHECK_INFEASIBLE", "reasons": outcome.infeasibility_reasons}
            self.run_repo.save_run(run)
            return run
        if not outcome.is_valid:
            run.status = contract.RunStatus.INVALID_INPUT.value
            run.diagnostics = {"solver_status": "INVALID_INPUT", "errors": outcome.errors}
            self.run_repo.save_run(run)
            return run

        # Database FK order: skills -> projects -> students -> locks -> runs.
        # An omitted catalog should not cause FK errors when skills are present
        # in student or project input. Add unnamed catalog entries as needed.
        catalog = {sk.id: sk for sk in request.skills or []}
        for student in request.students:
            for skill_id in student.skills:
                catalog.setdefault(skill_id, models.Skill(id=skill_id, name=f"Skill: {skill_id}"))
        for project in request.projects:
            for req in project.requirements:
                catalog.setdefault(req.skill_id, models.Skill(id=req.skill_id, name=f"Skill: {req.skill_id}"))
        try:
            for sk in catalog.values():
                repositories.SkillRepository(db).save(sk)
            for project in request.projects:
                repositories.ProjectRepository(db).save(project)
            for student in request.students:
                # A level of zero means "not possessed" in the domain model;
                # omit it from student_skills because SQLite requires level>=1.
                stored = dataclasses.replace(
                    student, skills={k: v for k, v in student.skills.items() if v > 0}
                )
                repositories.StudentRepository(db).save(stored)
            for fa in {
                (f.student_id, f.project_id): f
                for f in request.fixed_assignments or []
            }.values():
                repositories.FixedAssignmentRepository(db).save(fa)
        except sqlite3.IntegrityError as exc:
            run.status = contract.RunStatus.INVALID_INPUT.value
            run.diagnostics = {"solver_status": "PERSISTENCE_INPUT_ERROR", "errors": [str(exc)]}
            self.run_repo.save_run(run)
            return run

        sequence = [request.strategy_key] + [
            key for key in SUPPORTED_STRATEGY_KEYS if key != request.strategy_key
        ]
        earlier: list[list[tuple[str, str]]] = []
        for index in range(request.max_alternatives):
            key = sequence[index % len(sequence)]
            strategy = self.strategies[key]
            try:
                status, assignments, value, diagnostic = strategy.solve(
                    request.students, request.projects, request.fixed_assignments, earlier
                )
            except ImportError as exc:
                run.status = contract.RunStatus.FAILED.value
                run.diagnostics = {"solver_status": "DEPENDENCY_MISSING", "error": str(exc)}
                break
            except Exception as exc:
                logging.exception("Team B solver crashed")
                run.status = contract.RunStatus.FAILED.value
                run.diagnostics = {"solver_status": "ERROR", "error": str(exc)}
                break
            if status == "Infeasible":
                # If no solution, whole run infeasible; otherwise there simply
                # aren't any more distinct feasible alternatives.
                if not run.solutions:
                    run.status = contract.RunStatus.INFEASIBLE.value
                    run.diagnostics = {"solver_status": status, "reasons": ["The ILP has no feasible allocation."], **diagnostic}
                break
            if status != "Optimal":
                run.status = contract.RunStatus.FAILED.value
                run.diagnostics = {"solver_status": status, **diagnostic}
                break
            indicators = metrics.compute_solution_indicators(
                request.students, request.projects, assignments, request.fixed_assignments
            )
            if not indicators["feasibility"]["is_feasible"]:
                run.status = contract.RunStatus.FAILED.value
                run.diagnostics = {"solver_status": "INVALID_SOLUTION", "violations": indicators["feasibility"]["violations"]}
                break
            run.solutions.append(
                models.Solution(
                    id=str(uuid.uuid4()), run_id=run.id,
                    alternative_number=len(run.solutions) + 1,
                    strategy_name=key, objective_value=value,
                    assignments=assignments, indicators=indicators,
                    diagnostics=diagnostic,
                )
            )
            earlier.append([(a.student_id, a.project_id) for a in assignments])

        if run.solutions and run.status == "PENDING":
            run.status = contract.RunStatus.COMPLETED.value
        run.diagnostics.setdefault("solver_status", "Optimal" if run.solutions else "NO_SOLUTION")
        run.diagnostics["distinct_alternatives"] = len(run.solutions)
        run.diagnostics["requested_alternatives"] = request.max_alternatives
        self.run_repo.save_run(run)
        return run

    def run_assignment(
        self,
        students: list[models.Student],
        projects: list[models.Project],
        skills: list[models.Skill] | None = None,
        fixed_assignments: list[models.FixedAssignment] | None = None,
        strategy_name: str = "PREFERENCE",
        max_alternatives: int = 3,
        notes: str = "",
    ) -> models.AssignmentRun:
        """Convenience method delegating to execute_run via RunRequest.

        Args:
            students: Student profiles.
            projects: Project specifications.
            skills: Optional skills catalog.
            fixed_assignments: Optional pre-allocated locks.
            strategy_name: Strategy key name.
            max_alternatives: Max solutions to generate.
            notes: Administrative description or notes for the run.

        Returns:
            The created AssignmentRun.
        """
        req = contract.RunRequest(
            students=students,
            projects=projects,
            skills=skills or [],
            fixed_assignments=fixed_assignments or [],
            strategy_key=strategy_name,
            max_alternatives=max_alternatives,
            notes=notes,
        )
        return self.execute_run(req)

    def list_runs(self, limit: int = 20) -> list[models.AssignmentRun]:
        """Retrieves historical assignment runs from repository.

        Args:
            limit: Maximum number of runs to retrieve.

        Returns:
            List of historical AssignmentRun domain objects.
        """
        return self.run_repo.list_runs(limit=limit)

    def get_run(self, run_id: str) -> models.AssignmentRun | None:
        """Retrieves a specific run by identifier.

        Args:
            run_id: Unique run identifier.

        Returns:
            The AssignmentRun object, or None if not found.
        """
        return self.run_repo.get_run(run_id)

    def get_solution(self, solution_id: str) -> models.Solution | None:
        """Retrieves a specific solution and its student allocations.

        Args:
            solution_id: Unique solution identifier.

        Returns:
            The Solution object with assignments, or None if not found.
        """
        return self.run_repo.get_solution(solution_id)

    def compare_solutions(
        self, solution_a_id: str, solution_b_id: str
    ) -> models.RunComparison:
        """Compares two alternative solutions side-by-side using metrics module.

        Args:
            solution_a_id: Identifier of the baseline solution.
            solution_b_id: Identifier of the comparison solution.

        Returns:
            RunComparison containing delta metrics and changed assignments.

        Raises:
            KeyError: If either solution cannot be found.
        """
        sol_a = self.run_repo.get_solution(solution_a_id)
        sol_b = self.run_repo.get_solution(solution_b_id)
        if sol_a is None or sol_b is None:
            raise KeyError(
                f"Solutions not found: {solution_a_id}, {solution_b_id}"
            )
        comp_dict = metrics.compare_two_solutions(sol_a, sol_b)
        return models.RunComparison.from_dict(comp_dict)
