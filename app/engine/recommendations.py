"""Transparent recommendation generator distinguishing evidence from advice.

This module implements the decision-support engine required by Section 9 of the
TECH5 specification, providing inspectable recommendations with explicit
criteria, mathematical evidence, and policy-oriented advice.
"""

import dataclasses
from typing import Any

from app.domain import models


@dataclasses.dataclass
class RecommendationItem:
    """An individual decision recommendation.

    Attributes:
        priority_focus: The organizational objective prioritized (e.g.
            Student Satisfaction, Project Skill Delivery, Egalitarian Balance).
        recommended_solution_id: Identifier of the top solution for this focus.
        recommended_alternative_number: 1-based index of recommended solution.
        criteria_used: Explicit list of analytical metrics evaluated.
        evidence: Objective calculated facts supporting the recommendation.
        advice: Practical normative advice describing operational trade-offs.
    """

    priority_focus: str
    recommended_solution_id: str
    recommended_alternative_number: int
    criteria_used: list[str]
    evidence: list[str]
    advice: str

    def to_dict(self) -> dict[str, Any]:
        """Serializes recommendation item to a dictionary.

        Returns:
            Dictionary containing recommendation fields.
        """
        return {
            "priority_focus": self.priority_focus,
            "recommended_solution_id": self.recommended_solution_id,
            "recommended_alternative_number": (
                self.recommended_alternative_number
            ),
            "criteria_used": list(self.criteria_used),
            "evidence": list(self.evidence),
            "advice": self.advice,
        }


def generate_recommendations(
    solutions: list[models.Solution],
) -> list[RecommendationItem]:
    """Generates policy-oriented recommendations from alternative solutions.

    Args:
        solutions: Feasible alternative solutions from an assignment run.

    Returns:
        List of structured RecommendationItem instances.
    """
    if not solutions:
        return []

    recommendations: list[RecommendationItem] = []

    # Priority 1: Maximizing Student Satisfaction
    best_pref_sol = min(
        solutions,
        key=lambda s: (
            s.indicators.get("fairness", {}).get("unranked_count", 999),
            s.indicators.get("fairness", {}).get("mean_rank", 999.0),
            s.indicators.get("fairness", {}).get("worst_rank", 999),
        ),
    )
    pref_indicators = best_pref_sol.indicators
    pref_fairness = pref_indicators.get("fairness", {})
    pref_efficiency = pref_indicators.get("efficiency", {})

    recommendations.append(
        RecommendationItem(
            priority_focus="Student Preference Maximization",
            recommended_solution_id=best_pref_sol.id,
            recommended_alternative_number=best_pref_sol.alternative_number,
            criteria_used=[
                "Average student preference rank (lower is better)",
                "Count of students assigned outside stated preferences",
                "Worst individual student rank",
            ],
            evidence=[
                f"Achieves average preference rank of "
                f"{pref_fairness.get('mean_rank', 'N/A')}.",
                f"Assigned {pref_fairness.get('unranked_count', 0)} students "
                "outside stated preferences.",
                f"Worst individual student rank is "
                f"{pref_fairness.get('worst_rank', 'N/A')}.",
                f"Maintains average skill-fit score of "
                f"{pref_efficiency.get('mean_skill_fit', 0.0):.2f}.",
            ],
            advice=(
                f"Adopt Solution {best_pref_sol.alternative_number} if "
                "student satisfaction, programme morale, and minimizing "
                "student appeals are the primary administrative goals."
            ),
        )
    )

    # Priority 2: Maximizing Project Skill Fit & Deliverable Quality
    best_skill_sol = max(
        solutions,
        key=lambda s: (
            s.indicators.get("efficiency", {}).get("mean_skill_fit", -1.0),
            -s.indicators.get("efficiency", {}).get(
                "unmet_soft_requirements_count", 999
            ),
        ),
    )
    skill_indicators = best_skill_sol.indicators
    skill_efficiency = skill_indicators.get("efficiency", {})
    skill_fairness = skill_indicators.get("fairness", {})

    recommendations.append(
        RecommendationItem(
            priority_focus="Project Skill Quality & Delivery Assurance",
            recommended_solution_id=best_skill_sol.id,
            recommended_alternative_number=best_skill_sol.alternative_number,
            criteria_used=[
                "Average student-project skill fit score (higher is better)",
                "Total unmet soft skill requirements (lower is better)",
            ],
            evidence=[
                f"Highest average skill fit score of "
                f"{skill_efficiency.get('mean_skill_fit', 0.0):.2f}.",
                f"Unmet soft requirements count: "
                f"{skill_efficiency.get('unmet_soft_requirements_count', 0)}.",
                f"Average student preference rank is "
                f"{skill_fairness.get('mean_rank', 'N/A')}.",
            ],
            advice=(
                f"Adopt Solution {best_skill_sol.alternative_number} when "
                "partner organizations or client project deliverables demand "
                "rigorous technical and domain capabilities."
            ),
        )
    )

    # Priority 3: Egalitarian Fairness & Balanced Trade-off
    best_balanced_sol = min(
        solutions,
        key=lambda s: (
            s.indicators.get("fairness", {}).get("rank_gini", 1.0),
            s.indicators.get("fairness", {}).get("rank_variance", 999.0),
            s.indicators.get("fairness", {}).get("mean_rank", 999.0),
        ),
    )
    bal_indicators = best_balanced_sol.indicators
    bal_fairness = bal_indicators.get("fairness", {})
    bal_efficiency = bal_indicators.get("efficiency", {})

    recommendations.append(
        RecommendationItem(
            priority_focus="Balanced & Egalitarian Allocation",
            recommended_solution_id=best_balanced_sol.id,
            recommended_alternative_number=best_balanced_sol.alternative_number,
            criteria_used=[
                "Rank Gini coefficient (equality of outcome distribution)",
                "Rank variance across students",
                "Harmonized score between preference rank and skill fit",
            ],
            evidence=[
                f"Lowest rank disparity (Gini coefficient: "
                f"{bal_fairness.get('rank_gini', 'N/A')}).",
                f"Rank variance: {bal_fairness.get('rank_variance', 'N/A')}.",
                f"Average skill fit: "
                f"{bal_efficiency.get('mean_skill_fit', 0.0):.2f}.",
                f"Average rank: {bal_fairness.get('mean_rank', 'N/A')}.",
            ],
            advice=(
                f"Adopt Solution {best_balanced_sol.alternative_number} if the "
                "academic committee seeks a fair Pareto compromise that avoids "
                "extreme individual disadvantage."
            ),
        )
    )

    return recommendations


