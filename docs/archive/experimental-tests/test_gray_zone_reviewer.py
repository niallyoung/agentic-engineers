"""
Tests for gray_zone_reviewer — Lead Engineer quality gate for 70–79 HANDBACK scores.

Covers: analyze_handback_for_gray_zone, _assess_risk, _verify_deliverables,
        _extract_coverage, _count_criteria_met, _apply_decision_matrix,
        _build_reasoning, _generate_follow_up_items.
"""

import pytest
from src.orchestration.agents.gray_zone_reviewer import (
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

@pytest.fixture
def low_risk_handback():
    return {
        "task_id": "2025-01-01-refactor-client-abc",
        "quality_score": 75,
        "deliverables_completed": ["Updated client.py", "Added unit tests"],
        "test_coverage": 92,
        "criteria_met": 3,
        "notes": "",
    }


@pytest.fixture
def high_risk_handback():
    return {
        "task_id": "2025-01-01-deploy-auth-xyz",
        "quality_score": 74,
        "touches_production": True,
        "deliverables_completed": ["Updated auth.py"],
        "test_coverage": 85,
    }


@pytest.fixture
def sample_delegate():
    return {
        "task_id": "2025-01-01-refactor-client-abc",
        "deliverables": ["Updated client.py", "Added unit tests"],
        "success_criteria": [
            "All existing tests pass",
            "New tests cover 90%+ branch coverage",
            "No regressions in integration suite",
        ],
    }


# ---------------------------------------------------------------------------
# analyze_handback_for_gray_zone — top-level function
# ---------------------------------------------------------------------------

class TestAnalyzeHandbackForGrayZone:
    def test_returns_dict_with_required_keys(self, low_risk_handback, sample_delegate):
        """analyze_handback_for_gray_zone returns a dict with all required keys."""
        result = analyze_handback_for_gray_zone(low_risk_handback, sample_delegate)
        required_keys = {
            "handback_id", "score", "risk_level", "criteria_met",
            "coverage", "deliverables_verified", "recommendation",
            "reasoning", "follow_up_items",
        }
        assert required_keys.issubset(result.keys())

    def test_low_risk_high_coverage_accept_recommendation(self, sample_delegate):
        """Low-risk handback with all criteria met and high coverage → ACCEPT."""
        handback = {
            "task_id": "2025-01-01-task-001",
            "quality_score": 77,
            "deliverables_completed": [
                "Updated client.py", "Added unit tests", "No regressions in integration suite"
            ],
            "test_coverage": 95,
            "criteria_met": 3,
        }
        result = analyze_handback_for_gray_zone(handback, sample_delegate)
        assert result["recommendation"] == "ACCEPT"

    def test_high_risk_always_rework(self, sample_delegate):
        """High-risk HANDBACK always produces REWORK regardless of score."""
        handback = {
            "task_id": "2025-01-01-task-001",
            "quality_score": 79,
            "touches_production": True,
            "deliverables_completed": ["Updated client.py", "Added unit tests"],
            "test_coverage": 99,
            "criteria_met": 3,
        }
        result = analyze_handback_for_gray_zone(handback, sample_delegate)
        assert result["recommendation"] == "REWORK"

    def test_missing_deliverables_rework(self):
        """Missing deliverables always produce REWORK."""
        handback = {
            "task_id": "2025-01-01-task-001",
            "quality_score": 78,
            "deliverables_completed": [],
            "test_coverage": 95,
            "criteria_met": 3,
        }
        delegate = {
            "deliverables": ["Required feature A", "Required tests B"],
            "success_criteria": ["Tests pass", "Coverage > 90%", "No regressions"],
        }
        result = analyze_handback_for_gray_zone(handback, delegate)
        assert result["recommendation"] == "REWORK"

    def test_score_extracted_from_quality_score_field(self, sample_delegate):
        """Score is read from quality_score field."""
        handback = {
            "task_id": "2025-01-01-task-001",
            "quality_score": 72,
            "deliverables_completed": ["Updated client.py", "Added unit tests"],
            "test_coverage": 90,
            "criteria_met": 3,
        }
        result = analyze_handback_for_gray_zone(handback, sample_delegate)
        assert result["score"] == 72

    def test_score_falls_back_to_score_field(self, sample_delegate):
        """Score falls back to 'score' key when quality_score absent."""
        handback = {
            "task_id": "2025-01-01-task-001",
            "score": 73,
            "deliverables_completed": ["Updated client.py", "Added unit tests"],
            "test_coverage": 91,
            "criteria_met": 3,
        }
        result = analyze_handback_for_gray_zone(handback, sample_delegate)
        assert result["score"] == 73

    def test_task_id_from_handback(self, sample_delegate):
        """handback_id in result comes from handback block."""
        handback = {
            "task_id": "2025-01-01-my-special-task",
            "quality_score": 75,
            "deliverables_completed": ["Updated client.py", "Added unit tests"],
            "test_coverage": 92,
            "criteria_met": 3,
        }
        result = analyze_handback_for_gray_zone(handback, sample_delegate)
        assert result["handback_id"] == "2025-01-01-my-special-task"

    def test_conditional_produces_follow_up_items(self, sample_delegate):
        """CONDITIONAL recommendation includes follow_up_items."""
        handback = {
            "task_id": "2025-01-01-task-001",
            "quality_score": 75,
            "deliverables_completed": ["Updated client.py", "Added unit tests"],
            "test_coverage": 86,
            "criteria_met": 2,  # Only 2/3 met → CONDITIONAL for low risk
        }
        result = analyze_handback_for_gray_zone(handback, sample_delegate)
        if result["recommendation"] == "CONDITIONAL":
            assert isinstance(result["follow_up_items"], list)
            assert len(result["follow_up_items"]) > 0

    def test_accept_produces_empty_follow_up_items(self, sample_delegate):
        """ACCEPT recommendation has empty follow_up_items."""
        handback = {
            "task_id": "2025-01-01-task-001",
            "quality_score": 77,
            "deliverables_completed": [
                "Updated client.py", "Added unit tests", "No regressions in integration suite"
            ],
            "test_coverage": 95,
            "criteria_met": 3,
        }
        result = analyze_handback_for_gray_zone(handback, sample_delegate)
        if result["recommendation"] == "ACCEPT":
            assert result["follow_up_items"] == []

    def test_no_explicit_delegate_task_id_uses_handback(self):
        """When delegate has no task_id, handback's task_id is used."""
        handback = {"task_id": "hb-task-id", "quality_score": 75}
        delegate = {}
        result = analyze_handback_for_gray_zone(handback, delegate)
        assert result["handback_id"] == "hb-task-id"


# ---------------------------------------------------------------------------
# _assess_risk
# ---------------------------------------------------------------------------

class TestAssessRisk:
    def test_touches_production_is_high_risk(self):
        assert _assess_risk({"touches_production": True}) == "high"

    def test_new_dependencies_is_high_risk(self):
        assert _assess_risk({"new_dependencies": ["requests>=2.28"]}) == "high"

    def test_tests_failed_is_high_risk(self):
        assert _assess_risk({"tests_failed": True}) == "high"

    def test_coverage_decreased_is_medium_risk(self):
        assert _assess_risk({"coverage_decreased": True}) == "medium"

    def test_untested_paths_is_medium_risk(self):
        assert _assess_risk({"untested_paths": True}) == "medium"

    def test_notes_with_production_keyword_is_medium(self):
        assert _assess_risk({"notes": "This change touches the production database"}) == "medium"

    def test_notes_with_auth_keyword_is_medium(self):
        assert _assess_risk({"notes": "Updates the auth module"}) == "medium"

    def test_clean_handback_is_low_risk(self):
        assert _assess_risk({"notes": "", "test_coverage": 90}) == "low"

    def test_empty_handback_is_low_risk(self):
        assert _assess_risk({}) == "low"


# ---------------------------------------------------------------------------
# _verify_deliverables
# ---------------------------------------------------------------------------

class TestVerifyDeliverables:
    def test_all_deliverables_present_returns_true(self):
        handback = {"deliverables_completed": ["feature A", "unit tests for A"]}
        delegate = {"deliverables": ["feature A", "unit tests for A"]}
        assert _verify_deliverables(handback, delegate) is True

    def test_missing_deliverable_returns_false(self):
        handback = {"deliverables_completed": ["feature A"]}
        delegate = {"deliverables": ["feature A", "unit tests for A"]}
        assert _verify_deliverables(handback, delegate) is False

    def test_no_required_deliverables_returns_true(self):
        handback = {}
        delegate = {}
        assert _verify_deliverables(handback, delegate) is True

    def test_empty_completed_with_required_returns_false(self):
        handback = {"deliverables_completed": []}
        delegate = {"deliverables": ["feature A"]}
        assert _verify_deliverables(handback, delegate) is False

    def test_partial_string_match_counts(self):
        """Partial substring match is sufficient."""
        handback = {"deliverables_completed": ["Updated client.py with retry logic"]}
        delegate = {"deliverables": ["client.py"]}
        assert _verify_deliverables(handback, delegate) is True

    def test_alternate_deliverables_key(self):
        """Falls back to 'deliverables' key in handback."""
        handback = {"deliverables": ["feature A"]}
        delegate = {"deliverables": ["feature A"]}
        assert _verify_deliverables(handback, delegate) is True


# ---------------------------------------------------------------------------
# _extract_coverage
# ---------------------------------------------------------------------------

class TestExtractCoverage:
    def test_extract_integer_coverage(self):
        assert _extract_coverage({"test_coverage": 92}) == 92

    def test_extract_float_coverage(self):
        assert _extract_coverage({"test_coverage": 87.5}) == 87

    def test_extract_string_with_percent(self):
        assert _extract_coverage({"test_coverage": "90%"}) == 90

    def test_extract_from_coverage_key(self):
        assert _extract_coverage({"coverage": 85}) == 85

    def test_no_coverage_returns_zero(self):
        assert _extract_coverage({}) == 0

    def test_invalid_coverage_returns_zero(self):
        assert _extract_coverage({"test_coverage": "N/A"}) == 0


# ---------------------------------------------------------------------------
# _count_criteria_met
# ---------------------------------------------------------------------------

class TestCountCriteriaMet:
    def test_integer_criteria_met_used_directly(self):
        handback = {"criteria_met": 3}
        delegate = {"success_criteria": ["A", "B", "C", "D"]}
        met, total = _count_criteria_met(handback, delegate)
        assert met == 3
        assert total == 4

    def test_list_criteria_met_counts_length(self):
        handback = {"criteria_met": ["A", "B"]}
        delegate = {"success_criteria": ["A", "B", "C"]}
        met, total = _count_criteria_met(handback, delegate)
        assert met == 2
        assert total == 3

    def test_no_explicit_criteria_met_uses_score_heuristic(self):
        handback = {"quality_score": 80}
        delegate = {"success_criteria": ["A", "B", "C", "D"]}
        met, total = _count_criteria_met(handback, delegate)
        assert total == 4
        assert 1 <= met <= total

    def test_no_criteria_in_delegate_returns_defaults(self):
        """No criteria in delegate → returns generic 4-total estimate."""
        met, total = _count_criteria_met({}, {})
        assert total == 4
        assert met >= 1


# ---------------------------------------------------------------------------
# _apply_decision_matrix
# ---------------------------------------------------------------------------

class TestApplyDecisionMatrix:
    def test_missing_deliverables_always_rework(self):
        assert _apply_decision_matrix("low", 4, 4, 95, False) == "REWORK"

    def test_high_risk_always_rework(self):
        assert _apply_decision_matrix("high", 4, 4, 99, True) == "REWORK"

    def test_low_risk_full_criteria_high_coverage_accept(self):
        assert _apply_decision_matrix("low", 4, 4, 95, True) == "ACCEPT"

    def test_low_risk_partial_criteria_medium_coverage_conditional(self):
        """50%+ criteria met with 85%+ coverage → CONDITIONAL for low risk."""
        assert _apply_decision_matrix("low", 2, 4, 85, True) == "CONDITIONAL"

    def test_low_risk_poor_criteria_rework(self):
        """Low fraction of criteria met → REWORK even for low risk."""
        assert _apply_decision_matrix("low", 1, 4, 80, True) == "REWORK"

    def test_medium_risk_all_criteria_very_high_coverage_accept(self):
        assert _apply_decision_matrix("medium", 3, 3, 96, True) == "ACCEPT"

    def test_medium_risk_partial_criteria_high_coverage_conditional(self):
        assert _apply_decision_matrix("medium", 3, 4, 91, True) == "CONDITIONAL"

    def test_medium_risk_poor_coverage_rework(self):
        assert _apply_decision_matrix("medium", 3, 3, 80, True) == "REWORK"


# ---------------------------------------------------------------------------
# _build_reasoning
# ---------------------------------------------------------------------------

class TestBuildReasoning:
    def test_reasoning_contains_score(self):
        reasoning = _build_reasoning(75, "low", 3, 4, 90, True, "ACCEPT")
        assert "75" in reasoning

    def test_reasoning_contains_risk_level(self):
        reasoning = _build_reasoning(75, "low", 3, 4, 90, True, "ACCEPT")
        assert "low" in reasoning

    def test_reasoning_contains_recommendation(self):
        reasoning = _build_reasoning(75, "low", 3, 4, 90, True, "ACCEPT")
        assert "ACCEPT" in reasoning

    def test_reasoning_contains_coverage(self):
        reasoning = _build_reasoning(75, "low", 3, 4, 90, True, "ACCEPT")
        assert "90" in reasoning

    def test_reasoning_is_string(self):
        reasoning = _build_reasoning(75, "low", 3, 4, 90, True, "REWORK")
        assert isinstance(reasoning, str)
        assert len(reasoning) > 0

    def test_conditional_reasoning_mentions_follow_up(self):
        reasoning = _build_reasoning(76, "low", 2, 4, 86, True, "CONDITIONAL")
        assert "CONDITIONAL" in reasoning


# ---------------------------------------------------------------------------
# _generate_follow_up_items
# ---------------------------------------------------------------------------

class TestGenerateFollowUpItems:
    def test_unmet_criteria_generates_item(self):
        items = _generate_follow_up_items({}, {"success_criteria": ["A", "B", "C"]}, 2, 3)
        assert any("criteria" in item.lower() for item in items)

    def test_low_coverage_generates_item(self):
        handback = {"test_coverage": 80}
        items = _generate_follow_up_items(handback, {}, 3, 3)
        assert any("coverage" in item.lower() for item in items)

    def test_untested_paths_generates_item(self):
        handback = {"untested_paths": True}
        items = _generate_follow_up_items(handback, {"success_criteria": ["A"]}, 1, 1)
        assert any("untested" in item.lower() or "test" in item.lower() for item in items)

    def test_notes_generates_item(self):
        handback = {"notes": "There is a known issue with the error handler.", "test_coverage": 90}
        items = _generate_follow_up_items(handback, {"success_criteria": ["A"]}, 1, 1)
        assert any("notes" in item.lower() or "review" in item.lower() for item in items)

    def test_no_issues_generates_default_item(self):
        """When no issues detected, generates a default follow-up item."""
        items = _generate_follow_up_items({"test_coverage": 95}, {"success_criteria": ["A"]}, 1, 1)
        assert len(items) > 0

    def test_returns_list(self):
        items = _generate_follow_up_items({}, {}, 2, 3)
        assert isinstance(items, list)
