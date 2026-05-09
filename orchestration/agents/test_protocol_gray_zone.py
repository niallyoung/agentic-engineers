"""
Tests for Protocol Week 3: Gray-Zone Manual Review Gate (70–79 score band).
"""

import pytest
import sys
import os
from pathlib import Path

# Ensure the agents package is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from orchestration.agents.gray_zone_reviewer import (
    analyze_handback_for_gray_zone,
    _assess_risk,
    _verify_deliverables,
    _extract_coverage,
    _count_criteria_met,
    _apply_decision_matrix,
    _build_reasoning,
    _generate_follow_up_items,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_handback(score=75, coverage=90, deliverables=None, criteria_met=None,
                  new_dependencies=False, tests_failed=False, coverage_decreased=False,
                  untested_paths=False, touches_production=False, notes=""):
    hb = {
        "task_id": "test-task-001",
        "quality_score": score,
        "test_coverage": coverage,
        "tests_failed": tests_failed,
        "coverage_decreased": coverage_decreased,
        "new_dependencies": new_dependencies,
        "untested_paths": untested_paths,
        "touches_production": touches_production,
        "notes": notes,
    }
    if deliverables is not None:
        hb["deliverables_completed"] = deliverables
    if criteria_met is not None:
        hb["criteria_met"] = criteria_met
    return hb


def make_delegate(deliverables=None, success_criteria=None):
    d = {"task_id": "test-task-001"}
    if deliverables is not None:
        d["deliverables"] = deliverables
    if success_criteria is not None:
        d["success_criteria"] = success_criteria
    return d


# ---------------------------------------------------------------------------
# Analysis Tests (10 tests)
# ---------------------------------------------------------------------------

def test_score_75_low_risk_3_of_4_criteria_accept():
    """Score 75, low risk, 3/4 criteria met → ACCEPT."""
    hb = make_handback(score=75, coverage=92)
    hb["criteria_met"] = 3
    delegate = make_delegate(success_criteria=["c1", "c2", "c3", "c4"],
                             deliverables=["file_a"])
    hb["deliverables_completed"] = ["file_a"]
    result = analyze_handback_for_gray_zone(hb, delegate)
    assert result["recommendation"] == "ACCEPT"
    assert result["score"] == 75
    assert result["risk_level"] == "low"


def test_score_72_low_risk_2_of_4_criteria_conditional():
    """Score 72, low risk, 2/4 criteria met, 86% coverage → CONDITIONAL."""
    hb = make_handback(score=72, coverage=86)
    hb["criteria_met"] = 2
    delegate = make_delegate(success_criteria=["c1", "c2", "c3", "c4"],
                             deliverables=["file_a"])
    hb["deliverables_completed"] = ["file_a"]
    result = analyze_handback_for_gray_zone(hb, delegate)
    assert result["recommendation"] == "CONDITIONAL"


def test_score_78_high_risk_any_criteria_rework():
    """Score 78, high risk → REWORK regardless of criteria."""
    hb = make_handback(score=78, coverage=95, new_dependencies=True)
    hb["criteria_met"] = 4
    delegate = make_delegate(success_criteria=["c1", "c2", "c3", "c4"],
                             deliverables=["file_a"])
    hb["deliverables_completed"] = ["file_a"]
    result = analyze_handback_for_gray_zone(hb, delegate)
    assert result["recommendation"] == "REWORK"
    assert result["risk_level"] == "high"


def test_score_75_medium_risk_4_of_4_criteria_accept():
    """Score 75, medium risk, 4/4 criteria met, 96% coverage → ACCEPT."""
    hb = make_handback(score=75, coverage=96, coverage_decreased=True)  # triggers medium risk
    hb["criteria_met"] = 4
    delegate = make_delegate(success_criteria=["c1", "c2", "c3", "c4"],
                             deliverables=["file_a"])
    hb["deliverables_completed"] = ["file_a"]
    result = analyze_handback_for_gray_zone(hb, delegate)
    assert result["recommendation"] == "ACCEPT"
    assert result["risk_level"] == "medium"