@dataclasses.dataclass
class TradeoffRecommendation:
    """Detailed recommendation and trade-off justification between solutions.

    Attributes:
        what_improves: Concrete benefits of Solution B relative to Solution A.
        what_becomes_worse: Concrete costs or sacrifices of Solution B relative
            to Solution A.
        who_is_affected_summary: Narrative of students displaced or re-ranked.
        recommended_choice: The primary recommendation headline.
        evidence: Objective mathematical facts supporting the choice.
        advice: Normative administrative advice based on committee priorities.
        solution_a_strengths: Strengths of baseline Solution A.
        solution_b_strengths: Strengths of comparison Solution B.
        recommended_for_student_satisfaction: Alt number best for students.
        recommended_for_skill_delivery: Alt number best for project skill fit.
        recommended_for_balance: Alt number best for balanced equality.
    """

    what_improves: list[str]
    what_becomes_worse: list[str]
    who_is_affected_summary: str
    recommended_choice: str
    evidence: list[str]
    advice: str
    solution_a_strengths: list[str]
    solution_b_strengths: list[str]
    recommended_for_student_satisfaction: int
    recommended_for_skill_delivery: int
    recommended_for_balance: int

    def to_dict(self) -> dict[str, Any]:
        """Serializes tradeoff recommendation to a dictionary."""
        return {
            "what_improves": list(self.what_improves),
            "what_becomes_worse": list(self.what_becomes_worse),
            "who_is_affected_summary": self.who_is_affected_summary,
            "recommended_choice": self.recommended_choice,
            "evidence": list(self.evidence),
            "advice": self.advice,
            "solution_a_strengths": list(self.solution_a_strengths),
            "solution_b_strengths": list(self.solution_b_strengths),
            "recommended_for_student_satisfaction": (
                self.recommended_for_student_satisfaction
            ),
            "recommended_for_skill_delivery": (
                self.recommended_for_skill_delivery
            ),
            "recommended_for_balance": self.recommended_for_balance,
        }


