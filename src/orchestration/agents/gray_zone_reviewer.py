"""
Gray-Zone Reviewer — Lead Engineer quality gate for 70–79 score HANDBACKs.

Analyzes borderline HANDBACKs and recommends ACCEPT, CONDITIONAL, or REWORK
based on risk level, criteria met, and test coverage.
"""

from typing import Dict, List, Any, Optional


def analyze_handback_for_gray_zone(handback_block: dict, original_delegate: dict) -> dict:
    """
    Analyze a 70–79 HANDBACK for gray-zone review decision.

    Args:
        handback_block: HANDBACK dict with score, deliverables, tests, notes.
        original_delegate: Original DELEGATE dict for criteria comparison.

    Returns:
        dict with keys: handback_id, score, risk_level, criteria_met, coverage,
        deliverables_verified, recommendation, reasoning, follow_up_items.
    """
    task_id = handback_block.get("task_id", original_delegate.get("task_id", "unknown"))
    score = int(handback_block.get("quality_score", handback_block.get("score", 75)))

    # 1. Risk assessment
    risk_level = _assess_risk(handback_block)

    # 2. Deliverable verification
    deliverables_verified = _verify_deliverables(handback_block, original_delegate)

    # 3. Test coverage
    coverage = _extract_coverage(handback_block)

    # 4. Criteria mapping
    criteria_met, total_criteria = _count_criteria_met(handback_block, original_delegate)

    # 5. Apply decision matrix
    recommendation = _apply_decision_matrix(risk_level, criteria_met, total_criteria, coverage, deliverables_verified)

    # 6. Generate reasoning
    reasoning = _build_reasoning(score, risk_level, criteria_met, total_criteria, coverage, deliverables_verified, recommendation)

    # 7. Follow-up items for CONDITIONAL
    follow_up_items = _generate_follow_up_items(handback_block, original_delegate, criteria_met, total_criteria) if recommendation == "CONDITIONAL" else []

    return {
        "handback_id": task_id,
        "score": score,
        "risk_level": risk_level,
        "criteria_met": f"{criteria_met}/{total_criteria}",
        "coverage": coverage,
        "deliverables_verified": deliverables_verified,
        "recommendation": recommendation,
        "reasoning": reasoning,
        "follow_up_items": follow_up_items,
    }


def _assess_risk(handback_block: dict) -> str:
    """Assess risk level from HANDBACK metadata."""
    # High risk signals
    if handback_block.get("touches_production", False):
        return "high"
    if handback_block.get("new_dependencies"):
        return "high"
    if handback_block.get("tests_failed", False):
        return "high"
    if handback_block.get("coverage_decreased", False):
        return "medium"
    if handback_block.get("untested_paths", False):
        return "medium"
    # Check notes/status for risk signals
    notes = str(handback_block.get("notes", "")).lower()
    if any(kw in notes for kw in ["production", "database", "auth", "security", "critical"]):
        return "medium"
    return "low"


def _verify_deliverables(handback_block: dict, original_delegate: dict) -> bool:
    """Check that all required deliverables from DELEGATE are present in HANDBACK."""
    required = original_delegate.get("deliverables", [])
    if not required:
        return True
    completed = handback_block.get("deliverables_completed", handback_block.get("deliverables", []))
    if not completed:
        return False
    completed_set = {str(d).lower() for d in completed}
    for req in required:
        if not any(str(req).lower() in c or c in str(req).lower() for c in completed_set):
            return False
    return True


def _extract_coverage(handback_block: dict) -> int:
    """Extract test coverage percentage from HANDBACK."""
    cov = handback_block.get("test_coverage", handback_block.get("coverage", None))
    if cov is None:
        return 0
    try:
        return int(float(str(cov).replace("%", "").strip()))
    except (ValueError, TypeError):
        return 0


def _count_criteria_met(handback_block: dict, original_delegate: dict) -> tuple:
    """Count how many success_criteria from DELEGATE are fully met."""
    criteria = original_delegate.get("success_criteria", [])
    if not criteria:
        # No explicit criteria: assume 3 of 4 generic ones met if deliverables verified
        total = 4
        met = 3 if _verify_deliverables(handback_block, original_delegate) else 1
        return met, total
    total = len(criteria)
    met_criteria = handback_block.get("criteria_met", handback_block.get("success_criteria_met", None))
    if isinstance(met_criteria, int):
        return met_criteria, total
    if isinstance(met_criteria, list):
        return len(met_criteria), total
    # Heuristic: use quality score to estimate
    score = int(handback_block.get("quality_score", handback_block.get("score", 75)))
    met = max(1, round((score / 100) * total))
    return met, total


def _apply_decision_matrix(risk_level: str, criteria_met: int, total_criteria: int, coverage: int, deliverables_verified: bool) -> str:
    """Apply the decision matrix: Risk × Criteria Met × Coverage."""
    # Deliverable missing is always REWORK
    if not deliverables_verified:
        return "REWORK"
    # High risk is always REWORK
    if risk_level == "high":
        return "REWORK"

    fraction = criteria_met / total_criteria if total_criteria > 0 else 0

    if risk_level == "low":
        if fraction >= 0.75 and coverage >= 90:
            return "ACCEPT"
        elif fraction >= 0.5 and coverage >= 85:
            return "CONDITIONAL"
        else:
            return "REWORK"

    if risk_level == "medium":
        if fraction >= 1.0 and coverage >= 95:
            return "ACCEPT"
        elif fraction >= 0.75 and coverage >= 90:
            return "CONDITIONAL"
        else:
            return "REWORK"

    return "REWORK"


def _build_reasoning(score: int, risk_level: str, criteria_met: int, total_criteria: int, coverage: int, deliverables_verified: bool, recommendation: str) -> str:
    """Build human-readable reasoning for the recommendation."""
    parts = [
        f"Score {score}/100 (gray-zone 70–79).",
        f"Risk level: {risk_level}.",
        f"Criteria met: {criteria_met}/{total_criteria}.",
        f"Test coverage: {coverage}%.",
        f"Deliverables verified: {deliverables_verified}.",
        f"Recommendation: {recommendation}.",
    ]
    if recommendation == "ACCEPT":
        parts.append("Risk is acceptable; criteria and coverage meet thresholds for acceptance.")
    elif recommendation == "CONDITIONAL":
        parts.append("Borderline quality; merge with follow-up items to address gaps.")
    else:
        parts.append("Quality insufficient for merge; rework required.")
    return " ".join(parts)


def _generate_follow_up_items(handback_block: dict, original_delegate: dict, criteria_met: int, total_criteria: int) -> List[str]:
    """Generate specific follow-up items for CONDITIONAL decisions."""
    items = []
    if criteria_met < total_criteria:
        items.append(f"Address {total_criteria - criteria_met} unmet success criteria from original DELEGATE.")
    coverage = _extract_coverage(handback_block)
    if coverage < 90:
        items.append(f"Improve test coverage from {coverage}% to ≥90%.")
    if handback_block.get("untested_paths"):
        items.append("Add tests for identified untested code paths.")
    notes = handback_block.get("notes", "")
    if notes:
        items.append(f"Review and address notes: {notes[:120]}")
    if not items:
        items.append("Review and close any open quality findings before next release.")
    return items