def test_missing_deliverable_rework():
    """If a required deliverable is missing, recommendation must be REWORK."""
    hb = make_handback(score=77, coverage=92)
    hb["criteria_met"] = 3
    hb["deliverables_completed"] = ["only_file_a"]
    delegate = make_delegate(
        success_criteria=["c1", "c2", "c3", "c4"],
        deliverables=["only_file_a", "missing_file_b"]
    )
    result = analyze_handback_for_gray_zone(hb, delegate)
    assert result["recommendation"] == "REWORK"
    assert result["deliverables_verified"] is False


def test_coverage_dropped_causes_medium_risk():
    """coverage_decreased flag triggers medium risk assessment."""
    hb = make_handback(score=76, coverage=88, coverage_decreased=True)
    result_risk = _assess_risk(hb)
    assert result_risk == "medium"


def test_new_dependencies_causes_high_risk():
    """new_dependencies flag triggers high risk assessment."""
    hb = make_handback(score=74, new_dependencies=["requests==2.31"])
    result_risk = _assess_risk(hb)
    assert result_risk == "high"


def test_all_deliverables_verified_true():
    """When all required deliverables are present, verified=True."""
    hb = make_handback(score=73)
    hb["deliverables_completed"] = ["file_a", "file_b"]
    delegate = make_delegate(deliverables=["file_a", "file_b"])
    assert _verify_deliverables(hb, delegate) is True


def test_criteria_count_matches_expected():
    """Criteria count extraction returns correct values."""
    hb = make_handback(score=75)
    hb["criteria_met"] = 3
    delegate = make_delegate(success_criteria=["c1", "c2", "c3", "c4"])
    met, total = _count_criteria_met(hb, delegate)
    assert met == 3
    assert total == 4


def test_reasoning_generated_for_all_decisions():
    """Reasoning string is always present and non-empty for all decisions."""
    for recommendation in ["ACCEPT", "CONDITIONAL", "REWORK"]:
        reasoning = _build_reasoning(75, "low", 3, 4, 90, True, recommendation)
        assert reasoning
        assert str(recommendation) in reasoning
        assert "75/100" in reasoning


# ---------------------------------------------------------------------------
# Integration Tests (5 tests)
# ---------------------------------------------------------------------------

def test_gray_zone_handback_returns_manual_review_lead():
    """analyze_handback_for_gray_zone returns dict with expected structure."""
    hb = make_handback(score=75, coverage=92)
    hb["criteria_met"] = 3
    hb["deliverables_completed"] = ["file_a"]
    delegate = make_delegate(success_criteria=["c1", "c2", "c3", "c4"],
                             deliverables=["file_a"])
    result = analyze_handback_for_gray_zone(hb, delegate)
    assert "recommendation" in result
    assert "reasoning" in result
    assert "risk_level" in result
    assert "criteria_met" in result
    assert "coverage" in result
    assert "deliverables_verified" in result


def test_analysis_attached_to_routing_context():
    """Result dict includes handback_id matching task_id."""
    hb = make_handback(score=75)
    hb["task_id"] = "my-task-001"
    delegate = make_delegate()
    delegate["task_id"] = "my-task-001"
    result = analyze_handback_for_gray_zone(hb, delegate)
    assert result["handback_id"] == "my-task-001"


def test_lead_review_tool_save_and_load(tmp_path, monkeypatch):
    """Review decision can be persisted and loaded."""
    import orchestration.tools.lead_review_cli as cli
    reviews_file = tmp_path / "gray_zone_reviews.json"
    monkeypatch.setattr(cli, "REVIEWS_FILE", reviews_file)
    cli.save_review_decision("task-abc", "ACCEPT", "Looks good")
    reviews = cli._load_reviews()
    assert "task-abc" in reviews
    assert reviews["task-abc"]["decision"] == "ACCEPT"
    assert reviews["task-abc"]["status"] == "reviewed"