def explain_tradeoff(
    solution_a: models.Solution,
    solution_b: models.Solution,
    comparison: models.RunComparison,
) -> TradeoffRecommendation:
    """Explains which alternative is recommended and why between two solutions.

    In compliance with Section 6 of the TECH5 specification, evaluates:
    - What improves?
    - What becomes worse?
    - Who is affected?
    - Which alternative would we recommend, and why?

    Args:
        solution_a: Baseline solution.
        solution_b: Comparison solution.
        comparison: Computed RunComparison object between A and B.

    Returns:
        Structured TradeoffRecommendation with objective evidence and advice.
    """
    eff_a = solution_a.indicators.get("efficiency", {})
    eff_b = solution_b.indicators.get("efficiency", {})
    fair_a = solution_a.indicators.get("fairness", {})
    fair_b = solution_b.indicators.get("fairness", {})

    fit_a = float(eff_a.get("mean_skill_fit", 0.0))
    fit_b = float(eff_b.get("mean_skill_fit", 0.0))

    mean_rank_a = float(fair_a.get("mean_rank", 0.0))
    mean_rank_b = float(fair_b.get("mean_rank", 0.0))

    worst_rank_a = int(fair_a.get("worst_rank", 0))
    worst_rank_b = int(fair_b.get("worst_rank", 0))

    unranked_a = int(fair_a.get("unranked_count", 0))
    unranked_b = int(fair_b.get("unranked_count", 0))

    gini_a = float(fair_a.get("rank_gini", 0.0))
    gini_b = float(fair_b.get("rank_gini", 0.0))

    unmet_soft_a = int(eff_a.get("unmet_soft_requirements_count", 0))
    unmet_soft_b = int(eff_b.get("unmet_soft_requirements_count", 0))

    alt_a = solution_a.alternative_number
    alt_b = solution_b.alternative_number

    # 1. What improves in Solution B relative to Solution A?
    what_improves: list[str] = []
    if fit_b > fit_a:
        delta_fit_pct = (fit_b - fit_a) * 100
        what_improves.append(
            f"Average project skill fit increases by {delta_fit_pct:+.1f}% "
            f"({fit_b * 100:.1f}% in B vs {fit_a * 100:.1f}% in A)."
        )
    if mean_rank_b < mean_rank_a:
        delta_rank = mean_rank_a - mean_rank_b
        what_improves.append(
            f"Average preference rank improves by {delta_rank:.2f} ranks "
            f"(Choice #{mean_rank_b:.2f} in B vs #{mean_rank_a:.2f} in A; "
            "lower rank is better)."
        )
    if comparison.rank_improved_count > 0:
        what_improves.append(
            f"{comparison.rank_improved_count} student(s) receive higher-"
            "preference project assignments."
        )
    if unranked_b < unranked_a:
        diff_u = unranked_a - unranked_b
        what_improves.append(
            f"{diff_u} fewer student(s) assigned outside stated preferences "
            f"({unranked_b} in B vs {unranked_a} in A)."
        )
    if worst_rank_b < worst_rank_a:
        what_improves.append(
            f"Worst individual student rank is protected (Choice "
            f"#{worst_rank_b} in B vs #{worst_rank_a} in A)."
        )
    if gini_b < gini_a:
        what_improves.append(
            "Fairness distribution is more equal (Rank Gini drops by "
            f"{gini_a - gini_b:.4f} from {gini_a:.3f} to {gini_b:.3f})."
        )
    if unmet_soft_b < unmet_soft_a:
        what_improves.append(
            f"Unmet soft requirements reduced by {unmet_soft_a - unmet_soft_b} "
            f"({unmet_soft_b} in B vs {unmet_soft_a} in A)."
        )
    if not what_improves:
        what_improves.append(
            "No measured analytical metrics improve in Solution B relative to "
            "Solution A."
        )

    # 2. What becomes worse in Solution B relative to Solution A?
    what_becomes_worse: list[str] = []
    if fit_b < fit_a:
        delta_fit_pct = (fit_a - fit_b) * 100
        what_becomes_worse.append(
            f"Average project skill fit decreases by {delta_fit_pct:.1f}% "
            f"({fit_b * 100:.1f}% in B vs {fit_a * 100:.1f}% in A)."
        )
    if mean_rank_b > mean_rank_a:
        delta_rank = mean_rank_b - mean_rank_a
        what_becomes_worse.append(
            f"Average preference rank worsens by {delta_rank:+.2f} ranks "
            f"(Choice #{mean_rank_b:.2f} in B vs #{mean_rank_a:.2f} in A)."
        )
    if comparison.rank_worsened_count > 0:
        what_becomes_worse.append(
            f"{comparison.rank_worsened_count} student(s) receive lower-"
            "preference project assignments."
        )
    if unranked_b > unranked_a:
        diff_u = unranked_b - unranked_a
        what_becomes_worse.append(
            f"{diff_u} additional student(s) assigned outside stated "
            f"preferences ({unranked_b} in B vs {unranked_a} in A)."
        )
    if worst_rank_b > worst_rank_a:
        what_becomes_worse.append(
            f"Worst individual student outcome is worse (Choice "
            f"#{worst_rank_b} in B vs #{worst_rank_a} in A)."
        )
    if gini_b > gini_a:
        what_becomes_worse.append(
            "Rank inequality among students increases (Rank Gini rises by "
            f"{gini_b - gini_a:.4f} from {gini_a:.3f} to {gini_b:.3f})."
        )
    if unmet_soft_b > unmet_soft_a:
        what_becomes_worse.append(
            f"Unmet soft requirements increase by "
            f"{unmet_soft_b - unmet_soft_a} ({unmet_soft_b} in B vs "
            f"{unmet_soft_a} in A)."
        )
    if not what_becomes_worse:
        what_becomes_worse.append(
            "No measured analytical metrics worsen in Solution B relative to "
            "Solution A."
        )

    # 3. Who is affected?
    if comparison.changed_students_count == 0:
        who_summary = (
            "No students are affected; Solution A and Solution B produce "
            "identical assignments."
        )
    else:
        who_summary = (
            f"{comparison.changed_students_count} of "
            f"{comparison.total_students} students are assigned to different "
            f"projects ({comparison.rank_improved_count} gain rank, "
            f"{comparison.rank_worsened_count} lose rank)."
        )

    # 4. Strengths of A and B
    sol_a_strengths: list[str] = []
    sol_b_strengths: list[str] = []

    if mean_rank_a < mean_rank_b:
        sol_a_strengths.append(
            f"Better student satisfaction (average rank #{mean_rank_a:.2f} "
            f"vs #{mean_rank_b:.2f})"
        )
    elif mean_rank_b < mean_rank_a:
        sol_b_strengths.append(
            f"Better student satisfaction (average rank #{mean_rank_b:.2f} "
            f"vs #{mean_rank_a:.2f})"
        )

    if fit_a > fit_b:
        sol_a_strengths.append(
            f"Higher skill alignment ({fit_a * 100:.1f}% vs "
            f"{fit_b * 100:.1f}%)"
        )
    elif fit_b > fit_a:
        sol_b_strengths.append(
            f"Higher skill alignment ({fit_b * 100:.1f}% vs "
            f"{fit_a * 100:.1f}%)"
        )

    if unranked_a < unranked_b:
        sol_a_strengths.append(
            f"Fewer students outside preferences ({unranked_a} vs {unranked_b})"
        )
    elif unranked_b < unranked_a:
        sol_b_strengths.append(
            f"Fewer students outside preferences ({unranked_b} vs {unranked_a})"
        )

    if gini_a < gini_b:
        sol_a_strengths.append(
            f"More equal distribution of ranks (Gini {gini_a:.3f} vs "
            f"{gini_b:.3f})"
        )
    elif gini_b < gini_a:
        sol_b_strengths.append(
            f"More equal distribution of ranks (Gini {gini_b:.3f} vs "
            f"{gini_a:.3f})"
        )

    if worst_rank_a < worst_rank_b:
        sol_a_strengths.append(
            f"Protected worst-case outcome (Worst #{worst_rank_a} vs "
            f"#{worst_rank_b})"
        )
    elif worst_rank_b < worst_rank_a:
        sol_b_strengths.append(
            f"Protected worst-case outcome (Worst #{worst_rank_b} vs "
            f"#{worst_rank_a})"
        )

    # Priority bests between A and B
    score_student_a = (unranked_a, mean_rank_a, worst_rank_a)
    score_student_b = (unranked_b, mean_rank_b, worst_rank_b)
    best_student_alt = (
        alt_a if score_student_a <= score_student_b else alt_b
    )

    best_skill_alt = (
        alt_b
        if (fit_b, -unmet_soft_b) > (fit_a, -unmet_soft_a)
        else alt_a
    )

    best_bal_alt = (
        alt_a
        if (gini_a, mean_rank_a) <= (gini_b, mean_rank_b)
        else alt_b
    )

    # 5. Objective Evidence Facts
    evidence = [
        f"Alternative #{alt_a} ({solution_a.strategy_name}): Avg Rank "
        f"#{mean_rank_a:.2f}, Skill Fit {fit_a * 100:.1f}%, Unranked "
        f"{unranked_a}, Rank Gini {gini_a:.3f}.",
        f"Alternative #{alt_b} ({solution_b.strategy_name}): Avg Rank "
        f"#{mean_rank_b:.2f}, Skill Fit {fit_b * 100:.1f}%, Unranked "
        f"{unranked_b}, Rank Gini {gini_b:.3f}.",
        f"Cohort allocation impact: {comparison.changed_students_count} "
        f"student(s) re-allocated ({comparison.rank_improved_count} improved, "
        f"{comparison.rank_worsened_count} worsened).",
    ]

    # 6. Recommendation Headline and Normative Advice
    if not comparison.is_distinct:
        recommended_choice = "Alternatives Are Operationally Identical"
        advice = (
            f"Solutions #{alt_a} and #{alt_b} assign every student to the "
            "exact same project. There are no operational trade-offs between "
            "these two alternatives; either may be deployed."
        )
    elif best_student_alt == alt_a and best_skill_alt == alt_b:
        recommended_choice = (
            f"Alternative #{alt_a} for Student Satisfaction vs "
            f"Alternative #{alt_b} for Technical Skill Delivery"
        )
        advice = (
            f"Adopt Solution Alternative #{alt_a} if cohort morale, student "
            "satisfaction, and minimizing appeals are the governing priorities "
            f"(achieves average preference rank of #{mean_rank_a:.2f}). "
            f"Adopt Solution Alternative #{alt_b} if partner organization "
            "deliverables and technical capabilities are paramount "
            f"(achieves average skill fit of {fit_b * 100:.1f}%)."
        )
    elif best_student_alt == alt_b and best_skill_alt == alt_a:
        recommended_choice = (
            f"Alternative #{alt_b} for Student Satisfaction vs "
            f"Alternative #{alt_a} for Technical Skill Delivery"
        )
        advice = (
            f"Adopt Solution Alternative #{alt_b} if student preference "
            "satisfaction is prioritized. Adopt Solution Alternative "
            f"#{alt_a} if project deliverable skill coverage is prioritized."
        )
    elif best_student_alt == alt_b and best_skill_alt == alt_b:
        recommended_choice = f"Alternative #{alt_b} (Pareto Superior)"
        advice = (
            f"Solution Alternative #{alt_b} matches or outperforms Solution "
            f"Alternative #{alt_a} on both student preference satisfaction and "
            f"project skill alignment. Adopting Alternative #{alt_b} is "
            "recommended."
        )
    elif best_student_alt == alt_a and best_skill_alt == alt_a:
        recommended_choice = f"Alternative #{alt_a} (Pareto Superior)"
        advice = (
            f"Solution Alternative #{alt_a} matches or outperforms Solution "
            f"Alternative #{alt_b} on both student preference satisfaction and "
            f"project skill alignment. Retaining Alternative #{alt_a} is "
            "recommended."
        )
    else:
        recommended_choice = (
            f"Alternative #{best_bal_alt} for Balanced Trade-Off"
        )
        advice = (
            f"Solution Alternative #{best_bal_alt} achieves the most equitable "
            "compromise between student satisfaction and project skill "
            "requirements."
        )

    return TradeoffRecommendation(
        what_improves=what_improves,
        what_becomes_worse=what_becomes_worse,
        who_is_affected_summary=who_summary,
        recommended_choice=recommended_choice,
        evidence=evidence,
        advice=advice,
        solution_a_strengths=sol_a_strengths,
        solution_b_strengths=sol_b_strengths,
        recommended_for_student_satisfaction=best_student_alt,
        recommended_for_skill_delivery=best_skill_alt,
        recommended_for_balance=best_bal_alt,
    )