def test_review_decision_persisted_correctly(tmp_path, monkeypatch):
    """CONDITIONAL decision includes all expected fields."""
    import orchestration.tools.lead_review_cli as cli
    reviews_file = tmp_path / "gray_zone_reviews.json"
    monkeypatch.setattr(cli, "REVIEWS_FILE", reviews_file)
    cli.save_review_decision("task-xyz", "CONDITIONAL", "Minor gaps remain")
    reviews = cli._load_reviews()
    r = reviews["task-xyz"]
    assert r["decision"] == "CONDITIONAL"
    assert r["notes"] == "Minor gaps remain"
    assert "reviewed_at" in r


def test_conditional_generates_follow_up_items():
    """CONDITIONAL recommendation generates non-empty follow-up items."""
    hb = make_handback(score=72, coverage=86)
    hb["criteria_met"] = 2
    hb["deliverables_completed"] = ["file_a"]
    delegate = make_delegate(success_criteria=["c1", "c2", "c3", "c4"],
                             deliverables=["file_a"])
    result = analyze_handback_for_gray_zone(hb, delegate)
    if result["recommendation"] == "CONDITIONAL":
        assert len(result["follow_up_items"]) > 0


# ---------------------------------------------------------------------------
# Edge Case Tests (5 tests)
# ---------------------------------------------------------------------------

def test_score_exactly_70_treated_as_gray_zone():
    """Score 70 is in range and processed normally."""
    hb = make_handback(score=70, coverage=92)
    hb["criteria_met"] = 3
    hb["deliverables_completed"] = ["file_a"]
    delegate = make_delegate(success_criteria=["c1", "c2", "c3", "c4"],
                             deliverables=["file_a"])
    result = analyze_handback_for_gray_zone(hb, delegate)
    assert result["score"] == 70
    assert result["recommendation"] in ("ACCEPT", "CONDITIONAL", "REWORK")


def test_score_exactly_79_treated_as_gray_zone():
    """Score 79 is in range and processed normally."""
    hb = make_handback(score=79, coverage=92)
    hb["criteria_met"] = 3
    hb["deliverables_completed"] = ["file_a"]
    delegate = make_delegate(success_criteria=["c1", "c2", "c3", "c4"],
                             deliverables=["file_a"])
    result = analyze_handback_for_gray_zone(hb, delegate)
    assert result["score"] == 79
    assert result["recommendation"] in ("ACCEPT", "CONDITIONAL", "REWORK")


def test_multiple_criteria_at_different_met_levels():
    """Criteria count can be 0, partial, or full."""
    for met in [0, 1, 2, 3, 4]:
        hb = make_handback(score=75, coverage=90)
        hb["criteria_met"] = met
        hb["deliverables_completed"] = ["file_a"]
        delegate = make_delegate(success_criteria=["c1", "c2", "c3", "c4"],
                                 deliverables=["file_a"])
        result = analyze_handback_for_gray_zone(hb, delegate)
        assert result["recommendation"] in ("ACCEPT", "CONDITIONAL", "REWORK")


def test_zero_coverage_causes_rework():
    """Zero coverage is treated as insufficient and should cause REWORK."""
    hb = make_handback(score=77, coverage=0)
    hb["criteria_met"] = 4
    hb["deliverables_completed"] = ["file_a"]
    delegate = make_delegate(success_criteria=["c1", "c2", "c3", "c4"],
                             deliverables=["file_a"])
    result = analyze_handback_for_gray_zone(hb, delegate)
    assert result["recommendation"] == "REWORK"
    assert result["coverage"] == 0


def test_empty_deliverables_list_in_delegate():
    """When DELEGATE has no deliverables listed, verification passes trivially."""
    hb = make_handback(score=75, coverage=91)
    hb["criteria_met"] = 3
    delegate = make_delegate(success_criteria=["c1", "c2", "c3", "c4"])
    # No deliverables key in delegate
    assert _verify_deliverables(hb, delegate) is True
    result = analyze_handback_for_gray_zone(hb, delegate)
    assert result["deliverables_verified"] is True
